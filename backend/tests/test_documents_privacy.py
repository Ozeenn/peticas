import base64
from io import BytesIO
import os
from pathlib import Path
import uuid

from pypdf import PdfReader
import pytest
from backend.tests.test_api import client,call,register,URL,ANSWERS,PASSWORD

pytestmark=pytest.mark.skipif(not URL,reason='Configure PETICAS_TEST_DATABASE_URL')


def test_notice_acknowledgement_optional_video_and_private_record(client):
    c=client; register(c)
    notice=call(c,'privacy').json()
    missing=c.post('/api/adoptions',json={'cat':1,'answers':ANSWERS},headers={'Origin':'https://test.peticas'})
    assert missing.status_code==400
    assert call(c,'state').json()['applications']==[]
    stale=c.post('/api/adoptions',json={'cat':1,'answers':ANSWERS,'privacyAcknowledged':True,'privacyVersion':'old'},headers={'Origin':'https://test.peticas'})
    assert stale.status_code==409
    a=call(c,'adoptions','POST',{'cat':1,'answers':ANSWERS,'homeVideoConsent':False}).json()
    rid=a['request']['id']; token=a['token']
    choice=call(c,'tracking','POST',{'token':token}).json()['request']['privacy']
    assert choice['acknowledged'] and not choice['homeVideoConsent']
    video={'ownerType':'video','ownerId':rid,'name':'video.mp4','mime':'video/mp4','data':base64.b64encode(b'0000ftyp0000').decode(),'token':token}
    assert call(c,'attachments','POST',video).status_code==400
    c.cookies.clear()
    assert call(c,'adoptions/'+rid+'/privacy','POST',{'token':'wrong','privacyAcknowledged':True,'privacyVersion':notice['version'],'homeVideoConsent':True}).status_code==403
    assert call(c,'adoptions/'+rid+'/privacy','POST',{'token':token,'privacyAcknowledged':True,'privacyVersion':notice['version'],'homeVideoConsent':True}).status_code==200
    assert call(c,'attachments','POST',video).status_code==201
    assert call(c,'adoptions/'+rid+'/privacy','POST',{'token':token,'privacyAcknowledged':True,'privacyVersion':notice['version'],'homeVideoConsent':False}).status_code==200
    assert call(c,'attachments','POST',video).status_code==400
    public=call(c,'tracking/cpf','POST',{'cpf':ANSWERS['cpf']}).json()['results']
    assert all('privacy' not in row for row in public)
    with c.app.state.pool.connection() as db:
        records=db.execute('SELECT txt_aviso,flg_consentimento_video FROM registros_privacidade WHERE cod_candidatura=%s ORDER BY dat_cadastro',(rid,)).fetchall()
        assert len(records)==3
        assert records[0]['txt_aviso']


def test_privacy_requests_are_manual_and_restricted(client):
    c=client
    r=call(c,'privacy-requests','POST',{'name':'Pessoa teste','email':'test@example.test','kind':'deletion','description':'Solicito análise da eliminação de meus dados.'})
    assert r.status_code==201,r.text
    rid=r.json()['protocol']
    assert call(c,'privacy-requests').status_code==401
    register(c)
    records=call(c,'privacy-requests').json()['requests']
    assert records[0]['status']=='received'
    assert call(c,'privacy-requests/'+rid,'PATCH',{'status':'in_review','notes':'Contato para verificação de identidade.'}).status_code==200
    assert call(c,'privacy-requests/'+rid,'PATCH',{'status':'answered','notes':''}).status_code==400
    assert call(c,'privacy-requests/'+rid,'PATCH',{'status':'answered','notes':'Providência e resposta registradas após análise.'}).status_code==200
    assert call(c,'privacy-requests').json()['requests'][0]['status']=='answered'
    assert 'Contato para verificação' in call(c,'privacy-requests').json()['requests'][0]['notes']
    config={'controller':'Responsável teste do gatil','identifier':'Identificação documental interna','address':'Endereço institucional teste',
            'contact':'privacy@example.test','retention':'Política de guarda definida para este cenário fictício.'}
    before=call(c,'privacy').json()['version']
    assert call(c,'privacy-settings','PUT',config).status_code==200
    public=call(c,'privacy').json()
    assert public['version']!=before and 'identifier' not in public['config']
    assert 'Identificação documental interna' not in str(public)
    assert call(c,'privacy-settings').json()['settings']['identifier']==config['identifier']
    assert call(c,'maintenance-manual').status_code==200
    c.cookies.clear()
    assert call(c,'maintenance-manual').status_code==401


