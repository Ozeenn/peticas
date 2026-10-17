"""Draft privacy information, versioned acknowledgements and manual requests."""
import hashlib
import json
from .security import fail, text, email, now, uid

TEMPLATE_VERSION='2026-10-16.4'
DEFAULTS={'controller':'Gatil Peticas','identifier':'','address':'','contact':'','retention':'A conservação dos registros considera a finalidade de cada atendimento e as obrigações aplicáveis. Pedidos de eliminação podem ser registrados no formulário de privacidade.'}


def config(db):
    rows={r['key'].removeprefix('privacy:'):r['value'] for r in db.execute("SELECT txt_chave,txt_valor FROM configuracoes WHERE txt_chave LIKE 'privacy:%%'")}
    return {**DEFAULTS,**rows}


def notice(db):
    c=config(db)
    sections=[
        ('Uso do site','Esta política abrange a navegação no Peticas, o contato com a equipe, as candidaturas e o acesso de voluntários e da responsável. Cada recurso utiliza os dados necessários à sua finalidade. O aceite dos Termos de Uso e a ciência desta política não autorizam publicidade nem substituem escolhas específicas, como a autorização opcional do vídeo.'),
        ('Armazenamento no navegador','O site utiliza um cookie de sessão para o acesso da equipe e armazenamento local para lembrar a versão dos termos e da política reconhecida neste navegador. Essa preferência contém a versão e a data do aceite, sem dados da candidatura. O carrinho guarda no navegador e no servidor as estampas, os tamanhos e as quantidades escolhidos, sem dados de identificação ou pagamento. Uma referência privada neste navegador permite recuperar a seleção; não a compartilhe. O acesso ao carrinho no servidor expira após 30 dias sem atualização. Você pode esvaziar o carrinho, revisar os documentos pelo rodapé ou remover esses registros nas configurações do navegador.'),
        ('Responsável e contato',f"Responsável pelo tratamento: {c['controller']}. Endereço: {c['address'] or 'Av. Santana, 720 - Centro, Botucatu - SP, 18600-020'}. Canal para direitos: {c['contact'] or 'formulário de pedidos de privacidade disponível neste site'}. A identificação documental da responsável é utilizada nos termos internos e não é exposta neste aviso."),
        ('Dados e finalidades','Nome, CPF, idade, contato, endereço e respostas sobre a segurança do lar são usados para avaliar a candidatura solicitada, combinar a visita, formalizar e acompanhar a adoção. A ciência desta política informa esse uso e não autoriza outras finalidades.'),
        ('Vídeo da residência - consentimento separado','O envio de vídeo é opcional. Com autorização específica, o vídeo é acessado pela responsável para avaliar a proteção do lar. Não filme rostos, documentos, conversas ou dados de terceiros. Recusar ou revogar essa autorização não impede a candidatura; a equipe pode combinar uma visita ou outra forma adequada de avaliação. O material não será usado para publicidade.'),
        ('Acesso e serviços','A responsável acessa entrevistas e arquivos. Voluntários acessam somente as atividades autorizadas; a consulta por CPF retorna as etapas das candidaturas, sem comprovar identidade. O link privado permite consultar mensagens e anexos: guarde-o em segurança. Hospedagem e banco processam os registros. Ao entrar em contato pelo WhatsApp, as mensagens e os dados enviados também são processados por esse serviço, conforme suas próprias condições de uso e privacidade. Não há venda de dados nem consentimento para marketing neste aviso.'),
        ('Voluntários e localização','A ficha de voluntário registra identificação, contato, disponibilidade e aceite. Nas aplicações de medicamento, a localização do dispositivo, precisão e momento da coleta ficam disponíveis somente à responsável. O sistema não acompanha deslocamentos. A localização é solicitada pontualmente no registro da aplicação; a permissão é controlada pelo navegador.'),
        ('Guarda',c['retention']+' Dados sem necessidade devem ser eliminados ou anonimizados, ressalvadas hipóteses legais de conservação. Backups e documentos impressos também exigem controle de acesso e política de descarte.'),
        ('Seus direitos','Você pode solicitar confirmação e acesso, correção, informações sobre compartilhamento, anonimização, bloqueio ou eliminação quando cabíveis, e revogação do consentimento. Use o canal indicado ou o formulário deste site. O pedido é gratuito; a equipe verificará sua identidade de forma proporcional antes de fornecer dados ou alterar registros. A exclusão não é automática: a responsável avaliará a finalidade e eventual conservação legal e informará o resultado. É possível procurar a ANPD.'),
        ('Minimização','Informe apenas o necessário para a adoção. Não inclua nomes, documentos, condições de saúde ou imagens de outras pessoas. A avaliação e as decisões são realizadas pela responsável; o sistema não decide candidaturas automaticamente.'),
    ]
    terms=[
        ('Sobre o Peticas','O Peticas apresenta os gatos do gatil e permite solicitar e acompanhar adoções, entrar em contato e organizar as atividades da equipe. A disponibilidade dos animais e as informações são atualizadas pela responsável.'),
        ('Uso responsável','Ao utilizar os serviços, forneça informações verdadeiras e apenas os dados solicitados. Respeite as pessoas e os animais. Não envie conteúdo ofensivo, arquivos maliciosos ou dados e imagens de terceiros sem autorização. Não tente acessar registros ou contas de outras pessoas.'),
        ('Candidaturas e adoção','Enviar uma candidatura não garante reserva ou adoção. A equipe analisa a compatibilidade e a segurança do lar, combina as próximas etapas e formaliza a adoção em termo próprio. O aceite destes termos não substitui o termo de adoção.'),
        ('Acessos e comunicação','Guarde sua senha e o link privado da candidatura com cuidado. Utilize os canais do gatil para esclarecer dúvidas ou comunicar problemas. O acesso da equipe é pessoal e limitado às atividades autorizadas.'),
        ('Privacidade e escolhas opcionais','Os dados são tratados conforme a Política de Privacidade. A autorização de vídeo da residência é separada e opcional; a equipe pode combinar uma visita ou outra forma de avaliação. O aceite geral não autoriza o uso de imagens para publicidade.'),
        ('Atualizações e contato','Os termos e a política podem ser atualizados para refletir mudanças no serviço. Quando a versão mudar, o site apresentará novamente o aviso. Consulte a identificação e o canal de contato na Política de Privacidade.'),
    ]
    snapshot='\n\n'.join(title+'\n'+body for title,body in [('Termos de Uso',''),*terms,('Política de Privacidade',''),*sections])
    version=TEMPLATE_VERSION+'-'+hashlib.sha256(snapshot.encode()).hexdigest()[:12]
    return {'version':version,'templateVersion':TEMPLATE_VERSION,'config':c,'sections':[{'title':t,'text':b} for t,b in sections],'terms':[{'title':t,'text':b} for t,b in terms],
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
