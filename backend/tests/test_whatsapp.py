from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import pytest
import threading
import unittest

import httpx
from fastapi.testclient import TestClient
from backend.whatsapp import Settings, create_app
from backend.gateway import PostgresStore
from backend.tests.test_api import client, URL

pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL')


class GatewayTests(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def setup_database(self, client, monkeypatch):
        self.pool=client.app.state.pool
        monkeypatch.setenv('DATABASE_URL',self.pool.conninfo)
        self.settings = Settings(
            token="a" * 40,
            recipients={"owner": ("5511999999999",), "volunteers": ()},
            dry_run=False, access_token="fake-meta-token", phone_number_id="12345",
            graph_version="v99.0", mode="text",
        )
        self.calls = []
        self.reply = lambda request: httpx.Response(200, json={"messages": [{"id": "wamid.test"}]})
        def transport(request):
            self.calls.append(request)
            return self.reply(request)
        self.meta = httpx.Client(transport=httpx.MockTransport(transport))
        self.addCleanup(self.meta.close)

    def post(self, client, id="adoption:test", text="Nova candidatura", target="owner", **kwargs):
        return client.post("/messages", json={"id": id, "target": target, "text": text},
                           headers={"Authorization": "Bearer " + self.settings.token, "Idempotency-Key": id}, **kwargs)

    def client(self, settings=None):
        return TestClient(create_app(settings or self.settings, self.meta, store_factory=PostgresStore))

    def test_auth_validation_and_body_limit(self):
        with self.client() as client:
            self.assertEqual(client.post("/messages", json={}).status_code, 401)
            headers={"Authorization": "Bearer " + self.settings.token}
            self.assertEqual(client.post("/messages", content=b"x" * 65537, headers=headers).status_code, 413)
            self.assertEqual(client.post("/messages", json={}, headers=headers).status_code, 422)
            self.assertEqual(client.post("/messages", json={"id":"test", "target":"owner", "text":"test"}, headers=headers).status_code, 400)
            self.assertEqual(self.post(client, target="arbitrary-number").status_code, 422)
            self.assertEqual(self.post(client, target="volunteers").status_code, 422)
            self.assertEqual(self.post(client, text="x" * 4097).status_code, 422)
        self.assertEqual(self.calls, [])

    def test_delivery_and_persistent_deduplication(self):
        with self.client() as client:
            result=self.post(client)
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()["accepted"])
            self.assertEqual(self.post(client).json()["message_ids"], ["wamid.test"])
            self.assertEqual(self.post(client, text="Outro conteúdo").status_code, 409)
        with self.client() as restarted:
            self.assertEqual(self.post(restarted).status_code, 200)
        self.assertEqual(len(self.calls), 1)
        request=self.calls[0]
        self.assertEqual(str(request.url), "https://graph.facebook.com/v99.0/12345/messages")
        self.assertEqual(request.headers["authorization"], "Bearer fake-meta-token")
        self.assertIn(b'Nova candidatura', request.content)
        with self.pool.connection() as db:
            self.assertEqual(db.execute('SELECT txt_estado FROM entregas_whatsapp').fetchone()['state'], 'accepted')
            self.assertEqual(db.execute('SELECT count(*) FROM envios_whatsapp').fetchone()['count'], 1)

    def test_concurrent_requests_cannot_send_twice(self):
        entered, release = threading.Event(), threading.Event()
        def delayed(request):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release the simulated provider")
            return httpx.Response(200, json={"messages": [{"id": "wamid.concurrent"}]})
        self.reply=delayed
        with self.client() as client, ThreadPoolExecutor(max_workers=1) as pool:
            first=pool.submit(self.post, client)
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.post(client).status_code, 409)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5).status_code, 200)
            self.assertEqual(self.post(client).status_code, 200)
        self.assertEqual(len(self.calls), 1)

    def test_simulation_never_sends_or_consumes_id(self):
        with self.client(replace(self.settings, dry_run=True)) as client:
            result=self.post(client).json()
            self.assertFalse(result["accepted"])
            self.assertTrue(result["simulated"])
        self.assertEqual(self.calls, [])
        with self.client() as client:
            self.assertTrue(self.post(client).json()["accepted"])

    def test_partial_delivery_retries_only_rejected_recipient(self):
        settings=replace(self.settings, recipients={"owner": ("5511999999999", "5511888888888")})
        self.reply=lambda request: httpx.Response(429) if len(self.calls)==2 else httpx.Response(200, json={"messages":[{"id":f"wamid.{len(self.calls)}"}]})
        with self.client(settings) as client:
            self.assertEqual(self.post(client).status_code, 502)
            result=self.post(client)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["message_ids"], ["wamid.1", "wamid.3"])
        self.assertEqual(len(self.calls), 3)

    def test_timeout_stays_uncertain_and_is_not_resent(self):
        def timeout(request):
            raise httpx.ReadTimeout("secret-bearing error", request=request)
        self.reply=timeout
        with self.client() as client:
            result=self.post(client)
            self.assertEqual(result.status_code, 503)
            self.assertNotIn("secret-bearing", result.text)
            self.assertEqual(self.post(client).status_code, 409)
        self.assertEqual(len(self.calls), 1)

    def test_server_error_and_invalid_success_block_resend(self):
        for id, reply in [("server", httpx.Response(500)), ("malformed", httpx.Response(200, json={}))]:
            self.reply=lambda request: reply
            with self.client() as client:
                self.assertEqual(self.post(client, id=id).status_code, 502)
                self.assertEqual(self.post(client, id=id).status_code, 409)
        self.assertEqual(len(self.calls), 2)

    def test_template_uses_configured_link_instead_of_private_report(self):
        settings=replace(self.settings, mode="template", templates={"owner":"peticas_aviso"}, template_value="https://peticas.example/#team")
        with self.client(settings) as client:
            self.assertEqual(self.post(client, text="Relatório privado\ncom dados").status_code, 200)
        import json
        payload=json.loads(self.calls[0].content)
        self.assertEqual(payload["type"], "template")
        self.assertEqual(payload["template"]["name"], "peticas_aviso")
        self.assertEqual(payload["template"]["components"][0]["parameters"][0]["text"], settings.template_value)
        self.assertNotIn("Relatório privado", self.calls[0].content.decode())

    def test_invalid_configuration_fails_startup(self):
        for settings in [replace(self.settings, token="short"), replace(self.settings, graph_version=""),
                         replace(self.settings, recipients={"owner":("group@g.us",)}),
                         replace(self.settings, mode="template", templates={})]:
            with self.assertRaises(ValueError):
                with self.client(settings):
                    pass