def test_pdf_documents_contain_cat_data_and_require_administrator(client):
    c=client; register(c)
    r=call(c,'adoptions','POST',{'cat':1,'answers':{**ANSWERS,'name':'Pessoa fictícia para revisão'},'homeVideoConsent':False})
    assert r.status_code==201,r.text
    rid=r.json()['request']['id']
    assert call(c,'adoptions/'+rid+'/term.pdf').status_code==400
    for stage in (1,2,3): assert call(c,'adoptions/'+rid,'PATCH',{'cat':1,'stage':stage,'version':stage,'guidance':'Orientação de exemplo para a família.'}).status_code==200
    treatment={'id':str(uuid.uuid4()),'kind':'treatment','catId':1,'date':'2026-10-13','label':'Tratamento demonstrativo',
               'dose':'Conforme prescrição de exemplo','frequency':'Conforme prescrição','prescriber':'Veterinário fictício',
               'notes':'Registro de exemplo, sem orientação clínica real. '*15}
    assert call(c,'medical','POST',treatment).status_code==201
    from backend.db import ROOT
    photo=(ROOT/'public/assets/gato-laranja.jpg').read_bytes()
    assert call(c,'attachments','POST',{'ownerType':'cat','ownerId':'1','name':'foto-demonstrativa.jpg','mime':'image/jpeg','data':base64.b64encode(photo).decode()}).status_code==201
    report=call(c,'cats/1/report.pdf'); term=call(c,'adoptions/'+rid+'/term.pdf')
    for response in (report,term):
        assert response.status_code==200,response.text[:300] if response.status_code!=200 else ''
        assert response.headers['content-type']=='application/pdf'
        assert response.headers['cache-control']=='no-store'
        assert response.content.startswith(b'%PDF-')
    report_text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(report.content)).pages)
    term_text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(term.content)).pages)
    assert 'Luna' in report_text and 'Tratamento demonstrativo' in report_text and 'Pessoa fictícia para revisão' in report_text
    assert 'foto-demonstrativa.jpg' in report_text and 'Prontuário completo' in report_text
    assert 'Termo de adoção responsável' in term_text and '52998224725' in term_text and 'NÃO AUTORIZO' in term_text
    assert 'assinatura digital' in term_text and 'MODELO PARA REVISÃO' in term_text
    qa=os.getenv('PETICAS_PDF_QA_DIR')
    if qa:
        target=Path(qa); target.mkdir(parents=True,exist_ok=True)
        (target/'ficha-exemplo.pdf').write_bytes(report.content)
        (target/'termo-exemplo.pdf').write_bytes(term.content)
    c.cookies.clear()
    assert call(c,'cats/1/report.pdf').status_code==401
    assert call(c,'adoptions/'+rid+'/term.pdf').status_code==401
    call(c,'login','POST',{'email':'owner@example.test','password':PASSWORD})
    profile={'access':True,'permissions':['medical.read'],'cpf':'11144477735','name':'Voluntário','email':'staff@example.test','password':PASSWORD,
             'age':'30','address':'Endereço teste','phone':'14999999999','signature':'Teste','commitment':'Sim','rules':'Sim'}
    assert call(c,'users','POST',profile).status_code==201
    c.cookies.clear(); call(c,'login','POST',{'email':profile['email'],'password':PASSWORD})
    assert call(c,'cats/1/report.pdf').status_code==403
    assert call(c,'adoptions/'+rid+'/term.pdf').status_code==403
    assert call(c,'privacy-requests').status_code==403
