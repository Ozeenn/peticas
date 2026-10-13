"""Peticas -> gateway autenticado -> WhatsApp Cloud API.

O SQLite guarda hashes, estados e IDs da Meta, sem o texto das mensagens.
Uma chamada interrompida fica bloqueada para reconciliação, pois a Meta não
oferece aqui uma garantia de envio único baseada na chave do Peticas.
"""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool


@dataclass(frozen=True)
class Settings:
    token: str
    recipients: dict[str, tuple[str, ...]]
    db_path: str
    dry_run: bool = True
    access_token: str = ""
    phone_number_id: str = ""
    graph_version: str = ""
    mode: str = "template"
    templates: dict[str, str] | None = None
    language: str = "pt_BR"
    template_value: str = ""

    @classmethod
    def from_env(cls):
        def numbers(name):
            return tuple(dict.fromkeys(n.strip() for n in os.getenv(name, "").split(",") if n.strip()))
        dry_run = os.getenv("WHATSAPP_DRY_RUN", "true").lower()
        if dry_run not in ("true", "false"):
            raise ValueError("WHATSAPP_DRY_RUN deve ser true ou false.")
        return cls(
            token=os.getenv("PETICAS_GATEWAY_TOKEN", ""),
            recipients={"owner": numbers("WHATSAPP_OWNER_NUMBERS"), "volunteers": numbers("WHATSAPP_VOLUNTEERS_NUMBERS")},
            db_path=os.getenv("WHATSAPP_GATEWAY_DB", "data/whatsapp-gateway.sqlite"),
            dry_run=dry_run == "true", access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            graph_version=os.getenv("WHATSAPP_GRAPH_VERSION", ""),
            mode=os.getenv("WHATSAPP_MESSAGE_MODE", "template"),
            templates={"owner": os.getenv("WHATSAPP_OWNER_TEMPLATE", ""), "volunteers": os.getenv("WHATSAPP_VOLUNTEERS_TEMPLATE", "")},
            language=os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "pt_BR"),
            template_value=os.getenv("WHATSAPP_TEMPLATE_BODY_VALUE", ""),
        )

    def validate(self):
        if len(self.token) < 32 or not self.token.isascii():
            raise ValueError("PETICAS_GATEWAY_TOKEN precisa de pelo menos 32 caracteres ASCII.")
        if self.mode not in ("text", "template"):
            raise ValueError("WHATSAPP_MESSAGE_MODE deve ser text ou template.")
        if not any(self.recipients.values()):
            raise ValueError("Configure pelo menos um destinatário.")
        for recipients in self.recipients.values():
            if len(recipients) > 20 or any(not re.fullmatch(r"[1-9]\d{7,14}", n) for n in recipients):
                raise ValueError("Use até 20 telefones por destino, com código do país e somente dígitos.")
        if not self.dry_run:
            if not self.access_token or not re.fullmatch(r"\d+", self.phone_number_id) or not re.fullmatch(r"v\d+\.\d+", self.graph_version):
                raise ValueError("Configure token, ID do telefone e versão da Graph API.")
            if self.mode == "template":
                for target, recipients in self.recipients.items():
                    if recipients and not re.fullmatch(r"[a-z0-9_]+", (self.templates or {}).get(target, "")):
                        raise ValueError("Configure um modelo aprovado para cada destino ativo.")
                if not self.template_value or len(self.template_value) > 1024 or any(c in self.template_value for c in "\n\r\t"):
                    raise ValueError("Configure o parâmetro único de corpo do modelo (até 1024 caracteres, sem quebras).")


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9:_-]+$")
    target: str = Field(pattern=r"^(owner|volunteers)$")
    text: str = Field(min_length=1, max_length=32000)


class Store:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deliveries(
                    job_id TEXT NOT NULL, recipient_hash TEXT NOT NULL,
                    state TEXT NOT NULL, meta_id TEXT, updated INTEGER NOT NULL,
                    PRIMARY KEY(job_id, recipient_hash));
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self, job_id, fingerprint, recipient_hash):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO jobs VALUES(?,?)", (job_id, fingerprint))
            stored = db.execute("SELECT fingerprint FROM jobs WHERE id=?", (job_id,)).fetchone()[0]
            if stored != fingerprint:
                raise HTTPException(409, "Chave já utilizada para outro conteúdo ou configuração.")
            row = db.execute("SELECT state,meta_id FROM deliveries WHERE job_id=? AND recipient_hash=?", (job_id, recipient_hash)).fetchone()
            if row:
                if row[0] == "accepted":
                    return row[1]
                if row[0] in ("sending", "uncertain"):
                    raise HTTPException(409, "Envio em andamento ou incerto; confira antes de reenviar.")
            db.execute("INSERT INTO deliveries VALUES(?,?, 'sending',NULL,?) ON CONFLICT(job_id,recipient_hash) DO UPDATE SET state='sending',updated=excluded.updated", (job_id, recipient_hash, int(time.time())))
            return None

    def finish(self, job_id, recipient_hash, state, meta_id=None):
        with self.connection() as db:
            db.execute("UPDATE deliveries SET state=?,meta_id=?,updated=? WHERE job_id=? AND recipient_hash=?", (state, meta_id, int(time.time()), job_id, recipient_hash))


