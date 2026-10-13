"""FastAPI entrypoint, preserving the browser's existing API contract."""
import base64
import hmac
import json
import logging
import math
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .db import make_pool, initialize_database, seed_demo, ROOT
from . import repository as repo
from . import privacy, reports
from .security import (PERMISSIONS, LOCAL_TZ, now, uid, fail, text, digest, password_hash, check_password,
                       validate_password, email, cpf, cpf_hash, limit, get_user, safe_user, staff, admin, permit, date)
from .schedule import medication_schedule, unscheduled, iso


def reply(data, status=200):
    return JSONResponse(data, status_code=status)


def session(db, request, user):
    from .security import permissions
    token = secrets.token_hex(32)
    repo.insert(db,'sessions',{'id':digest(token),'user_id':user['id'],'expires':now()+7*86400000})
    user['permissions'] = permissions(db,user)
    r = reply({'user':safe_user(user)})
    r.set_cookie('__Host-peticas_session' if request.url.scheme=='https' else 'peticas_session', token,
                 max_age=7*86400, httponly=True, secure=request.url.scheme=='https', samesite='lax', path='/')
    return r


def setting(db,key,default=''):
    row = db.execute('SELECT txt_valor FROM configuracoes WHERE txt_chave=%s',(key,)).fetchone()
    return row['value'] if row else default


def set_setting(db,key,value):
    db.execute('INSERT INTO configuracoes VALUES(%s,%s) ON CONFLICT(txt_chave) DO UPDATE SET txt_valor=excluded.txt_valor',(key,value))


def adopt_row(db,rid,lock=False):
    row = db.execute('SELECT * FROM candidaturas_adocao WHERE cod_identificador=%s'+(' FOR UPDATE' if lock else ''),(rid,)).fetchone()
    if not row:
        fail(404,'Candidatura não encontrada.')
    return row


def authorize_adoption(db,user,rid,token):
    row = adopt_row(db,rid)
    if not user or user['role']!='admin':
        if not isinstance(token,str) or not hmac.compare_digest(digest(token),row['token_hash']):
            fail(403,'Acesso restrito.')
    return row


def version(row,b):
    if type(b.get('version')) is not int or b['version']!=row['version']:
        fail(409,'O registro mudou. Reabra antes de salvar.')


def queue(db,key,target,message):
    db.execute('INSERT INTO fila_mensagens(cod_identificador,txt_destino,txt_mensagem,dat_cadastro) VALUES(%s,%s,%s,to_timestamp(%s/1000.0)) ON CONFLICT DO NOTHING',(key,target,message,now()))


