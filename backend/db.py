"""PostgreSQL connections and immutable, checksummed SQL migrations."""
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg_pool import ConnectionPool
from .naming import REVERSE_COLUMNS, decode_value

ROOT = Path(__file__).resolve().parent.parent


def portuguese_row(cursor):
    keys = [REVERSE_COLUMNS.get(c.name, c.name) for c in cursor.description] if cursor.description else []
    return lambda values: {key:decode_value(key,value) for key,value in zip(keys,values)}


def make_pool(url=None):
    return ConnectionPool(url or os.environ['DATABASE_URL'], min_size=1, max_size=10,
                          kwargs={'row_factory': portuguese_row}, open=False)


def migrate(pool):
    with pool.connection() as db:
        db.execute('SELECT pg_advisory_xact_lock(742091)')
        db.execute('CREATE TABLE IF NOT EXISTS migracoes_esquema(txt_nome text PRIMARY KEY, txt_verificacao_hash text NOT NULL)')
        for path in sorted((ROOT / 'backend/migrations').glob('*.sql')):
            content = path.read_text(encoding='utf-8')
            checksum = hashlib.sha256(content.encode()).hexdigest()
            row = db.execute('SELECT txt_verificacao_hash FROM migracoes_esquema WHERE txt_nome=%s', (path.name,)).fetchone()
            if row:
                if row['checksum'] != checksum:
                    raise RuntimeError('Migração aplicada foi alterada: ' + path.name)
                continue
            db.execute(content)
            db.execute('INSERT INTO migracoes_esquema VALUES(%s,%s)', (path.name, checksum))
        db.execute("INSERT INTO configuracoes VALUES('segredo_cpf',%s) ON CONFLICT DO NOTHING", (os.urandom(32).hex(),))


def seed_demo(pool):
    from .repository import insert_cat
    from datetime import datetime
    from .security import LOCAL_TZ
    path = ROOT / 'backend/seed.json'
    if not path.exists():
        path = ROOT / 'server/seed.json'
    with pool.connection() as db:
        db.execute('SELECT pg_advisory_xact_lock(742091)')
        if db.execute("SELECT 1 FROM configuracoes WHERE txt_chave='demo-seeded'").fetchone():
            return
        if not db.execute('SELECT 1 FROM gatos LIMIT 1').fetchone():
            for cat in json.loads(path.read_text(encoding='utf-8'))['cats']:
                cat.update(color='Não informada (exemplo)',entryDate=datetime.now(LOCAL_TZ).strftime('%Y-%m-%d'),
                           rescueLocation='Cadastro demonstrativo',rescuer='Equipe (exemplo)',
                           rescueReport='Registro fictício para demonstrar o cadastro do gatil.')
                if cat['status']=='Reservado':
                    cat['status']='Disponível'
                insert_cat(db, cat)
            # Dated care examples in the old seed are intentionally not reused.
        db.execute("INSERT INTO configuracoes VALUES('demo-seeded','true')")


if __name__ == '__main__':
    with make_pool() as pool:
        migrate(pool)
