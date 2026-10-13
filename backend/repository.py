"""Relational storage; assemble the existing browser's API representation."""
from psycopg import sql
from .security import fail, text, date
from .naming import TABLES, COLUMNS, encode_value

CAT_FIELDS = {'name': 'name', 'age': 'age', 'sex': 'sex', 'personality': 'personality',
              'status': 'status', 'story': 'story', 'color': 'color', 'entryDate': 'entry_date',
              'rescueLocation': 'rescue_location', 'rescuer': 'rescuer', 'rescueReport': 'rescue_report',
              'photo': 'photo', 'approvedBy': 'approved_by'}
MED_FIELDS = {'label': 'label', 'date': 'date', 'time': 'time', 'dose': 'dose',
              'frequency': 'frequency', 'endDate': 'end_date', 'prescriber': 'prescriber',
              'notes': 'notes', 'scheduledAt': 'scheduled_at', 'intervalHours': 'interval_hours'}
PROFILE_FIELDS = ['cpf','age','address','phone','occupation','transport','experience','animals','skills',
                  'days','hours','frequency','preferences','motivation','commitment','rules','signature','signedAt']


def insert(db, table, values):
    query = sql.SQL('INSERT INTO {} ({}) VALUES ({}) RETURNING *').format(
        sql.Identifier(TABLES[table]), sql.SQL(',').join(sql.Identifier(COLUMNS[k]) for k in values),
        sql.SQL(',').join(sql.Placeholder() for _ in values))
    return db.execute(query, tuple(encode_value(k,v,table) for k,v in values.items())).fetchone()


def update(db, table, values, key, value):
    query = sql.SQL('UPDATE {} SET {} WHERE {}=%s').format(
        sql.Identifier(TABLES[table]), sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(COLUMNS[k])) for k in values),
        sql.Identifier(COLUMNS[key]))
    return db.execute(query, (*[encode_value(k,v,table) for k,v in values.items()], value))


def validate_cat(b):
    c = {}
    for key, maximum in [('name',100),('age',50),('sex',20),('personality',200),('story',3000),
                         ('color',100),('entryDate',10),('rescueLocation',300),('rescuer',200),('rescueReport',3000)]:
        c[key] = text(b.get(key, ''), maximum, key != 'story')
    date(c['entryDate'])
    if c['sex'] not in ('Fêmea', 'Macho') or b.get('status') not in ('Disponível','Em tratamento','Reservado','Adotado'):
        fail(400, 'Situação ou sexo inválido.')
    c.update(status=b['status'], tags=[c['personality']], photo=b.get('photo', 0))
    return c


def insert_cat(db, c):
    values = {v: c[k] for k, v in CAT_FIELDS.items() if k in c}
    if 'id' in c:
        values['id'] = c['id']
    row = insert(db, 'cats', values)
    for i, tag in enumerate(c.get('tags', [])):
        insert(db, 'cat_tags', {'cat_id': row['id'], 'position': i, 'label': tag})
    db.execute("SELECT setval(pg_get_serial_sequence('gatos','cod_identificador'), COALESCE((SELECT max(cod_identificador) FROM gatos),1),true)")
    return row['id']


def update_cat(db, c):
    update(db, 'cats', {v: c[k] for k, v in CAT_FIELDS.items() if k in c}, 'id', c['id'])
    db.execute('DELETE FROM caracteristicas_gatos WHERE cod_gato=%s', (c['id'],))
    for i, tag in enumerate(c['tags']):
        insert(db, 'cat_tags', {'cat_id': c['id'], 'position': i, 'label': tag})


def cats(db):
    tags = {}
    for row in db.execute('SELECT * FROM caracteristicas_gatos ORDER BY cod_gato,num_posicao'):
        tags.setdefault(row['cat_id'], []).append(row['label'])
    out = []
    for row in db.execute('SELECT c.*,p.cod_anexo FROM gatos c LEFT JOIN fotos_gatos p ON p.cod_gato=c.cod_identificador ORDER BY c.cod_identificador'):
        c = {'id': row['id'], **{k: row[v] for k, v in CAT_FIELDS.items() if row[v] is not None}, 'tags': tags.get(row['id'], [])}
        if row['attachment_id']:
            c['photoId'] = row['attachment_id']
        out.append(c)
    return out


UNSPECIFIED = object()


def revision(db, expected=UNSPECIFIED, bump=False):
    r = db.execute('SELECT num_versao FROM revisoes_estado WHERE cod_identificador=1 FOR UPDATE').fetchone()['version']
    if expected is not UNSPECIFIED and (type(expected) is not int or expected != r):
        fail(409, 'Os registros mudaram. Recarregue e tente novamente.')
    if bump:
        db.execute('UPDATE revisoes_estado SET num_versao=num_versao+1 WHERE cod_identificador=1')
    return r + int(bump)


def state(db):
    vaccines = []
    for r in db.execute('SELECT * FROM vacinas ORDER BY num_posicao,cod_identificador'):
        vaccines.append({'id':r['id'],'version':r['version'],'cat': r['cat_id'], **{k:r[k] for k in ('label','date','status','done','applied','person','next','proof')}})
    meds = [{'cat': r['cat_id'], **{k:r[k] for k in ('label','time','done')}} for r in db.execute('SELECT * FROM tarefas_cuidados ORDER BY num_posicao,cod_identificador')]
    return {'cats': cats(db), 'vaccines': vaccines, 'meds': meds,
            'version': db.execute('SELECT num_versao FROM revisoes_estado WHERE cod_identificador=1').fetchone()['version']}