def dispatch(request,b,db,pool):
    path = request.url.path.removeprefix('/api/'); method=request.method
    user = get_user(db,request)
    ip = request.client.host if request.client else 'local'
    throttle = lambda key,maximum=10: limit(pool,key+':'+ip,maximum)
    if path=='privacy' and method=='GET':
        current=privacy.notice(db)
        current['config']={k:v for k,v in current['config'].items() if k!='identifier'}
        return reply({k:v for k,v in current.items() if k!='snapshot'})
    if path=='privacy-settings':
        admin(user)
        if method=='GET': return reply({'settings':privacy.config(db)})
        if method=='PUT': privacy.save_config(db,b); return reply({'ok':True})
    if path=='maintenance-manual' and method=='GET':
        admin(user)
        return Response((ROOT/'docs/MANUAL_MANUTENCAO.md').read_text(encoding='utf-8'),media_type='text/markdown',
                        headers={'Content-Disposition':'attachment; filename="manual-manutencao-peticas.md"'})
    if path=='privacy-requests':
        if method=='POST':
            throttle('privacy-request',5)
            return reply({'protocol':privacy.create_request(db,b),'message':'Pedido registrado. A responsável verificará sua identidade e dará andamento pelo contato informado.'},201)
        if method=='GET': admin(user); return reply({'requests':privacy.requests(db)})
    match=re.fullmatch(r'privacy-requests/([^/]+)',path)
    if match and method=='PATCH':
        admin(user)
        if b.get('status') not in ('received','in_review','answered'): fail(400,'Situação inválida.')
        notes=text(b.get('notes',''),3000,False)
        if b['status']=='answered' and not notes: fail(400,'Registre a providência e a resposta antes de concluir o pedido.')
        entry=f"{datetime.now(LOCAL_TZ):%d/%m/%Y %H:%M} | {user['name']} | {notes}" if notes else ''
        result=db.execute("UPDATE solicitacoes_privacidade SET txt_situacao=%s,txt_anotacoes=concat_ws(E'\\n\\n',NULLIF(txt_anotacoes,''),NULLIF(%s,'')),dat_atualizacao=now() WHERE cod_identificador=%s",(b['status'],entry,match[1]))
        if not result.rowcount: fail(404,'Pedido não encontrado.')
        return reply({'ok':True})
    match=re.fullmatch(r'cats/(\d+)/report.pdf',path)
    if match and method=='GET':
        admin(user)
        return Response(reports.cat_report(db,int(match[1]),user),media_type='application/pdf',
                        headers={'Content-Disposition':f'inline; filename="ficha-gato-{match[1]}.pdf"'})
    match=re.fullmatch(r'adoptions/([^/]+)/term.pdf',path)
    if match and method=='GET':
        admin(user)
        return Response(reports.adoption_term(db,match[1],user),media_type='application/pdf',
                        headers={'Content-Disposition':'inline; filename="termo-adocao.pdf"'})
    match=re.fullmatch(r'adoptions/([^/]+)/privacy',path)
    if match and method=='POST':
        throttle('privacy-consent',10)
        authorize_adoption(db,None,match[1],b.get('token'))
        # Choices must use the candidate's private link, even for an administrator.
        privacy.record(db,match[1],b)
        return reply({'ok':True})
    if path=='health' and method=='GET':
        db.execute('SELECT 1')
        return reply({'ok':True,'backend':'python','database':'postgresql'})
    if path=='session' and method=='GET':
        return reply({'user':safe_user(user),'setupRequired':not db.execute("SELECT cod_identificador FROM usuarios WHERE txt_perfil='admin'").fetchone()})
    if path=='project-settings':
        if method=='GET':
            return reply({'settings':{'pix':setting(db,'pix'),'campaigns':list(db.execute('SELECT txt_descricao,txt_endereco_web FROM campanhas ORDER BY cod_identificador'))}})
        admin(user)
        if method=='PUT':
            pix=text(b.get('pix',''),200,False); campaigns=b.get('campaigns')
            if not isinstance(campaigns,list) or len(campaigns)>10:
                fail(400,'Campanhas inválidas.')
            checked=[]
            for c in campaigns:
                if not isinstance(c,dict): fail(400,'Campanha inválida.')
                url=text(c.get('url'),1000); parts=urlparse(url)
                if parts.scheme!='https' or not parts.hostname or parts.username or parts.password:
                    fail(400,'Use links HTTPS válidos.')
                checked.append({'label':text(c.get('label'),100),'url':url})
            set_setting(db,'pix',pix); db.execute('DELETE FROM campanhas')
            for c in checked: repo.insert(db,'campaigns',c)
            return reply({'ok':True})
    if path=='register' and method=='POST':
        throttle('register',8)
        db.execute('SELECT pg_advisory_xact_lock(742092)')
        if db.execute("SELECT cod_identificador FROM usuarios WHERE txt_perfil='admin'").fetchone(): fail(403,'Somente a responsável pode cadastrar voluntários.')
        name=text(b.get('name'),100); mail=email(b.get('email')); password=validate_password(b.get('password'))
        key=os.getenv('ADMIN_SETUP_KEY','')
        if not key or not isinstance(b.get('setupKey'),str) or not hmac.compare_digest(digest(b['setupKey']),digest(key)):
            fail(403,'Chave de primeiro acesso inválida.')
        u=repo.insert(db,'users',{'id':uid(),'name':name,'email':mail,'password':password_hash(password),'role':'admin','created':now()})
        return session(db,request,u)
    if path=='login' and method=='POST':
        throttle('login-ip',30); mail=email(b.get('email')); limit(pool,'login-email:'+mail,10)
        u=db.execute('SELECT * FROM usuarios WHERE txt_email=%s',(mail,)).fetchone()
        stored=u['password'] if u else '0'*32+':'+'0'*64
        if not check_password(b.get('password'),stored) or not u: fail(401,'E-mail ou senha incorretos.')
        return session(db,request,u)
    if path=='logout' and method=='POST':
        token=request.cookies.get('__Host-peticas_session') or request.cookies.get('peticas_session')
        if token: db.execute('DELETE FROM sessoes WHERE cod_identificador=%s',(digest(token),))
        r=reply({'ok':True}); r.delete_cookie('__Host-peticas_session' if request.url.scheme=='https' else 'peticas_session',path='/')
        return r
    if path=='reset-password' and method=='POST':
        throttle('recovery',5); mail=email(b.get('email')); limit(pool,'recovery-email:'+mail,5)
        new=validate_password(b.get('password')); provided=digest(text(b.get('code'),256))
        u=db.execute('SELECT * FROM usuarios WHERE txt_email=%s FOR UPDATE',(mail,)).fetchone()
        expected=(u['recovery_hash'] or (digest(os.environ['ADMIN_SETUP_KEY']) if u['role']=='admin' and os.getenv('ADMIN_SETUP_KEY') else '')) if u else ''
        if not u or not expected or not hmac.compare_digest(provided,expected): fail(400,'E-mail ou código de recuperação inválido.')
        code=secrets.token_hex(32)
        repo.update(db,'users',{'password':password_hash(new),'recovery_hash':digest(code)},'id',u['id'])
        db.execute('DELETE FROM sessoes WHERE cod_usuario=%s',(u['id'],))
        return reply({'ok':True,'recoveryCode':code})
    if path=='cats' and method=='GET':
        fields=('id','name','age','sex','personality','tags','photo','photoId','status','story','color')
        return reply({'cats':[{k:c[k] for k in fields if k in c} for c in repo.cats(db) if c['status']=='Disponível']})
    if path=='adoptions' and method=='POST':
        throttle('adoption',5); answers=b.get('answers')
        if not isinstance(answers,dict): fail(400,'Preencha a entrevista.')
        for k,v in answers.items():
            if not re.fullmatch('[a-zA-Z]+',k) or not isinstance(v,str) or len(v)>2500: fail(400,'Resposta inválida.')
        text(answers.get('name'),100); answers['cpf']=cpf(answers.get('cpf')); email(answers.get('email'))
        age=answers.get('age','')
        if not age.isdigit() or not 18<=int(age)<=120: fail(400,'A adoção é permitida apenas para maiores de 18 anos.')
        text(answers.get('phone'),40); text(answers.get('address'),2500); text(answers.get('security'),2500)
        cat_id=b.get('cat')
        if cat_id is not None:
            if type(cat_id) is not int: fail(400,'Gato inválido.')
            c=db.execute('SELECT txt_situacao FROM gatos WHERE cod_identificador=%s FOR SHARE',(cat_id,)).fetchone()
            if not c or c['status']!='Disponível': fail(409,'Este gato não está disponível. Atualize a página.')
        rid=uid(); token=secrets.token_hex(32); guidance='Recebemos sua candidatura. Aguarde o contato da equipe.'
        repo.insert(db,'adoption_requests',{'id':rid,'token_hash':digest(token),'cpf_hash':cpf_hash(db,answers['cpf']),
                    'cat_id':cat_id,'date':datetime.now(LOCAL_TZ).strftime('%d/%m/%Y'),'guidance':guidance,
                    'note':'Entrevista recebida pelo site.','created':now()})
        for k,v in answers.items(): repo.insert(db,'adoption_answers',{'adoption_id':rid,'question':k,'answer':v})
        privacy.record(db,rid,b)
        repo.insert(db,'adoption_messages',{'id':uid(),'adoption_id':rid,'message':guidance,'created':now()})
        queue(db,'adoption:'+rid,'owner','Nova candidatura de adoção recebida. Acesse a área da responsável para analisar.')
        return reply({'token':token,'request':{'id':rid,'name':answers['name'],'cat':cat_id,'stage':0,'guidance':guidance}},201)
    if path=='tracking' and method=='POST':
        throttle('tracking',60)
        r=db.execute('SELECT * FROM candidaturas_adocao WHERE txt_token_hash=%s',(digest(text(b.get('token'),100)),)).fetchone()
        if not r: fail(404,'Link de acompanhamento inválido.')
        a=repo.adoption(db,r)
        detail={k:a[k] for k in ('id','name','cat','stage','guidance','returned','rejectionReason')}
        detail.update(stageHistory=repo.stage_history(db,r),messages=repo.adoption_messages(db,r['id']),privacy=privacy.latest(db,r['id']))
        return reply({'request':detail})
    if path in ('tracking/cpf','adoptions/lookup') and method=='POST':
        if path=='adoptions/lookup': permit(user,'adoptions.lookup'); limit(pool,'adoption-lookup:'+user['id'],20)
        else: throttle('public-cpf-lookup',10)
        matches=db.execute('SELECT * FROM candidaturas_adocao WHERE txt_cpf_hash=%s ORDER BY dat_cadastro DESC,cod_identificador',(cpf_hash(db,b.get('cpf')),)).fetchall()
        return reply({'results':[{'stage':r['stage'],'date':r['date'],'returned':r['returned'],'stageHistory':repo.stage_history(db,r)} for r in matches]})
    if path=='adoption-records' and method=='POST':
        a=authorize_adoption(db,user,b.get('adoptionId'),b.get('token'))
        if a['stage']!=4: fail(403,'Histórico disponível após a adoção.')
        full=repo.adoption(db,a); c=next((c for c in repo.cats(db) if c['id']==a['cat_id']),None)
        final=next((h['date'] for h in full['stageHistory'] if h['stage']==4),None)
        cutoff=int(datetime.fromisoformat(final.replace('Z','+00:00')).timestamp()*1000) if final else now()
        records=[{k:r[k] for k in ('kind','data','created')} for r in repo.medical(db) if r['cat_id']==a['cat_id'] and r['created']<=cutoff]
        return reply({'cat':{k:c[k] for k in ('name','age','sex','color','story')} if c else None,'records':records,
                      'vaccines':[v for v in repo.state(db)['vaccines'] if v['cat']==a['cat_id']]})
    if path=='attachments' or re.fullmatch(r'attachments/[^/]+',path):
        return attachment_route(request,b,db,user,path,method)
    staff(user)
    if re.match(r'^(inventory|items|purchases|notifications)(/|$)',path): fail(410,'O controle de estoque foi retirado do escopo.')
    if path=='volunteer-guide' and method=='GET':
        return reply({'groupUrl':'https://chat.whatsapp.com/LChyZayqubA5ESmaW8wAH8',
                      'entry':'A chave do gatil fica na gavetinha azul, ao lado da porta da cozinha. Ao sair, tranque o portão e devolva a chave ao mesmo lugar.'})
    if path in ('password','recovery-code') and method=='POST':
        limit(pool,path+':'+user['id'],5)
        locked=db.execute('SELECT * FROM usuarios WHERE cod_identificador=%s FOR UPDATE',(user['id'],)).fetchone()
        if not check_password(b.get('current'),locked['password']): fail(400,'Senha atual incorreta.')
        if path=='recovery-code':
            code=secrets.token_hex(32); repo.update(db,'users',{'recovery_hash':digest(code)},'id',user['id'])
            return reply({'recoveryCode':code})
        repo.update(db,'users',{'password':password_hash(validate_password(b.get('password')))},'id',user['id'])
        db.execute('DELETE FROM sessoes WHERE cod_usuario=%s',(user['id'],))
        return session(db,request,user)
    if path=='users':
        admin(user)
        if method=='GET': return reply({'users':list(db.execute('SELECT cod_identificador,txt_nome,txt_email,txt_perfil,dat_cadastro FROM usuarios ORDER BY dat_cadastro DESC'))})
        if method=='POST':
            name=text(b.get('name'),100); mail=email(b.get('email')); enabled=b.get('access') is True
            selected=validate_permissions(b.get('permissions'))
            profile={k:text(b.get(k,''),2500,False) for k in repo.PROFILE_FIELDS if k!='cpf'}
            profile['cpf']=cpf(b.get('cpf'))
            if not all(profile[k] for k in ('phone','address','signature')) or profile['commitment']!='Sim' or profile['rules']!='Sim':
                fail(400,'Preencha contato, endereço, assinatura e os aceites do voluntário.')
            if not profile['age'].isdigit() or not 1<=int(profile['age'])<=120: fail(400,'Idade inválida.')
            user_id=uid(); password=validate_password(b.get('password')) if enabled else secrets.token_hex(32)
            repo.insert(db,'users',{'id':user_id,'name':name,'email':mail,'password':password_hash(password),'role':'staff' if enabled else 'pending','created':now()})
            repo.insert(db,'volunteer_profiles',{'user_id':user_id,**{('signed_at' if k=='signedAt' else k):v for k,v in profile.items()}})
            for p in selected: repo.insert(db,'user_permissions',{'user_id':user_id,'permission':p})
            return reply({'id':user_id},201)
    match=re.fullmatch(r'users/([^/]+)(?:/(profile|permissions))?',path)
    if match:
        admin(user); user_id,action=match.groups()
        target=db.execute('SELECT * FROM usuarios WHERE cod_identificador=%s FOR UPDATE',(user_id,)).fetchone()
        if not target or target['role']=='admin': fail(400,'Voluntário inválido.')
        if action=='profile' and method=='GET':
            p=db.execute('SELECT * FROM fichas_voluntarios WHERE cod_usuario=%s',(user_id,)).fetchone()
            return reply({'profile':{('signedAt' if k=='signed_at' else k):v for k,v in p.items() if k!='user_id'} if p else None})
        if action=='permissions':
            from .security import permissions
            if method=='GET': return reply({'permissions':permissions(db,target)})
            if method=='PUT':
                selected=validate_permissions(b.get('permissions')); db.execute('DELETE FROM permissoes_usuarios WHERE cod_usuario=%s',(user_id,))
                for p in selected: repo.insert(db,'user_permissions',{'user_id':user_id,'permission':p})
                db.execute('DELETE FROM sessoes WHERE cod_usuario=%s',(user_id,)); return reply({'ok':True})
        if action is None and method=='PATCH':
            role=b.get('role')
            if role not in ('staff','pending','blocked'): fail(400,'Perfil inválido.')
            if role=='staff' and target['role']=='pending' and not b.get('password'): fail(400,'Defina uma senha inicial para liberar o acesso.')
            password=password_hash(validate_password(b['password'])) if b.get('password') else target['password']
            repo.update(db,'users',{'role':role,'password':password},'id',user_id)
            db.execute('DELETE FROM sessoes WHERE cod_usuario=%s',(user_id,)); return reply({'ok':True})
    if path=='state':
        if method=='GET':
            s=repo.state(db)
            if 'medical.read' not in user['permissions']: s['vaccines']=[]; s['meds']=[]
            s['applications']=[repo.adoption(db,r) for r in db.execute('SELECT * FROM candidaturas_adocao ORDER BY dat_cadastro DESC')] if user['role']=='admin' else []
            return reply(s)
        if method=='PUT': admin(user); return reply({'version':repo.replace_state(db,b)})
    if path in ('cat-register','cat-submissions'):
        if path=='cat-submissions' and method=='GET':
            rows=db.execute('SELECT * FROM propostas_gatos ORDER BY dat_cadastro DESC') if user['role']=='admin' else db.execute('SELECT * FROM propostas_gatos WHERE cod_usuario=%s ORDER BY dat_cadastro DESC',(user['id'],))
            return reply({'submissions':[submission(r) for r in rows]})
        if method=='POST':
            if path=='cat-register': admin(user)
            else: permit(user,'cats.submit')
            c=repo.validate_cat(b)
            if c['status'] not in ('Disponível','Em tratamento'): fail(400,'Novos gatos devem estar disponíveis ou em tratamento.')
            if path=='cat-register':
                repo.revision(db,bump=True); repo.insert_cat(db,{**c,'approvedBy':user['id']})
            else:
                values={v:c[k] for k,v in repo.CAT_FIELDS.items() if k in c and k not in ('photo','status')}
                repo.insert(db,'cat_submissions',{'id':uid(),'user_id':user['id'],'status':'pending','cat_status':c['status'],'created':now(),**values})
            return reply({'ok':True},201)
    match=re.fullmatch(r'cat-submissions/([^/]+)',path)
    if match and method=='PATCH':
        admin(user); repo.revision(db,bump=True)
        row=db.execute('SELECT * FROM propostas_gatos WHERE cod_identificador=%s FOR UPDATE',(match[1],)).fetchone()
        if not row: fail(404,'Cadastro não encontrado.')
        version(row,b)
        if row['status']!='pending': fail(409,'Cadastro já revisado.')
        if b.get('status') not in ('approved','rejected'): fail(400,'Decisão inválida.')
        reason=text(b.get('reason',''),2000,b['status']=='rejected'); cat_id=None
        if b['status']=='approved': cat_id=repo.insert_cat(db,{**submission(row)['cat'],'approvedBy':user['id']})
        repo.update(db,'cat_submissions',{'status':b['status'],'reason':reason,'reviewed_by':user['id'],'reviewed_at':now(),
                                        'approved_cat_id':cat_id,'version':row['version']+1},'id',row['id'])
        return reply({'ok':True})
    match=re.fullmatch(r'cats/(\d+)',path)
    if match and method=='PATCH':
        repo.revision(db,b.get('version'),True)
        c=next((c for c in repo.cats(db) if c['id']==int(match[1])),None)
        if not c: fail(404,'Gato não encontrado.')
        if user['role']=='admin':
            next_cat=repo.validate_cat({**c,**b})
            if c['status'] in ('Reservado','Adotado') or next_cat['status'] in ('Reservado','Adotado'):
                if c['status']!=next_cat['status']: fail(400,'Altere reserva, adoção ou devolução pela candidatura.')
            c.update(next_cat)
        else:
            permit(user,'cats.status')
            if c['status'] not in ('Disponível','Em tratamento') or b.get('status') not in ('Disponível','Em tratamento'):
                fail(400,'Reserva, adoção e devolução dependem da responsável.')
            c['status']=b['status']
        repo.update_cat(db,c); return reply({'ok':True})
    match=re.fullmatch(r'adoptions/([^/]+)(?:/(cpf|history))?',path)
    if match:
        admin(user); rid,action=match.groups()
        # Consistent lock order: global cat revision, then adoption row.
        repo.revision(db,bump=action!='cpf'); row=adopt_row(db,rid,True); version(row,b)
        if action=='cpf' and method=='PATCH':
            value=cpf(b.get('cpf')); repo.update(db,'adoption_requests',{'cpf_hash':cpf_hash(db,value),'version':row['version']+1},'id',rid)
            db.execute("INSERT INTO respostas_entrevistas VALUES(%s,'cpf',%s) ON CONFLICT(cod_candidatura,txt_pergunta) DO UPDATE SET txt_resposta=excluded.txt_resposta",(rid,value))
            return reply({'ok':True})
        if action=='history' and method=='POST':
            if row['stage']!=4: fail(400,'Disponível após concluir a adoção.')
            kind=b.get('kind')
            if kind not in ('followup','return','term'): fail(400,'Registro inválido.')
            event_date=date(b.get('date')); notes=text(b.get('notes'),3000)
            if kind=='return':
                if row['returned']: fail(409,'Devolução já registrada.')
                c=db.execute('SELECT txt_situacao FROM gatos WHERE cod_identificador=%s FOR UPDATE',(row['cat_id'],)).fetchone()
                if not c or c['status']!='Adotado': fail(409,'A situação do gato mudou.')
                repo.update(db,'cats',{'status':'Disponível'},'id',row['cat_id'])
            repo.insert(db,'adoption_events',{'id':uid(),'adoption_id':rid,'kind':kind,'date':event_date,'notes':notes,'user_id':user['id'],'created':now()})
            repo.update(db,'adoption_requests',{'returned':row['returned'] or kind=='return','version':row['version']+1},'id',rid)
            return reply({'ok':True})
        if action is None and method=='PATCH':
            stage=b.get('stage'); old=row['stage']; cat_id=b.get('cat')
            if type(stage) is not int or not -1<=stage<=4 or stage not in (old,old+1,-1): fail(400,'Etapa inválida.')
            if row['returned'] or (old==4 and stage!=4): fail(400,'Use o acompanhamento ou a devolução da adoção concluída.')
            if old>=3 and stage>=3 and cat_id!=row['cat_id']: fail(400,'O gato reservado ou adotado não pode ser trocado.')
            c=db.execute('SELECT * FROM gatos WHERE cod_identificador=%s FOR UPDATE',(cat_id,)).fetchone() if type(cat_id) is int else None
            if cat_id is not None and not c: fail(400,'Gato inválido.')
            if stage>=3 and not c: fail(400,'Escolha um gato antes da aprovação.')
            if old<3 and stage==3 and c['status']!='Disponível': fail(409,'Gato indisponível.')
            if stage==3: repo.update(db,'cats',{'status':'Reservado'},'id',cat_id)
            if stage==4: repo.update(db,'cats',{'status':'Adotado'},'id',cat_id)
            if old==3 and stage==-1: repo.update(db,'cats',{'status':'Disponível'},'id',row['cat_id'])
            rejection=text(b.get('rejectionReason') or row['rejection_reason'],3000) if stage==-1 else row['rejection_reason']
            guidance=text(b.get('guidance',''),3000,False)
            repo.update(db,'adoption_requests',{'cat_id':cat_id,'stage':stage,'guidance':guidance,
                                              'rejection_reason':rejection,'version':row['version']+1},'id',rid)
            if guidance and guidance!=row['guidance']:
                repo.insert(db,'adoption_messages',{'id':uid(),'adoption_id':rid,'user_id':user['id'],'message':guidance,'created':now()})
            if stage!=old: repo.insert(db,'adoption_stage_history',{'adoption_id':rid,'stage':stage,'date':iso(datetime.now(timezone.utc)),'user_id':user['id']})
            return reply({'ok':True})
    if path=='medical':
        if method=='GET':
            permit(user,'medical.read'); records=repo.medical(db)
            if user['role']=='admin':
                locations=repo.application_locations(db)
                for r in records:
                    if r['id'] in locations: r['location']=locations[r['id']]
            return reply({'records':records})
        if method=='POST': permit(user,'medical.write'); return save_medical(db,b,user)
    if path=='vaccines' and method=='GET':
        medical_access(user)
        return reply({'vaccines':repo.state(db)['vaccines']})
    match=re.fullmatch(r'vaccines/(\d+)/application',path)
    if match and method=='POST':
        permit(user,'medical.write'); repo.revision(db,bump=True)
        vaccine=db.execute('SELECT * FROM vacinas WHERE cod_identificador=%s FOR UPDATE',(int(match[1]),)).fetchone()
        if not vaccine: fail(404,'Vacina não encontrada.')
        version(vaccine,b)
        if vaccine['done']: fail(409,'Aplicação de vacina já registrada.')
        applied=date(b.get('applied'))
        if applied>datetime.now(LOCAL_TZ).strftime('%Y-%m-%d'): fail(400,'A aplicação não pode estar no futuro.')
        repo.update(db,'vaccines',{'done':True,'applied':applied,'person':user['name'],'applied_by':user['id'],
                    'applied_created':now(),'version':vaccine['version']+1},'id',vaccine['id'])
        return reply({'ok':True},201)
    if path=='medication-schedule' and method=='GET':
        medical_access(user); start=date(request.query_params.get('start')); end=date(request.query_params.get('end'))
        difference=datetime.fromisoformat(end)-datetime.fromisoformat(start)
        if not timedelta(0)<=difference<=timedelta(days=7): fail(400,'Escolha um período de até 7 dias.')
        records=repo.medical(db)
        return reply({'schedule':medication_schedule(records,start,end),'unscheduled':unscheduled(records)})
    if path=='messages' and method=='GET':
        admin(user)
        configured=all(os.getenv(k) for k in ('WHATSAPP_WEBHOOK_URL','WHATSAPP_WEBHOOK_TOKEN','WHATSAPP_OWNER_TARGET','WHATSAPP_VOLUNTEERS_TARGET'))
        return reply({'configured':configured,'jobs':list(db.execute('SELECT cod_identificador,txt_destino,dat_cadastro,dat_envio,num_tentativas,txt_ultimo_erro FROM fila_mensagens ORDER BY dat_cadastro DESC LIMIT 50'))})
    fail(404,'Recurso não encontrado.')


