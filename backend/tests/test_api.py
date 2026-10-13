import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import re
import uuid
import time

import httpx
import psycopg
from psycopg import sql
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db import initialize_database
from backend.jobs import weekly_report, dispatch_messages
from backend.security import LOCAL_TZ

URL=os.getenv('PETICAS_TEST_DATABASE_URL')
pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL para um PostgreSQL de teste')
PASSWORD='Senha-de-teste-123'
ANSWERS={'name':'Pessoa teste','cpf':'52998224725','age':'30','phone':'14999999999',
         'address':'Endereço teste','security':'Telado','email':'candidate@example.test'}
CAT={'name':'Gato teste','age':'2 anos','sex':'Fêmea','personality':'Tranquila','color':'Cinza',
     'entryDate':'2026-10-07','rescueLocation':'Local teste','rescuer':'Equipe',
     'rescueReport':'Relato de resgate','status':'Disponível','story':'História pública'}


@pytest.fixture
def client(monkeypatch):
    # Each test creates an isolated schema; never truncate a supplied database.
    schema='teste_'+uuid.uuid4().hex
    with psycopg.connect(URL,autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    from psycopg.conninfo import make_conninfo
    test_url=make_conninfo(URL,options='-c search_path='+schema)
    monkeypatch.setenv('ADMIN_SETUP_KEY','private-test-setup')
    app=create_app(test_url,seed=True)
    try:
        with TestClient(app,base_url='https://test.peticas') as c:
            yield c
    finally:
        with psycopg.connect(URL,autocommit=True) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def call(c,path,method='GET',data=None):
    return c.request(method,'/api/'+path,json=data,headers={'Origin':'https://test.peticas'})


def register(c):
    r=call(c,'register','POST',{'name':'Responsável','email':'owner@example.test','password':PASSWORD,'setupKey':'private-test-setup'})
    assert r.status_code==200,r.text
    return r.json()['user']


def test_authentication_permissions_and_recovery(client):
    c=client
    assert call(c,'medical').status_code==401
    assert call(c,'register','POST',{'name':'Test','email':'test@example.test','password':PASSWORD}).status_code==403
    register(c)
    assert call(c,'register','POST',{}).status_code==403
    profile={'access':True,'permissions':['medical.read','medical.write','adoptions.lookup'],
             'cpf':'11144477735','name':'Voluntário','email':'staff@example.test','password':PASSWORD,'age':'30',
             'address':'Endereço teste','phone':'14999999999','signature':'Voluntário','commitment':'Sim','rules':'Sim'}
    r=call(c,'users','POST',profile); assert r.status_code==201,r.text
    user_id=r.json()['id']; admin_cookie=dict(c.cookies)
    assert call(c,'users/'+user_id+'/profile').json()['profile']['phone']==profile['phone']
    c.cookies.clear()
    assert call(c,'login','POST',{'email':profile['email'],'password':PASSWORD}).status_code==200
    assert call(c,'users').status_code==403
    assert call(c,'medical').status_code==200
    assert call(c,'state','PUT',{}).status_code==403
    assert call(c,'inventory').status_code==410
    c.cookies.clear(); c.cookies.update(admin_cookie)
    assert call(c,'users/'+user_id+'/permissions','PUT',{'permissions':[]}).status_code==200
    call(c,'logout','POST',{})
    call(c,'login','POST',{'email':profile['email'],'password':PASSWORD})
    assert call(c,'medical').status_code==403
    assert call(c,'state').json()['vaccines']==[]
    c.cookies.clear(); c.cookies.update(admin_cookie)
    reset={'email':'owner@example.test','code':'private-test-setup','password':'Nova-senha-teste-456'}
    assert call(c,'reset-password','POST',{**reset,'code':'wrong'}).status_code==400
    r=call(c,'reset-password','POST',reset); assert r.status_code==200,r.text
    assert len(r.json()['recoveryCode'])==64
    assert call(c,'medical').status_code==401
    assert call(c,'reset-password','POST',reset).status_code==400
    assert call(c,'login','POST',{'email':reset['email'],'password':reset['password']}).status_code==200
    assert call(c,'recovery-code','POST',{'current':reset['password']}).status_code==200


def test_adoption_attachments_return_and_privacy(client):
    c=client; register(c)
    r=call(c,'adoptions','POST',{'cat':1,'answers':ANSWERS}); assert r.status_code==201,r.text
    rid=r.json()['request']['id']; token=r.json()['token']
    assert set(call(c,'tracking/cpf','POST',{'cpf':ANSWERS['cpf']}).json()['results'][0])=={'stage','date','returned','stageHistory'}
    assert call(c,'tracking/cpf','POST',{'cpf':'11111111111'}).status_code==400
    cookie=dict(c.cookies); c.cookies.clear()
    video={'ownerType':'video','ownerId':rid,'name':'video.mp4','mime':'video/mp4','data':base64.b64encode(b'0000ftyp0000').decode(),'token':token}
    assert call(c,'attachments','POST',{**video,'token':'wrong'}).status_code==403
    file=call(c,'attachments','POST',video); assert file.status_code==201,file.text
    assert call(c,'attachments?adoptionId='+rid).status_code==403
    assert len(call(c,'attachments?adoptionId='+rid+'&token='+token).json()['files'])==1
    assert call(c,'attachments/'+file.json()['id']+'?token='+token).content==b'0000ftyp0000'
    assert call(c,'adoption-records','POST',{'adoptionId':rid,'token':token}).status_code==403
    c.cookies.update(cookie)
    for stage in (1,2,3,4):
        r=call(c,'adoptions/'+rid,'PATCH',{'stage':stage,'cat':1,'version':stage})
        assert r.status_code==200,r.text
    assert not any(x['id']==1 for x in call(c,'cats').json()['cats'])
    assert call(c,'adoptions/'+rid,'PATCH',{'stage':-1,'cat':1,'version':5,'rejectionReason':'Teste'}).status_code==400
    assert call(c,'adoptions/'+rid+'/history','POST',{'kind':'followup','date':'2026-10-13','notes':'Tudo bem','version':5}).status_code==200
    assert call(c,'adoptions/'+rid+'/history','POST',{'kind':'return','date':'2026-10-13','notes':'Devolução','version':6}).status_code==200
    assert call(c,'adoptions/'+rid+'/history','POST',{'kind':'return','date':'2026-10-13','notes':'Duplicada','version':7}).status_code==409
    a=call(c,'state').json()['applications'][0]
    assert a['stage']==4 and a['returned'] and len(a['history'])==2
    assert any(x['id']==1 for x in call(c,'cats').json()['cats'])
    assert call(c,'adoption-records','POST',{'adoptionId':rid,'token':token}).status_code==200


def test_cat_submissions_care_and_concurrency(client):
    c=client; register(c)
    assert call(c,'cat-submissions','POST',CAT).status_code==201
    row=call(c,'cat-submissions').json()['submissions'][0]
    r=call(c,'cat-submissions/'+row['id'],'PATCH',{'status':'approved','version':row['version']}); assert r.status_code==200,r.text
    assert call(c,'cat-submissions/'+row['id'],'PATCH',{'status':'approved','version':row['version']}).status_code==409
    public=next(x for x in call(c,'cats').json()['cats'] if x['name']==CAT['name'])
    assert 'rescuer' not in public
    s=call(c,'state').json()
    s['vaccines'].append({'cat':public['id'],'label':'Vacina','date':'2026-10-13','status':'Hoje','done':False})
    assert call(c,'state','PUT',s).status_code==200
    assert call(c,'state','PUT',s).status_code==409
    s=call(c,'state').json(); s['cats'][0]['status']='Adotado'
    assert call(c,'state','PUT',s).status_code==400
    a=call(c,'adoptions','POST',{'cat':public['id'],'answers':ANSWERS}).json()['request']['id']
    other=call(c,'adoptions','POST',{'cat':public['id'],'answers':ANSWERS}).json()['request']['id']
    for rid in (a,other):
        for stage in (1,2): assert call(c,'adoptions/'+rid,'PATCH',{'stage':stage,'cat':public['id'],'version':stage}).status_code==200
    def reserve(rid):
        return call(c,'adoptions/'+rid,'PATCH',{'stage':3,'cat':public['id'],'version':3}).status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(reserve,(a,other)))==[200,409]
    assert call(c,'project-settings','PUT',{'pix':'teste','campaigns':[{'label':'Teste','url':'javascript:alert(1)'}]}).status_code==400
    assert call(c,'project-settings','PUT',{'pix':'teste','campaigns':[{'label':'Teste','url':'https://example.test'}]}).status_code==200


