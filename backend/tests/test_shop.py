from concurrent.futures import ThreadPoolExecutor
import uuid
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest
from backend.tests.test_api import client, call, register, URL
from backend.db import ROOT, make_pool, initialize_database
from backend.shop_migrate import migrate
from backend.security import digest

pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL')


def test_catalog_private_carts_prices_and_versions(client):
    c=client
    catalog=call(c,'shop/products').json()
    assert len(catalog['products'])==11 and len(catalog['variants'])==44
    assert catalog['checkoutEnabled'] is False
    assert all(v['available'] is None for v in catalog['variants'])
    created=call(c,'shop/cart','POST',{'items':[{'id':'marina','size':'M','quantity':2,'unitPriceCents':1}],'totalCents':2})
    assert created.status_code==201,created.text
    cart=created.json();token=cart['token']
    assert len(token)==64 and cart['totalCents']==9998
    with c.app.state.pool.connection() as db:
        assert db.execute('SELECT txt_token_hash FROM carrinhos_loja').fetchone()['token_hash']==digest(token)
    assert call(c,'shop/cart/read','POST',{'token':'wrong'}).status_code==403
    other=call(c,'shop/cart','POST',{}).json()
    assert call(c,'shop/cart/read','POST',{'token':other['token']}).json()['items']==[]
    update={'token':token,'version':cart['version'],'items':[{'id':'marina','size':'M','quantity':1},{'id':'marina','size':'G','quantity':1}]}
    saved=call(c,'shop/cart','PUT',update)
    assert saved.status_code==200 and saved.json()['totalCents']==9998
    assert call(c,'shop/cart','PUT',update).status_code==409
    assert len(call(c,'shop/cart/read','POST',{'token':token}).json()['items'])==2
    assert c.put('/api/shop/cart',json={**update,'version':1},headers={'Origin':'https://other.test'}).status_code==403
    assert call(c,'shop/cart','PUT',{'token':token,'version':1,'items':[]}).json()['items']==[]
    with c.app.state.pool.connection() as db:db.execute("UPDATE carrinhos_loja SET dat_expiracao=now()-interval '1 second' WHERE txt_token_hash=%s",(digest(token),))
    assert call(c,'shop/cart/read','POST',{'token':token}).status_code==403


def test_cart_availability_invalid_items_and_concurrent_updates(client):
    c=client
    for item in [{'id':'missing','size':'M','quantity':1},{'id':'marina','size':'XXL','quantity':1},{'id':'marina','size':'P','quantity':True},{'id':'marina','size':'P','quantity':1.5}]:
        assert call(c,'shop/cart','POST',{'items':[item]}).status_code in (400,409)
    with c.app.state.pool.connection() as db:db.execute("UPDATE variantes_produtos_loja SET num_estoque=2,num_reservado=1 WHERE cod_identificador='marina:P'")
    assert call(c,'shop/cart','POST',{'items':[{'id':'marina','size':'P','quantity':2}]}).status_code==409
    cart=call(c,'shop/cart','POST',{'items':[{'id':'marina','size':'P','quantity':1}]}).json()
    def update(size):return call(c,'shop/cart','PUT',{'token':cart['token'],'version':0,'items':[{'id':'marina','size':size,'quantity':1}]}).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:statuses=list(executor.map(update,['M','G']))
    assert sorted(statuses)==[200,409]


def test_draft_orders_are_admin_only_idempotent_and_preserve_item_snapshots(client):
    c=client
    cart=call(c,'shop/cart','POST',{'items':[{'id':'marina','size':'M','quantity':2}]}).json()
    body={'token':cart['token'],'idempotencyKey':'test-order-key'}
    assert call(c,'shop/orders/draft','POST',body).status_code==401
    assert call(c,'shop/orders').status_code==401
    register(c)
    result=call(c,'shop/orders/draft','POST',body)
    assert result.status_code==201,result.text
    order=result.json();assert order['state']=='draft' and order['totalCents']==9998
    assert call(c,'shop/orders/draft','POST',body).json()['id']==order['id']
    assert len(call(c,'shop/orders').json()['orders'])==1
    with c.app.state.pool.connection() as db:
        db.execute("UPDATE variantes_produtos_loja SET num_preco_centavos=7000 WHERE cod_identificador='marina:M'")
        item=db.execute('SELECT num_preco_centavos,num_quantidade,num_total_centavos FROM itens_pedidos_loja WHERE cod_pedido=%s',(order['id'],)).fetchone()
        assert item['num_preco_centavos']==4999 and item['num_total_centavos']==9998
        assert db.execute('SELECT count(*) AS amount FROM pagamentos_loja').fetchone()['amount']==0
        assert db.execute('SELECT count(*) AS amount FROM historico_pedidos_loja').fetchone()['amount']==1
        db.execute("INSERT INTO pagamentos_loja(cod_identificador,cod_pedido,txt_provedor,txt_chave_idempotencia,num_valor_centavos) VALUES('payment',%s,'test','test-payment',9998)",(order['id'],))
        with pytest.raises(psycopg.errors.CheckViolation):
            with db.transaction():db.execute("UPDATE pagamentos_loja SET txt_estado='fake-paid' WHERE cod_identificador='payment'")
        db.execute("INSERT INTO eventos_pagamentos_loja(cod_identificador,txt_provedor,txt_evento_externo,txt_tipo,txt_conteudo_hash) VALUES('event','test','same-event','payment','hash')")
        with pytest.raises(psycopg.errors.UniqueViolation):
            with db.transaction():db.execute("INSERT INTO eventos_pagamentos_loja(cod_identificador,txt_provedor,txt_evento_externo,txt_tipo,txt_conteudo_hash) VALUES('event2','test','same-event','payment','hash')")
    assert call(c,'shop/checkout','POST',body).status_code==404


def test_explicit_migration_is_additive_repeatable_and_installs_real_catalog():
    schema='shop_migration_'+uuid.uuid4().hex
    with psycopg.connect(URL,autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        with make_pool(make_conninfo(URL,options='-c search_path='+schema)) as pool:
            with pool.connection() as db:
                db.execute((ROOT/'backend/schema.sql').read_text(encoding='utf-8'))
                db.execute("INSERT INTO configuracoes VALUES('sentinel','keep')")
            migrate(pool);migrate(pool);initialize_database(pool)
            with pool.connection() as db:
                assert db.execute("SELECT txt_valor FROM configuracoes WHERE txt_chave='sentinel'").fetchone()['value']=='keep'
                assert db.execute('SELECT count(*) AS amount FROM produtos_loja').fetchone()['amount']==11
                assert db.execute('SELECT count(*) AS amount FROM variantes_produtos_loja').fetchone()['amount']==44
    finally:
        with psycopg.connect(URL,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
