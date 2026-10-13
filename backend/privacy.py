"""Draft privacy information, versioned acknowledgements and manual requests."""
import hashlib
import json
from .security import fail, text, email, now, uid

TEMPLATE_VERSION='2026-10-13.1'
DEFAULTS={'controller':'Gatil Peticas','identifier':'','address':'','contact':'','retention':'Revisar periodicamente a necessidade de cada registro; os prazos devem ser definidos pela responsável conforme a finalidade e as obrigações aplicáveis.'}


def config(db):
    rows={r['key'].removeprefix('privacy:'):r['value'] for r in db.execute("SELECT txt_chave,txt_valor FROM configuracoes WHERE txt_chave LIKE 'privacy:%%'")}
    return {**DEFAULTS,**rows}


def notice(db):
    c=config(db)
    sections=[
        ('Responsável e contato',f"Responsável pelo tratamento: {c['controller']}. Endereço: {c['address'] or 'a completar pela responsável'}. Canal para direitos: {c['contact'] or 'formulário de pedidos de privacidade disponível neste site'}. A identificação documental da responsável é utilizada nos termos internos e não é exposta neste aviso."),
        ('Dados e finalidades','Nome, CPF, idade, contato, endereço e respostas sobre a segurança do lar são usados para avaliar a candidatura solicitada, combinar a visita, formalizar e acompanhar a adoção. O tratamento necessário aos procedimentos preliminares e à adoção deve ser avaliado pela responsável no contexto do art. 7º, V, da LGPD. A ciência deste aviso não é uma autorização genérica nem substitui essa avaliação.'),
        ('Vídeo da residência - consentimento separado','O envio de vídeo é opcional. Com autorização específica, o vídeo é acessado pela responsável para avaliar a proteção do lar. Não filme rostos, documentos, conversas ou dados de terceiros. Recusar ou revogar essa autorização não impede a candidatura; a equipe pode combinar uma visita ou outra forma adequada de avaliação. O material não será usado para publicidade.'),
        ('Acesso e serviços','A responsável acessa entrevistas e arquivos. Voluntários acessam somente as atividades autorizadas; a consulta por CPF retorna as etapas das candidaturas, sem comprovar identidade. O link privado permite consultar mensagens e anexos: guarde-o em segurança. Hospedagem e banco processam os registros. Quando configurado, o WhatsApp/Meta processa mensagens e dados necessários ao contato; a responsável deve verificar contratos, localização dos serviços e eventual transferência internacional. Não há venda de dados nem consentimento para marketing neste aviso.'),
        ('Voluntários e localização','A ficha de voluntário registra identificação, contato, disponibilidade e aceite. Nas aplicações de medicamento, a localização do dispositivo, precisão e momento da coleta ficam disponíveis somente à responsável. O sistema não acompanha deslocamentos. A responsável deve justificar a necessidade e a base legal desse tratamento; a permissão do navegador não é, sozinha, a comprovação de consentimento válido.'),
        ('Guarda',c['retention']+' Dados sem necessidade devem ser eliminados ou anonimizados, ressalvadas hipóteses legais de conservação. Backups e documentos impressos também exigem controle de acesso e política de descarte.'),
        ('Seus direitos','Você pode solicitar confirmação e acesso, correção, informações sobre compartilhamento, anonimização, bloqueio ou eliminação quando cabíveis, e revogação do consentimento. Use o canal indicado ou o formulário deste site. O pedido é gratuito; a equipe verificará sua identidade de forma proporcional antes de fornecer dados ou alterar registros. A exclusão não é automática: a responsável avaliará a finalidade e eventual conservação legal e informará o resultado. É possível procurar a ANPD.'),
        ('Minimização','Informe apenas o necessário para a adoção. Não inclua nomes, documentos, condições de saúde ou imagens de outras pessoas. A avaliação e as decisões são realizadas pela responsável; o sistema não decide candidaturas automaticamente.'),
    ]
    snapshot='\n\n'.join(title+'\n'+body for title,body in sections)
    version=TEMPLATE_VERSION+'-'+hashlib.sha256(snapshot.encode()).hexdigest()[:12]
    return {'version':version,'templateVersion':TEMPLATE_VERSION,'config':c,'sections':[{'title':t,'text':b} for t,b in sections],
            'snapshot':snapshot,'draft':not all(c[k] for k in ('identifier','address','contact'))}


def record(db,rid,body):
    current=notice(db)
    if body.get('privacyAcknowledged') is not True: fail(400,'Leia o aviso de privacidade e confirme a ciência para enviar a candidatura.')
    if body.get('privacyVersion')!=current['version']: fail(409,'O aviso de privacidade mudou. Abra a versão atual e confirme a ciência novamente.')
    consent=body.get('homeVideoConsent',False)
    if type(consent) is not bool: fail(400,'Informe uma escolha válida para o vídeo da residência.')
    db.execute('INSERT INTO registros_privacidade(cod_identificador,cod_candidatura,txt_versao_aviso,txt_aviso,flg_ciencia,flg_consentimento_video) VALUES(%s,%s,%s,%s,true,%s)',
               (uid(),rid,current['version'],current['snapshot'],consent))


def latest(db,rid):
    r=db.execute('SELECT txt_versao_aviso,flg_ciencia,flg_consentimento_video,dat_cadastro FROM registros_privacidade WHERE cod_candidatura=%s ORDER BY dat_cadastro DESC,cod_identificador DESC LIMIT 1',(rid,)).fetchone()
    return {'version':r['txt_versao_aviso'],'acknowledged':r['flg_ciencia'],'homeVideoConsent':r['flg_consentimento_video'],'date':r['created']} if r else None


def acknowledged_text(db,rid):
    r=db.execute('SELECT txt_aviso FROM registros_privacidade WHERE cod_candidatura=%s ORDER BY dat_cadastro DESC,cod_identificador DESC LIMIT 1',(rid,)).fetchone()
    return r['txt_aviso'] if r else ''


def save_config(db,body):
    for key,maximum in [('controller',200),('identifier',100),('address',500),('contact',300),('retention',2000)]:
        value=text(body.get(key,''),maximum)
        db.execute('INSERT INTO configuracoes VALUES(%s,%s) ON CONFLICT(txt_chave) DO UPDATE SET txt_valor=excluded.txt_valor',('privacy:'+key,value))


def create_request(db,body):
    kind=body.get('kind')
    if kind not in ('access','correction','deletion','revocation','other'): fail(400,'Escolha o tipo de solicitação.')
    rid=uid()
    db.execute('INSERT INTO solicitacoes_privacidade(cod_identificador,txt_nome,txt_email,txt_tipo,txt_descricao) VALUES(%s,%s,%s,%s,%s)',
               (rid,text(body.get('name'),100),email(body.get('email')),kind,text(body.get('description'),3000)))
    return rid


def requests(db):
    return [dict(r) for r in db.execute('SELECT * FROM solicitacoes_privacidade ORDER BY dat_cadastro DESC')]