def test_medical_schedule_idempotency_completion_and_outbox(client,monkeypatch):
    c=client; register(c)
    tid=str(uuid.uuid4())
    treatment={'id':tid,'kind':'treatment','catId':1,'date':'2026-10-09','time':'08:00','endDate':'2026-10-11',
               'intervalHours':12,'label':'Prescrição teste','dose':'Conforme receita','frequency':'12 horas','prescriber':'Vet teste'}
    r=call(c,'medical','POST',treatment); assert r.status_code==201,r.text
    assert call(c,'medical','POST',treatment).status_code==200
    doses=call(c,'medication-schedule?start=2026-10-10&end=2026-10-11').json()['schedule']; assert len(doses)==4
    dose={'id':str(uuid.uuid4()),'kind':'application','catId':1,'treatmentId':tid,'date':'2026-10-10','time':'08:10','scheduledAt':doses[0]['scheduledAt'],
          'location':{'latitude':-22.88,'longitude':-48.44,'accuracy':10,'capturedAt':int(time.time()*1000)}}
    assert call(c,'medical','POST',dose).status_code==201
    assert call(c,'medical','POST',dose).status_code==200
    assert call(c,'medical','POST',{**dose,'id':str(uuid.uuid4())}).status_code==409
    assert call(c,'medical','POST',{'id':str(uuid.uuid4()),'kind':'completion','catId':1,'treatmentId':tid,'date':'2026-10-10','time':'12:00'}).status_code==201
    assert len(call(c,'medication-schedule?start=2026-10-10&end=2026-10-11').json()['schedule'])==1
    assert call(c,'medical','POST',{**dose,'id':str(uuid.uuid4()),'scheduledAt':''}).status_code==409
    pool=c.app.state.pool
    weekly_report(pool,datetime(2026,10,9,12,tzinfo=LOCAL_TZ)); weekly_report(pool,datetime(2026,10,9,12,tzinfo=LOCAL_TZ))
    assert len(call(c,'messages').json()['jobs'])==1
    monkeypatch.setenv('WHATSAPP_WEBHOOK_URL','https://gateway.example.test/messages')
    monkeypatch.setenv('WHATSAPP_WEBHOOK_TOKEN','test-token')
    monkeypatch.setenv('WHATSAPP_VOLUNTEERS_TARGET','volunteers')
    calls=[]
    def mock(request):
        calls.append(request)
        import json
        payload=json.loads(request.content)
        return httpx.Response(200,json={'id':payload['id'],'accepted':True,'simulated':False})
    with httpx.Client(transport=httpx.MockTransport(mock)) as gateway:
        dispatch_messages(pool,gateway); dispatch_messages(pool,gateway)
    assert len(calls)==1
    assert call(c,'messages').json()['jobs'][0]['sent'] is not None


