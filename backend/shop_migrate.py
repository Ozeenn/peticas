"""Explicit, additive shop migration. Never alters adoption tables or existing products."""
import re
from .db import make_pool, ROOT
from .shop import seed_catalog


def migrate(pool):
    content=(ROOT/'backend/shop_schema.sql').read_text(encoding='utf-8')
    expected=set(re.findall(r'CREATE TABLE ([a-z_]+)',content))
    with pool.connection() as db:
        db.execute('SELECT pg_advisory_xact_lock(742091)')
        existing={r['table_name'] for r in db.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()')}
        present=expected.intersection(existing)
        if present and present!=expected:
            raise RuntimeError('Estrutura parcial da loja. Revise a instalação antes de continuar.')
        if not present:
            db.execute(content)
            seed_catalog(db)
        print('Estrutura da loja verificada:',len(expected),'tabelas.')


if __name__=='__main__':
    with make_pool() as pool:
        migrate(pool)