def validate_permissions(value):
    if not isinstance(value,list) or any(p not in PERMISSIONS for p in value): fail(400,'Permissões inválidas.')
    return list(dict.fromkeys(value))


def submission(row):
    c={k:row[v] for k,v in repo.CAT_FIELDS.items() if k not in ('photo','status','approvedBy')}
    c.update(status=row['cat_status'],tags=[row['personality']],photo=0)
    return {'id':row['id'],'cat':c,'userId':row['user_id'],'status':row['status'],'version':row['version'],
            'created':row['created'],'reason':row['reason'],'reviewedBy':row['reviewed_by'],'reviewedAt':row['reviewed_at']}


def save_medical(db,b,user):
    event_id=text(b.get('id'),80); kind=text(b.get('kind'),30); cat_id=b.get('catId')
    if kind not in ('treatment','application','note','completion'): fail(400,'Tipo de registro inválido.')
    if type(cat_id) is not int or not db.execute('SELECT cod_identificador FROM gatos WHERE cod_identificador=%s',(cat_id,)).fetchone(): fail(400,'Gatinho inválido.')
    d={k:text(b.get(k,''),3000 if k=='notes' else 200,False) for k in repo.MED_FIELDS if k!='intervalHours'}
    date(d['date'])
    if d['endDate'] and (date(d['endDate'])<d['date']): fail(400,'Fim previsto anterior ao início.')
    if d['time'] and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',d['time']): fail(400,'Horário inválido.')
    if kind=='treatment':
        if not all(d[k] for k in ('label','dose','frequency','prescriber')): fail(400,'Informe medicamento, dose, frequência e referência da prescrição veterinária.')
        if 'intervalHours' in b:
            try: hours=float(b['intervalHours'])
            except (TypeError,ValueError): fail(400,'Intervalo inválido.')
            if not 1<=hours<=168 or not d['time'] or not d['endDate']: fail(400,'Informe intervalo entre 1 e 168 horas, horário inicial e fim previsto.')
            d['intervalHours']=hours
    treatment_id=None
    if kind in ('application','completion'):
        treatment_id=text(b.get('treatmentId'),80)
        t=db.execute("SELECT * FROM registros_clinicos WHERE cod_identificador=%s AND cod_gato=%s AND txt_tipo='treatment' FOR UPDATE",(treatment_id,cat_id)).fetchone()
        if not t: fail(400,'Tratamento não encontrado.')
        if d['date']<t['date']: fail(400,'A data não pode anteceder o início do tratamento.')
        if kind=='application' and not d['time']: fail(400,'Informe o horário da aplicação.')
    existing=next((r for r in repo.medical(db) if r['id']==event_id),None)
    if existing:
        if existing['cat_id']!=cat_id or existing['kind']!=kind or existing['user_id']!=user['id'] or existing['treatment_id']!=treatment_id or existing['data']!=d:
            fail(409,'Identificador já utilizado.')
        return reply({'ok':True})
    location=validate_location(b.get('location')) if kind=='application' else None
    if treatment_id and db.execute("SELECT cod_identificador FROM registros_clinicos WHERE cod_tratamento=%s AND txt_tipo='completion'",(treatment_id,)).fetchone(): fail(409,'Este tratamento já foi encerrado.')
    if kind=='note' and not d['notes']: fail(400,'Descreva a evolução clínica.')
    if kind=='application' and d['scheduledAt']:
        try: stamp=datetime.fromisoformat(d['scheduledAt'].replace('Z','+00:00')); day=stamp.astimezone(LOCAL_TZ).strftime('%Y-%m-%d')
        except ValueError: fail(400,'Dose programada inválida.')
        doses=medication_schedule(repo.medical(db),day,day)
        if not any(s['scheduledAt']==d['scheduledAt'] and s['treatmentId']==treatment_id for s in doses): fail(400,'Dose programada inválida.')
    repo.insert(db,'medical_records',{'id':event_id,'cat_id':cat_id,'kind':kind,'treatment_id':treatment_id,
                'user_id':user['id'],'created':now(),**{repo.MED_FIELDS[k]:(v or None if k=='scheduledAt' else v) for k,v in d.items()}})
    if location:
        repo.insert(db,'application_locations',{'record_id':event_id,**location})
    return reply({'ok':True},201)


