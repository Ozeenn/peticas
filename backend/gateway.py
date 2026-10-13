"""WhatsApp gateway with PostgreSQL persistence."""
from contextlib import contextmanager
import os
import time
import psycopg
from fastapi import HTTPException
from .db import portuguese_row
from .whatsapp import create_app as create_whatsapp_app


class PostgresStore:
    def __init__(self):
        self.url=os.environ['DATABASE_URL']

    @contextmanager
    def connection(self):
        with psycopg.connect(self.url,row_factory=portuguese_row) as db:
            yield db

    def claim(self, job_id, fingerprint, recipient_hash):
        with self.connection() as db:
            db.execute('INSERT INTO envios_whatsapp VALUES(%s,%s) ON CONFLICT DO NOTHING',(job_id,fingerprint))
            job=db.execute('SELECT txt_impressao_hash FROM envios_whatsapp WHERE cod_identificador=%s FOR UPDATE',(job_id,)).fetchone()
            if job['fingerprint']!=fingerprint: raise HTTPException(409,'Chave já utilizada para outro conteúdo ou configuração.')
            row=db.execute('SELECT txt_estado,txt_identificador_meta FROM entregas_whatsapp WHERE cod_envio=%s AND txt_destinatario_hash=%s',(job_id,recipient_hash)).fetchone()
            if row:
                if row['state']=='accepted': return row['meta_id']
                if row['state'] in ('sending','uncertain'): raise HTTPException(409,'Envio em andamento ou incerto; confira antes de reenviar.')
            db.execute("INSERT INTO entregas_whatsapp VALUES(%s,%s,'sending',NULL,to_timestamp(%s)) ON CONFLICT(cod_envio,txt_destinatario_hash) DO UPDATE SET txt_estado='sending',dat_atualizacao=excluded.dat_atualizacao",(job_id,recipient_hash,int(time.time())))
            return None

    def finish(self, job_id, recipient_hash, state, meta_id=None):
        with self.connection() as db:
            db.execute('UPDATE entregas_whatsapp SET txt_estado=%s,txt_identificador_meta=%s,dat_atualizacao=to_timestamp(%s) WHERE cod_envio=%s AND txt_destinatario_hash=%s',
                       (state,meta_id,int(time.time()),job_id,recipient_hash))


def create_app():
    return create_whatsapp_app(store_factory=PostgresStore)


app=create_app()
