"""Server-owned catalog, private guest carts and restricted draft orders. No payment acceptance."""
import json
import re
import secrets
from pathlib import Path
from .security import admin, digest, fail, text, uid

SIZES=('P','M','G','GG')


def seed_catalog(db):
    for p in json.loads(Path(__file__).with_name('shop_catalog.json').read_text(encoding='utf-8')):
        db.execute('INSERT INTO produtos_loja(cod_identificador,txt_nome,txt_estilo,txt_cor,txt_imagem) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (p['id'],p['name'],p['style'],p['color'],p['image']))
        for size in SIZES:
            db.execute('INSERT INTO variantes_produtos_loja(cod_identificador,cod_produto,txt_tamanho,num_preco_centavos) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                       (p['id']+':'+size,p['id'],size,p['priceCents']))


def catalog(db):
    products=list(db.execute('SELECT cod_identificador AS id,txt_nome AS name,txt_estilo AS style,txt_cor AS color,txt_imagem AS image FROM produtos_loja WHERE flg_ativo ORDER BY cod_identificador'))
    variants=list(db.execute('SELECT v.cod_identificador AS "variantId",v.cod_produto AS id,v.txt_tamanho AS size,v.num_preco_centavos AS "unitPriceCents",CASE WHEN v.num_estoque IS NULL THEN NULL ELSE v.num_estoque-v.num_reservado END AS available FROM variantes_produtos_loja v JOIN produtos_loja p ON p.cod_identificador=v.cod_produto WHERE v.flg_ativo AND p.flg_ativo ORDER BY v.cod_identificador'))
    return {'products':products,'variants':variants,'checkoutEnabled':False}


def find_cart(db,token,lock=False,converted=False):
    if not isinstance(token,str) or not re.fullmatch('[a-f0-9]{64}',token):fail(403,'Acesso ao carrinho inválido ou expirado.')
    row=db.execute('SELECT cod_identificador AS "cartId",num_versao AS version,txt_estado AS state FROM carrinhos_loja WHERE txt_token_hash=%s AND dat_expiracao>now()'+('' if converted else " AND txt_estado='active'")+(' FOR UPDATE' if lock else ''),(digest(token),)).fetchone()
    if not row:fail(403,'Acesso ao carrinho inválido ou expirado.')
    return row


def validated_items(db,items):
    if not isinstance(items,list) or len(items)>44:fail(400,'Confira os itens do carrinho.')
    result=[];seen=set()
    for item in items:
        if not isinstance(item,dict):fail(400,'Item inválido.')
        product=item.get('id');size=item.get('size');quantity=item.get('quantity')
        if not isinstance(product,str) or len(product)>100 or size not in SIZES or type(quantity) is not int or not 1<=quantity<=99:fail(400,'Confira estampa, tamanho e quantidade (1 a 99).')
        key=product+':'+size
        if key in seen:fail(400,'Agrupe os itens de mesma estampa e tamanho.')
        seen.add(key)
        variant=db.execute('SELECT v.cod_identificador AS "variantId",v.num_preco_centavos AS "unitPriceCents",v.num_estoque AS stock,v.num_reservado AS reserved FROM variantes_produtos_loja v JOIN produtos_loja p ON p.cod_identificador=v.cod_produto WHERE v.cod_identificador=%s AND v.flg_ativo AND p.flg_ativo FOR SHARE OF v,p',(key,)).fetchone()
        if not variant:fail(409,'Uma das estampas ou tamanhos não está disponível. Atualize o catálogo.')
        if variant['stock'] is not None and quantity>variant['stock']-variant['reserved']:fail(409,'A quantidade solicitada supera a disponibilidade atual.')
        result.append({**variant,'quantity':quantity})
    return result


def cart_result(db,cart):
    items=list(db.execute('SELECT p.cod_identificador AS id,v.cod_identificador AS "variantId",v.txt_tamanho AS size,i.num_quantidade AS quantity,v.num_preco_centavos AS "unitPriceCents",(p.flg_ativo AND v.flg_ativo) AS active FROM itens_carrinhos_loja i JOIN variantes_produtos_loja v ON v.cod_identificador=i.cod_variante JOIN produtos_loja p ON p.cod_identificador=v.cod_produto WHERE i.cod_carrinho=%s ORDER BY i.cod_variante',(cart['cartId'],)))
    return {'version':cart['version'],'items':items,'totalCents':sum(i['quantity']*i['unitPriceCents'] for i in items),'checkoutEnabled':False}


def create_cart(db,body):
    items=validated_items(db,body.get('items',[]));token=secrets.token_hex(32);cid=uid()
    db.execute('INSERT INTO carrinhos_loja(cod_identificador,txt_token_hash) VALUES(%s,%s)',(cid,digest(token)))
    for item in items:db.execute('INSERT INTO itens_carrinhos_loja VALUES(%s,%s,%s)',(cid,item['variantId'],item['quantity']))
    return {**cart_result(db,{'cartId':cid,'version':0}),'token':token}


def replace_cart(db,body):
    cart=find_cart(db,body.get('token'),lock=True)
    if type(body.get('version')) is not int or body['version']!=cart['version']:fail(409,'O carrinho mudou em outra aba. Recarregue sua seleção.')
    items=validated_items(db,body.get('items'))
    db.execute('DELETE FROM itens_carrinhos_loja WHERE cod_carrinho=%s',(cart['cartId'],))
    for item in items:db.execute('INSERT INTO itens_carrinhos_loja VALUES(%s,%s,%s)',(cart['cartId'],item['variantId'],item['quantity']))
    db.execute("UPDATE carrinhos_loja SET num_versao=num_versao+1,dat_atualizacao=now(),dat_expiracao=now()+interval '30 days' WHERE cod_identificador=%s",(cart['cartId'],))
    cart['version']+=1
    return cart_result(db,cart)


def draft_order(db,body,user):
    cart=find_cart(db,body.get('token'),lock=True,converted=True)
    key=text(body.get('idempotencyKey'),100)
    existing=db.execute('SELECT cod_identificador AS id,cod_carrinho AS "cartId",txt_estado AS state,num_total_centavos AS "totalCents" FROM pedidos_loja WHERE txt_chave_idempotencia=%s',(key,)).fetchone()
    if existing:
        if existing['cartId']!=cart['cartId']:fail(409,'Chave já usada em outro pedido.')
        return existing
    if cart['state']!='active':fail(409,'Carrinho já convertido.')
    current=cart_result(db,cart)
    if not current['items']:fail(400,'O carrinho está vazio.')
    validated_items(db,current['items'])
    current=cart_result(db,cart)
    order=uid();total=current['totalCents']
    db.execute('INSERT INTO pedidos_loja(cod_identificador,cod_carrinho,txt_chave_idempotencia,num_subtotal_centavos,num_total_centavos) VALUES(%s,%s,%s,%s,%s)',(order,cart['cartId'],key,total,total))
    db.execute('INSERT INTO itens_pedidos_loja(cod_identificador,cod_pedido,cod_variante,txt_nome_produto,txt_estilo,txt_cor,txt_tamanho,num_preco_centavos,num_quantidade) SELECT %s||v.cod_identificador,%s,v.cod_identificador,p.txt_nome,p.txt_estilo,p.txt_cor,v.txt_tamanho,v.num_preco_centavos,i.num_quantidade FROM itens_carrinhos_loja i JOIN variantes_produtos_loja v ON v.cod_identificador=i.cod_variante JOIN produtos_loja p ON p.cod_identificador=v.cod_produto WHERE i.cod_carrinho=%s',(order+':',order,cart['cartId']))
    db.execute("INSERT INTO historico_pedidos_loja(cod_identificador,cod_pedido,txt_estado_novo,txt_motivo,cod_usuario) VALUES(%s,%s,'draft','Rascunho administrativo; sem cobrança ou reserva de estoque.',%s)",(uid(),order,user['id']))
    db.execute("UPDATE carrinhos_loja SET txt_estado='converted',dat_atualizacao=now() WHERE cod_identificador=%s",(cart['cartId'],))
    return {'id':order,'state':'draft','totalCents':total}


def route(db,path,method,body,user,throttle):
    if path=='shop/products' and method=='GET':return catalog(db),200
    if path=='shop/cart' and method=='POST':throttle('shop-cart-create',30);return create_cart(db,body),201
    if path=='shop/cart/read' and method=='POST':throttle('shop-cart-read',150);return cart_result(db,find_cart(db,body.get('token'))),200
    if path=='shop/cart' and method=='PUT':throttle('shop-cart-update',150);return replace_cart(db,body),200
    if path=='shop/orders' and method=='GET':
        admin(user)
        return {'orders':list(db.execute('SELECT cod_identificador AS id,txt_estado AS state,num_total_centavos AS "totalCents",dat_cadastro AS created FROM pedidos_loja ORDER BY dat_cadastro DESC LIMIT 100'))},200
    if path=='shop/orders/draft' and method=='POST':
        admin(user)
        return draft_order(db,body,user),201
    fail(404,'Recurso da loja não encontrado.')