def medical_access(user):
    staff(user)
    if not {'medical.read','medical.write'}.intersection(user['permissions']): fail(403,'Sem permissão para consultar cuidados.')


def validate_location(location):
    if not isinstance(location,dict): fail(400,'Autorize a localização para registrar a aplicação de medicamento.')
    values={}
    for key,minimum,maximum in [('latitude',-90,90),('longitude',-180,180),('accuracy',0,100000)]:
        value=location.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or not minimum<=value<=maximum:
            fail(400,'Localização inválida. Solicite uma nova leitura do navegador.')
        values[key]=value
    captured=location.get('capturedAt')
    if type(captured) not in (int,float) or not math.isfinite(captured) or not now()-120000<=captured<=now()+30000:
        fail(400,'A localização expirou. Solicite uma nova leitura do navegador.')
    values['captured_at']=int(captured)
    return values


def attachment_route(request,b,db,user,path,method):
    if path!='attachments' and method=='GET':
        f=db.execute('SELECT * FROM anexos WHERE cod_identificador=%s',(path.split('/')[1],)).fetchone()
        if not f: fail(404,'Arquivo não encontrado.')
        if f['owner_type']=='cat':
            public=db.execute("SELECT c.cod_identificador FROM gatos c JOIN fotos_gatos p ON p.cod_gato=c.cod_identificador WHERE c.cod_identificador=%s AND c.txt_situacao='Disponível' AND p.cod_anexo=%s",(f['cat_id'],f['id'])).fetchone()
            if not public: permit(user,'cats.photos')
        else: authorize_adoption(db,user,f['adoption_id'],request.query_params.get('token'))
        return Response(bytes(f['content']),media_type=f['mime'],headers={'Content-Disposition':'inline; filename="arquivo.'+f['mime'].split('/')[1]+'"'})
    if path=='attachments' and method=='GET':
        rid=request.query_params.get('adoptionId'); authorize_adoption(db,user,rid,request.query_params.get('token'))
        return reply({'files':list(db.execute('SELECT cod_identificador,txt_nome,txt_tipo_midia,txt_tipo_vinculo,dat_cadastro FROM anexos WHERE cod_candidatura=%s ORDER BY dat_cadastro',(rid,)))})
    if path=='attachments' and method=='POST':
        owner_type=text(b.get('ownerType'),20); name=text(b.get('name'),200); mime=text(b.get('mime'),100)
        if owner_type not in ('cat','video','term') or mime not in ('image/jpeg','image/png','video/mp4','video/webm','application/pdf'): fail(400,'Formato inválido.')
        value=b.get('data')
        if not isinstance(value,str) or len(value)>11200000: fail(400,'Arquivo inválido ou maior que 8 MB.')
        try: raw=base64.b64decode(value,validate=True)
        except (ValueError,TypeError): fail(400,'Arquivo inválido.')
        if not raw: fail(400,'Arquivo vazio.')
        if len(raw)>8*1024*1024: fail(413,'Limite de 8 MB por arquivo.')
        valid={'image/jpeg':raw.startswith(b'\xff\xd8\xff'),'image/png':raw.startswith(b'\x89PNG\r\n\x1a\n'),
               'application/pdf':raw.startswith(b'%PDF-'),'video/mp4':raw[4:8]==b'ftyp','video/webm':raw.startswith(b'\x1a\x45\xdf\xa3')}[mime]
        if not valid: fail(400,'Conteúdo não corresponde ao formato do arquivo.')
        cat_id=None; rid=None
        if owner_type=='cat':
            permit(user,'cats.photos'); repo.revision(db,bump=True)
            if not mime.startswith('image/'): fail(400,'Envie uma foto JPEG ou PNG.')
            try: cat_id=int(b.get('ownerId'))
            except (ValueError,TypeError): fail(400,'Gato inválido.')
            if not db.execute('SELECT cod_identificador FROM gatos WHERE cod_identificador=%s FOR UPDATE',(cat_id,)).fetchone(): fail(404,'Gato não encontrado.')
            count=db.execute('SELECT count(*) AS num_contagem FROM anexos WHERE cod_gato=%s',(cat_id,)).fetchone()['count']
        else:
            rid=text(b.get('ownerId'),80); authorize_adoption(db,user,rid,b.get('token')); adopt_row(db,rid,True)
            if owner_type=='term':
                admin(user)
                if mime!='application/pdf': fail(400,'Envie o termo em PDF.')
            elif not mime.startswith('video/'): fail(400,'Envie vídeo MP4 ou WebM.')
            elif not (privacy.latest(db,rid) or {}).get('homeVideoConsent'):
                fail(400,'O vídeo exige autorização específica da pessoa candidata. Ela pode confirmar pelo link privado ou combinar uma avaliação sem vídeo.')
            count=db.execute('SELECT count(*) AS num_contagem FROM anexos WHERE cod_candidatura=%s AND txt_tipo_vinculo=%s',(rid,owner_type)).fetchone()['count']
        if count>=10: fail(400,'Limite de 10 arquivos por registro.')
        fid=uid(); repo.insert(db,'attachments',{'id':fid,'owner_type':owner_type,'cat_id':cat_id,'adoption_id':rid,'name':name,'mime':mime,'content':raw,'created':now()})
        if cat_id: db.execute('INSERT INTO fotos_gatos VALUES(%s,%s) ON CONFLICT(cod_gato) DO UPDATE SET cod_anexo=excluded.cod_anexo',(cat_id,fid))
        return reply({'id':fid},201)
    fail(404,'Recurso não encontrado.')