def build_payload(settings, message, recipient):
    payload = {"messaging_product": "whatsapp", "to": recipient}
    if settings.mode == "text":
        if len(message.text) > 4096:
            raise HTTPException(422, "Texto acima do limite de 4096 caracteres; divida o aviso na origem.")
        payload.update(type="text", text={"body": message.text, "preview_url": False})
    else:
        payload.update(type="template", template={
            "name": (settings.templates or {}).get(message.target, ""),
            "language": {"code": settings.language},
            "components": [{"type": "body", "parameters": [{"type": "text", "text": settings.template_value}]}],
        })
    return payload


def deliver(settings, store, client, message):
    recipients = settings.recipients.get(message.target, ())
    if not recipients:
        raise HTTPException(422, "Destino sem destinatários configurados.")
    payloads = [build_payload(settings, message, n) for n in recipients]
    if settings.dry_run:
        return {"id": message.id, "accepted": False, "simulated": True, "recipients": len(recipients)}
    # Incluir configuração efetiva impede reuso silencioso após mudar destinatários/modelos.
    fingerprint = hashlib.sha256(json.dumps({"text": message.text, "payloads": payloads, "sender": settings.phone_number_id}, sort_keys=True).encode()).hexdigest()
    message_ids = []
    start = time.monotonic()
    for recipient, payload in zip(recipients, payloads):
        if time.monotonic() - start > 8:
            raise HTTPException(503, "Lote parcial; a próxima tentativa continua pelos destinatários restantes.")
        recipient_hash = hashlib.sha256(recipient.encode()).hexdigest()
        existing = store.claim(message.id, fingerprint, recipient_hash)
        if existing:
            message_ids.append(existing)
            continue
        try:
            response = client.post(
                f"https://graph.facebook.com/{settings.graph_version}/{settings.phone_number_id}/messages",
                headers={"Authorization": "Bearer " + settings.access_token}, json=payload,
            )
        except httpx.RequestError:
            store.finish(message.id, recipient_hash, "uncertain")
            raise HTTPException(503, "Resultado incerto na Meta; confira o envio antes de liberar nova tentativa.") from None
        if not response.is_success:
            # Resposta explícita de rejeição permite nova tentativa. Erros de servidor
            # podem ocorrer depois do processamento: preservar como incertos.
            store.finish(message.id, recipient_hash, "rejected" if 400 <= response.status_code < 500 else "uncertain")
            raise HTTPException(502, f"Meta retornou HTTP {response.status_code}; consulte o painel da Meta.")
        try:
            meta_id = response.json()["messages"][0]["id"]
            if not isinstance(meta_id, str) or not meta_id:
                raise ValueError()
        except (ValueError, KeyError, IndexError, TypeError):
            store.finish(message.id, recipient_hash, "uncertain")
            raise HTTPException(502, "Resposta da Meta sem identificação; envio precisa de conferência.") from None
        store.finish(message.id, recipient_hash, "accepted", meta_id)
        message_ids.append(meta_id)
    return {"id": message.id, "accepted": True, "simulated": False, "message_ids": message_ids}


def create_app(settings=None, client=None):
    @asynccontextmanager
    async def lifespan(app):
        config = settings or Settings.from_env()
        config.validate()
        app.state.settings = config
        app.state.store = Store(config.db_path)
        app.state.client = client or httpx.Client(timeout=5, follow_redirects=False, trust_env=False)
        try:
            yield
        finally:
            if client is None:
                app.state.client.close()

    app = FastAPI(title="Peticas WhatsApp", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health():
        return {"ok": True, "simulated": app.state.settings.dry_run}

    @app.post("/messages")
    async def messages(request: Request):
        config = app.state.settings
        expected = "Bearer " + config.token
        if not hmac.compare_digest(request.headers.get("authorization", "").encode(), expected.encode()):
            raise HTTPException(401, "Autenticação inválida.")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 65536:
                raise HTTPException(413, "Mensagem muito grande.")
        try:
            message = Message.model_validate_json(bytes(raw))
        except ValidationError:
            raise HTTPException(422, "Informe id, target (owner/volunteers) e text válidos.") from None
        if request.headers.get("idempotency-key") != message.id:
            raise HTTPException(400, "Idempotency-Key deve corresponder ao id da mensagem.")
        return await run_in_threadpool(deliver, config, app.state.store, app.state.client, message)

    return app


app = create_app()
