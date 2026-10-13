"""Durable PostgreSQL outbox with leases and weekly report deduplication."""
import logging
import os
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx

from .db import make_pool
from .security import now, LOCAL_TZ
from .repository import medical, cats
from .schedule import medication_schedule, unscheduled
from .app import queue


def weekly_report(pool, current=None):
    local=(current or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ)
    if local.weekday()!=4: return
    start=(local+timedelta(days=1)).strftime('%Y-%m-%d'); end=(local+timedelta(days=2)).strftime('%Y-%m-%d')
    with pool.connection() as db:
        records=medical(db); names={c['id']:c['name'] for c in cats(db)}
        schedule=medication_schedule(records,start,end)
        message='Medicações do fim de semana '+start+' a '+end+'\n'
        message+='\n'.join(f"{'[x]' if s['applied'] else '[ ]'} {s['date']} {s['time']} · {names.get(s['catId'],s['catId'])} · {s['label']} · {s['dose']}" for s in schedule) or 'Nenhuma dose programada.'
        count=unscheduled(records)
        if count: message+=f'\nAtenção: {count} tratamento(s) sem intervalo estruturado. Conferir a prescrição no sistema.'
        queue(db,'weekend:'+start,'volunteers',message)


def dispatch_messages(pool, client=None):
    endpoint=os.getenv('WHATSAPP_WEBHOOK_URL',''); token=os.getenv('WHATSAPP_WEBHOOK_TOKEN','')
    if not endpoint or not token: return
    parts=urlparse(endpoint)
    if parts.username or parts.password or not parts.hostname: return
    if parts.scheme!='https' and not (parts.scheme=='http' and parts.hostname in ('localhost','127.0.0.1','gateway','::1')): return
    owned=client is None
    client=client or httpx.Client(timeout=15,follow_redirects=False,trust_env=False)
    try:
        for _ in range(20):
            # Commit lease before I/O. SKIP LOCKED allows multiple workers.
            with pool.connection() as db:
                job=db.execute('SELECT * FROM fila_mensagens WHERE dat_envio IS NULL AND num_tentativas<10 AND dat_proxima_tentativa<=to_timestamp(%s/1000.0) ORDER BY dat_cadastro FOR UPDATE SKIP LOCKED LIMIT 1',(now(),)).fetchone()
                if not job: break
                target=os.getenv('WHATSAPP_OWNER_TARGET' if job['target']=='owner' else 'WHATSAPP_VOLUNTEERS_TARGET','')
                lease=now()+120000
                db.execute('UPDATE fila_mensagens SET dat_proxima_tentativa=to_timestamp(%s/1000.0) WHERE cod_identificador=%s',(lease,job['id']))
            if not target: continue
            try:
                r=client.post(endpoint,headers={'Authorization':'Bearer '+token,'Idempotency-Key':job['id']},
                              json={'id':job['id'],'target':target,'text':job['message']})
                r.raise_for_status(); receipt=r.json()
                if receipt.get('id')!=job['id'] or receipt.get('accepted') is not True or receipt.get('simulated') is not False:
                    raise ValueError('Gateway não confirmou a aceitação real da mensagem.')
                with pool.connection() as db:
                    db.execute('UPDATE fila_mensagens SET dat_envio=to_timestamp(%s/1000.0),txt_ultimo_erro=NULL WHERE cod_identificador=%s AND dat_proxima_tentativa=to_timestamp(%s/1000.0)',(now(),job['id'],lease))
            except (httpx.HTTPError,ValueError,TypeError) as error:
                with pool.connection() as db:
                    db.execute('UPDATE fila_mensagens SET num_tentativas=num_tentativas+1,dat_proxima_tentativa=to_timestamp(%s/1000.0),txt_ultimo_erro=%s WHERE cod_identificador=%s AND dat_proxima_tentativa=to_timestamp(%s/1000.0)',
                               (now()+min(3600000,60000*2**job['attempts']),str(error)[:200],job['id'],lease))
    finally:
        if owned: client.close()


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    with make_pool() as pool:
        while True:
            try:
                weekly_report(pool); dispatch_messages(pool)
                with pool.connection() as db:
                    db.execute('DELETE FROM limites_requisicoes WHERE dat_expiracao<to_timestamp(%s/1000.0)',(now(),))
                    db.execute('DELETE FROM sessoes WHERE dat_expiracao<to_timestamp(%s/1000.0)',(now(),))
            except Exception:
                logging.exception('Falha no processamento de mensagens')
            time.sleep(60)