def handle(request,b,pool):
    try:
        with pool.connection() as db:
            return dispatch(request,b,db,pool)
    except psycopg.errors.UniqueViolation as e:
        message='Dose já registrada.' if e.diag.constraint_name=='uq_registros_dose_prevista' else 'Registro já existente ou alterado por outra pessoa.'
        return reply({'error':message},409)
    except (psycopg.errors.ForeignKeyViolation,psycopg.errors.CheckViolation):
        return reply({'error':'Os registros relacionados são inválidos.'},400)
    except (psycopg.errors.DeadlockDetected,psycopg.errors.SerializationFailure):
        return reply({'error':'Outra pessoa atualizou os registros. Recarregue antes de salvar.'},409)


def create_app(database_url=None, seed=None):
    @asynccontextmanager
    async def lifespan(app):
        pool=make_pool(database_url); pool.open(); pool.wait()
        try:
            await run_in_threadpool(initialize_database,pool)
            should_seed = seed if seed is not None else os.getenv('SEED_DEMO','false').lower()=='true'
            if should_seed:
                await run_in_threadpool(seed_demo,pool)
            app.state.pool=pool
            yield
        finally:
            pool.close()
    app=FastAPI(title='Peticas — API Python',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

    @app.exception_handler(HTTPException)
    async def fault(request,error):
        return reply({'error':error.detail},error.status_code)

    @app.middleware('http')
    async def headers(request,call_next):
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api/') else 'no-cache'
        return response

    @app.api_route('/api/{path:path}',methods=['GET','HEAD','POST','PUT','PATCH','DELETE'])
    async def api(request:Request,path:str):
        b={}
        if request.method not in ('GET','HEAD'):
            origin=str(request.url).split('/api/')[0]
            if request.headers.get('origin')!=origin: fail(403,'Origem da solicitação inválida.')
            if 'application/json' not in request.headers.get('content-type',''): fail(415,'Envie dados JSON.')
            maximum=12000000 if path=='attachments' else 65536
            raw=bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw)>maximum: fail(413,'Conteúdo muito grande.')
            try: b=json.loads(raw)
            except (ValueError,UnicodeDecodeError): fail(400,'Dados inválidos.')
            if not isinstance(b,dict): fail(400,'Envie um objeto JSON.')
        try:
            return await run_in_threadpool(handle,request,b,app.state.pool)
        except HTTPException: raise
        except Exception:
            logging.exception('Peticas request failed')
            return reply({'error':'Não foi possível concluir. Tente novamente.'},500)
    app.mount('/',StaticFiles(directory=ROOT/'public',html=True),name='interface')
    return app


app=create_app()
