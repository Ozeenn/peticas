import time
import uuid
from datetime import datetime
import pytest
from backend.security import LOCAL_TZ
from backend.tests.test_api import client, call, register, URL, ANSWERS, PASSWORD

pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL')


def test_cpf_returns_every_application_and_history_without_messages(client):
    c=client; register(c)
    first=call(c,'adoptions','POST',{'cat':1,'answers':ANSWERS}).json()
    rid=first['request']['id']
    for stage in (1,2):
        assert call(c,'adoptions/'+rid,'PATCH',{'cat':1,'stage':stage,'version':stage,'guidance':'Mensagem privada '+str(stage)}).status_code==200
    assert call(c,'adoptions/'+rid,'PATCH',{'cat':1,'stage':-1,'version':3,'rejectionReason':'Motivo privado'}).status_code==200
    second=call(c,'adoptions','POST',{'cat':2,'answers':ANSWERS}).json()
    c.cookies.clear()
    results=call(c,'tracking/cpf','POST',{'cpf':ANSWERS['cpf']}).json()['results']
    assert len(results)==2
    declined=next(r for r in results if r['stage']==-1)
    assert [h['stage'] for h in declined['stageHistory']]==[0,1,2,-1]
    assert all(h['date'] for h in declined['stageHistory'])
    assert all(set(r)=={'stage','date','returned','stageHistory'} for r in results)
    assert all(set(h)=={'stage','date'} for r in results for h in r['stageHistory'])
    detail=call(c,'tracking','POST',{'token':first['token']}).json()['request']
    assert [m['text'] for m in detail['messages']][-2:]==['Mensagem privada 1','Mensagem privada 2']
    assert detail['rejectionReason']=='Motivo privado'
    assert call(c,'tracking','POST',{'token':second['token']}).json()['request']['stageHistory'][0]['stage']==0
    assert call(c,'tracking','POST',{'token':'wrong'}).status_code==404


def test_mandatory_location_and_volunteer_vaccination(client):
    c=client; register(c)
    treatment={'id':str(uuid.uuid4()),'kind':'treatment','catId':1,'date':'2026-10-01','label':'Receita teste',
               'dose':'Receita','frequency':'Conforme prescrição','prescriber':'Vet teste'}
    assert call(c,'medical','POST',treatment).status_code==201
    s=call(c,'state').json()
    s['vaccines'].append({'cat':1,'label':'Vacina teste','date':'2026-10-13','status':'Hoje','done':False})
    assert call(c,'state','PUT',s).status_code==200
    vaccine=call(c,'vaccines').json()['vaccines'][0]
    profile={'access':True,'permissions':['medical.read','medical.write'],'cpf':'11144477735','name':'Voluntário teste',
             'email':'volunteer@example.test','password':PASSWORD,'age':'30','address':'Teste','phone':'14999999999',
             'signature':'Teste','commitment':'Sim','rules':'Sim'}
    assert call(c,'users','POST',profile).status_code==201
    c.cookies.clear(); assert call(c,'login','POST',{'email':profile['email'],'password':PASSWORD}).status_code==200
    event={'id':str(uuid.uuid4()),'kind':'application','catId':1,'treatmentId':treatment['id'],'date':'2026-10-13','time':'10:00'}
    assert call(c,'medical','POST',event).status_code==400
    coordinates={'latitude':-22.88,'longitude':-48.44,'accuracy':20,'capturedAt':int(time.time()*1000)}
    for invalid in ({**coordinates,'latitude':91},{**coordinates,'capturedAt':0},{**coordinates,'accuracy':-1},{**coordinates,'longitude':True}):
        assert call(c,'medical','POST',{**event,'location':invalid}).status_code==400
    r=call(c,'medical','POST',{**event,'location':coordinates}); assert r.status_code==201,r.text
    records=call(c,'medical').json()['records']
    assert not any('location' in r for r in records)
    assert call(c,'state','PUT',{}).status_code==403
    today=datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
    r=call(c,'vaccines/'+str(vaccine['id'])+'/application','POST',{'applied':today,'version':vaccine['version']}); assert r.status_code==201,r.text
    assert call(c,'vaccines/'+str(vaccine['id'])+'/application','POST',{'applied':today,'version':vaccine['version']}).status_code==409
    saved=call(c,'vaccines').json()['vaccines'][0]
    assert saved['done'] is True and saved['person']==profile['name']
    c.cookies.clear(); call(c,'login','POST',{'email':'owner@example.test','password':PASSWORD})
    record=next(r for r in call(c,'medical').json()['records'] if r['id']==event['id'])
    assert record['location']['latitude']==coordinates['latitude']
    # Saving another planned care must preserve vaccine IDs and attribution.
    s=call(c,'state').json(); s['vaccines'].append({'cat':2,'label':'Outra vacina','date':today,'status':'Hoje','done':False})
    assert call(c,'state','PUT',s).status_code==200
    assert call(c,'vaccines').json()['vaccines'][0]['id']==vaccine['id']
