from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import threading

import httpx
from fastapi.testclient import TestClient
import pytest

from backend.gateway import PostgresStore
from backend.whatsapp import Settings, create_app
from backend.tests.test_api import client, URL

pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL')


def test_gateway_postgres_receipts_deduplication_and_uncertain_delivery(client,monkeypatch):
    monkeypatch.setenv('DATABASE_URL',client.app.state.pool.conninfo)
    calls=[]
    def mock(request):
        calls.append(request)
        return httpx.Response(200,json={'messages':[{'id':'wamid.test'}]})
    settings=Settings(token='a'*40,recipients={'owner':('5511999999999',),'volunteers':()},
                      dry_run=False,access_token='fake-meta-token',phone_number_id='12345',graph_version='v99.0',mode='text')
    headers={'Authorization':'Bearer '+settings.token,'Idempotency-Key':'adoption:test'}
    payload={'id':'adoption:test','target':'owner','text':'Nova candidatura'}
    with httpx.Client(transport=httpx.MockTransport(mock)) as meta:
        for _ in range(2):
            with TestClient(create_app(settings,meta,store_factory=PostgresStore)) as gateway:
                result=gateway.post('/messages',json=payload,headers=headers)
                assert result.status_code==200,result.text
                assert result.json()['accepted'] is True
                assert gateway.post('/messages',json={**payload,'text':'Outro texto'},headers=headers).status_code==409
        assert len(calls)==1
    store=PostgresStore()
    assert store.claim('incerto','hash','destino') is None
    store.finish('incerto','destino','uncertain')
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error: store.claim('incerto','hash','destino')
    assert error.value.status_code==409
    with client.app.state.pool.connection() as db:
        assert db.execute("SELECT txt_estado FROM entregas_whatsapp WHERE cod_envio='adoption:test'").fetchone()['state']=='accepted'
        assert db.execute('SELECT count(*) FROM fila_mensagens').fetchone()['count']==0