def replace_state(db, b):
    for key, maximum in [('cats',500),('vaccines',5000),('meds',5000)]:
        if not isinstance(b.get(key), list) or len(b[key]) > maximum or any(not isinstance(x,dict) for x in b[key]):
            fail(400, 'Registros inválidos.')
    revision(db, b.get('version'), True)
    current = {c['id']:c for c in cats(db)}
    incoming = set()
    for c in b['cats']:
        text(c.get('name'), 100); text(c.get('age'), 50); text(c.get('story',''),3000,False)
        if type(c.get('id')) is not int or c['id'] in incoming or c.get('status') not in ('Disponível','Em tratamento','Reservado','Adotado'):
            fail(400, 'Cadastro de gato inválido.')
        if not isinstance(c.get('tags'), list) or len(c['tags']) > 30:
            fail(400, 'Características inválidas.')
        for tag in c['tags']:
            text(tag,200)
        incoming.add(c['id'])
        if c['id'] in current:
            # A bulk care save cannot undo a reservation, adoption or return.
            if c['status'] != current[c['id']]['status']:
                fail(400, 'Altere a situação pelo cadastro ou pela candidatura.')
            if c != current[c['id']]:
                fail(400, 'Altere os dados do gato pelo cadastro individual.')
        else:
            checked = validate_cat(c)
            if checked['status'] not in ('Disponível','Em tratamento'):
                fail(400, 'Novos gatos devem estar disponíveis ou em tratamento.')
            insert_cat(db, {**checked,'id':c['id']})
    if set(current) - incoming:
        fail(400, 'O histórico dos gatos deve ser preservado.')
    old_vaccines={v['id']:v for v in state(db)['vaccines']}
    vaccine_ids=set()
    db.execute('DELETE FROM tarefas_cuidados')
    for i, v in enumerate(b['vaccines']):
        if v.get('cat') not in incoming or type(v.get('done')) is not bool:
            fail(400, 'Vacina inválida.')
        if v.get('applied'): date(v['applied'])
        if v.get('next'): date(v['next'])
        date(v.get('date'))
        values={'cat_id':v['cat'],'position':i,'done':v['done'],
                **{k:text(v.get(k,''),300,k in ('label','date','status')) for k in ('label','date','status','applied','person','next','proof')}}
        if 'id' in v:
            if v['id'] not in old_vaccines or v['id'] in vaccine_ids: fail(400,'Vacina inválida.')
            vaccine_ids.add(v['id'])
            if v != old_vaccines[v['id']]: fail(400,'Registre a aplicação de vacina pela ação individual.')
        else:
            if v['done']: fail(400,'Cadastre a vacina prevista antes de registrar a aplicação.')
            insert(db,'vaccines',values)
    if set(old_vaccines)-vaccine_ids: fail(400,'Preserve o histórico das vacinas cadastradas.')
    for i, v in enumerate(b['meds']):
        if v.get('cat') not in incoming or type(v.get('done')) is not bool:
            fail(400, 'Cuidado inválido.')
        insert(db, 'care_tasks', {'cat_id':v['cat'],'position':i,'done':v['done'],
                                'label':text(v.get('label')),'time':text(v.get('time'),5)})
    return b['version'] + 1


def adoption(db, row):
    answers = {r['question']:r['answer'] for r in db.execute('SELECT txt_pergunta,txt_resposta FROM respostas_entrevistas WHERE cod_candidatura=%s', (row['id'],))}
    history = [{ 'id':r['id'],'kind':r['kind'],'date':r['date'],'notes':r['notes'],'userId':r['user_id'],'created':r['created']}
               for r in db.execute('SELECT * FROM eventos_adocao WHERE cod_candidatura=%s ORDER BY dat_cadastro,cod_identificador', (row['id'],))]
    stages = [{'stage':r['stage'],'date':r['date'],'userId':r['user_id']} for r in db.execute('SELECT * FROM historico_etapas_adocao WHERE cod_candidatura=%s ORDER BY cod_identificador', (row['id'],))]
    return {'id':row['id'],'name':answers.get('name',''),'cat':row['cat_id'],'stage':row['stage'],
            'date':row['date'],'guidance':row['guidance'],'note':row['note'],'rejectionReason':row['rejection_reason'],
            'returned':row['returned'],'version':row['version'],'answers':answers,'history':history,'stageHistory':stages}


def medical(db):
    out = []
    for row in db.execute('SELECT m.*,u.txt_nome AS txt_responsavel_registro FROM registros_clinicos m JOIN usuarios u ON u.cod_identificador=m.cod_usuario ORDER BY m.dat_cadastro DESC,m.cod_identificador DESC'):
        data = {k: (row[v] or '') for k,v in MED_FIELDS.items() if k != 'intervalHours'}
        if row['interval_hours'] is not None:
            data['intervalHours'] = row['interval_hours']
        out.append({**{k:row[k] for k in ('id','cat_id','kind','treatment_id','user_id','created','responsible','scheduled_at')},'data':data})
    return out


def stage_history(db,row):
    from datetime import datetime, timezone
    received=datetime.fromtimestamp(row['created']/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
    history=[{'stage':0,'date':received}]
    history.extend({'stage':r['stage'],'date':r['date']} for r in db.execute(
        'SELECT num_etapa,dat_data FROM historico_etapas_adocao WHERE cod_candidatura=%s ORDER BY cod_identificador',(row['id'],)))
    return history


def adoption_messages(db,rid):
    return [{'text':r['message'],'date':r['created']} for r in db.execute(
        'SELECT txt_mensagem,dat_cadastro FROM mensagens_candidaturas WHERE cod_candidatura=%s ORDER BY dat_cadastro,cod_identificador',(rid,))]


def application_locations(db):
    return {r['record_id']:{'latitude':r['latitude'],'longitude':r['longitude'],'accuracy':r['accuracy'],'capturedAt':r['captured_at']}
            for r in db.execute('SELECT * FROM localizacoes_aplicacoes')}
