"""PostgreSQL connections and initial creation from the current schema."""
import json
import os
import re
from pathlib import Path

from psycopg import sql
from psycopg_pool import ConnectionPool
from .naming import REVERSE_COLUMNS, decode_value

ROOT = Path(__file__).resolve().parent.parent


def portuguese_row(cursor):
    keys = [REVERSE_COLUMNS.get(c.name, c.name) for c in cursor.description] if cursor.description else []
    return lambda values: {key:decode_value(key,value) for key,value in zip(keys,values)}


def make_pool(url=None):
    return ConnectionPool(url or os.environ['DATABASE_URL'], min_size=1, max_size=10,
                          kwargs={'row_factory': portuguese_row}, open=False)


def initialize_database(pool):
    with pool.connection() as db:
        db.execute('SELECT pg_advisory_xact_lock(742091)')
        content=(ROOT/'backend/schema.sql').read_text(encoding='utf-8')+'\n'+(ROOT/'backend/shop_schema.sql').read_text(encoding='utf-8')
        tables=re.findall(r'CREATE TABLE ([a-z_]+)\s*\((.*?)\);',content,re.S)
        existing={r['table_name'] for r in db.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()')}
        expected={name for name,_ in tables}
        if not existing.intersection(expected):
            db.execute(content)
            from .shop import seed_catalog
            seed_catalog(db)
        else:
            if not expected.issubset(existing):
                raise RuntimeError('Banco incompleto. Confira backend/schema.sql antes de iniciar a aplicação.')
            # Check required columns without altering populated tables.
            for name,definition in tables:
                columns=re.findall(r'\b((?:cod|txt|num|dat|hor|flg|bin)_[a-z_]+)\s+(?:text|integer|bigint|double precision|timestamptz|date|time|boolean|bytea)\b',definition)
                db.execute(sql.SQL('SELECT {} FROM {} LIMIT 0').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(name)))
        db.execute("INSERT INTO configuracoes VALUES('segredo_cpf',%s) ON CONFLICT DO NOTHING", (os.urandom(32).hex(),))


def seed_demo(pool):
    from .repository import insert_cat
    from datetime import datetime
    from .security import LOCAL_TZ
    path = ROOT / 'backend/seed.json'
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
        initialize_database(pool)