def test_sql_naming_constraints_and_initialization(client):
    pool=client.app.state.pool
    initialize_database(pool)
    with pool.connection() as db:
        assert db.execute("SELECT to_regclass('migracoes_esquema') AS tabela").fetchone()['tabela'] is None
        columns=list(db.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=current_schema()"))
        assert columns
        assert all(re.fullmatch(r'(cod|txt|num|dat|hor|flg|bin)_[a-z_]+',r['column_name']) for r in columns)
        assert not {'users','cats','adoption_requests'} & {r['table_name'] for r in columns}
        typed=list(db.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema=current_schema() AND (column_name LIKE 'dat_%' OR column_name LIKE 'hor_%' OR column_name LIKE 'flg_%')"))
        for r in typed:
            prefix=r['column_name'][:3]
            allowed={'dat':{'date','timestamp with time zone'},'hor':{'time without time zone'},'flg':{'boolean'}}
            assert r['data_type'] in allowed[prefix],r
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with db.transaction():
                db.execute("INSERT INTO caracteristicas_gatos VALUES(99999,0,'Teste')")
    assert call(client,'health').json()['database']=='postgresql'
    assert client.get('/').status_code==200
    assert call(client,'tracking/cpf','POST',{'cpf':'11111111111'}).status_code==400
    for _ in range(9): assert call(client,'tracking/cpf','POST',{'cpf':'11111111111'}).status_code==400
    assert call(client,'tracking/cpf','POST',{'cpf':ANSWERS['cpf']}).status_code==429
    assert client.post('/api/login',json={},headers={'Origin':'https://evil.test'}).status_code==403
