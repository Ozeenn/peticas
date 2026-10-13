"""Portuguese SQL names; English keys exist only in the browser compatibility layer."""
TABLES = {
 'users':'usuarios','permissions':'permissoes','user_permissions':'permissoes_usuarios',
 'volunteer_profiles':'fichas_voluntarios','sessions':'sessoes','rate_limits':'limites_requisicoes',
 'app_config':'configuracoes','state_revision':'revisoes_estado','cats':'gatos','cat_tags':'caracteristicas_gatos',
 'cat_submissions':'propostas_gatos','vaccines':'vacinas','care_tasks':'tarefas_cuidados',
 'adoption_requests':'candidaturas_adocao','adoption_answers':'respostas_entrevistas',
 'adoption_stage_history':'historico_etapas_adocao','adoption_events':'eventos_adocao',
 'medical_records':'registros_clinicos','attachments':'anexos','cat_photos':'fotos_gatos',
 'campaigns':'campanhas','message_jobs':'fila_mensagens','gateway_jobs':'envios_whatsapp',
 'gateway_deliveries':'entregas_whatsapp','schema_migrations':'migracoes_esquema',
 'application_locations':'localizacoes_aplicacoes','adoption_messages':'mensagens_candidaturas'
}
COLUMNS = {
 'id':'cod_identificador','name':'txt_nome','email':'txt_email','password':'txt_senha_hash','role':'txt_perfil',
 'created':'dat_cadastro','recovery_hash':'txt_recuperacao_hash','user_id':'cod_usuario',
 'permission':'txt_permissao','cpf':'txt_cpf','age':'txt_idade','address':'txt_endereco','phone':'txt_telefone',
 'occupation':'txt_ocupacao','transport':'txt_transporte','experience':'txt_experiencia','animals':'txt_animais',
 'skills':'txt_habilidades','days':'txt_dias','hours':'txt_horas','frequency':'txt_frequencia',
 'preferences':'txt_preferencias','motivation':'txt_motivacao','commitment':'txt_compromisso','rules':'txt_regras',
 'signature':'txt_assinatura','signed_at':'dat_assinatura','expires':'dat_expiracao','key':'txt_chave',
 'count':'num_contagem','value':'txt_valor','version':'num_versao','sex':'txt_sexo','personality':'txt_personalidade',
 'status':'txt_situacao','story':'txt_historia','color':'txt_cor','entry_date':'dat_entrada',
 'rescue_location':'txt_local_resgate','rescuer':'txt_resgatante','rescue_report':'txt_relato_resgate',
 'photo':'num_foto_exemplo','approved_by':'cod_aprovador','cat_id':'cod_gato','position':'num_posicao',
 'label':'txt_descricao','reviewed_by':'cod_revisor','reviewed_at':'dat_revisao','reason':'txt_motivo',
 'cat_status':'txt_situacao_gato','approved_cat_id':'cod_gato_aprovado','date':'dat_data',
 'done':'flg_realizado','applied':'dat_aplicacao','person':'txt_responsavel','next':'dat_proxima_dose',
 'proof':'txt_comprovante','time':'hor_horario','token_hash':'txt_token_hash','cpf_hash':'txt_cpf_hash',
 'stage':'num_etapa','guidance':'txt_orientacao','note':'txt_observacao','rejection_reason':'txt_motivo_reprovacao',
 'returned':'flg_devolvido','adoption_id':'cod_candidatura','question':'txt_pergunta','answer':'txt_resposta',
 'kind':'txt_tipo','notes':'txt_anotacoes','treatment_id':'cod_tratamento','dose':'txt_dose',
 'end_date':'dat_fim_previsto','prescriber':'txt_prescritor','scheduled_at':'dat_dose_prevista',
 'interval_hours':'num_intervalo_horas','owner_type':'txt_tipo_vinculo','mime':'txt_tipo_midia',
 'content':'bin_conteudo','attachment_id':'cod_anexo','url':'txt_endereco_web','target':'txt_destino',
 'message':'txt_mensagem','sent':'dat_envio','attempts':'num_tentativas','next_attempt':'dat_proxima_tentativa',
 'last_error':'txt_ultimo_erro','fingerprint':'txt_impressao_hash','job_id':'cod_envio',
 'recipient_hash':'txt_destinatario_hash','state':'txt_estado','meta_id':'txt_identificador_meta',
 'updated':'dat_atualizacao','checksum':'txt_verificacao_hash','responsible':'txt_responsavel_registro',
 'record_id':'cod_registro','latitude':'num_latitude','longitude':'num_longitude',
 'accuracy':'num_precisao_metros','captured_at':'dat_coleta','applied_by':'cod_usuario_aplicacao',
 'applied_created':'dat_registro_aplicacao'
}
REVERSE_COLUMNS = {v:k for k,v in COLUMNS.items()}

# Browser timestamps use milliseconds; PostgreSQL stores typed instants/dates.
EPOCH_FIELDS = {'created','reviewed_at','expires','sent','next_attempt','updated','captured_at','applied_created'}
DATE_FIELDS = {'signed_at','entry_date','date','applied','next','end_date'}


def encode_value(field,value,table=None):
    from fastapi import HTTPException
    try:
        return _encode_value(field,value,table)
    except (ValueError,TypeError,OverflowError):
        raise HTTPException(400,'Confira as datas e os horários informados.') from None


def _encode_value(field,value,table=None):
    from datetime import datetime, date, time, timezone
    if value is None: return None
    if field in EPOCH_FIELDS:
        return datetime.fromtimestamp(value/1000,timezone.utc)
    if field in DATE_FIELDS:
        if value=='': return None
        if field=='date' and table=='adoption_stage_history':
            return datetime.fromisoformat(value.replace('Z','+00:00'))
        if field=='date' and table=='adoption_requests' and '/' in value:
            return datetime.strptime(value,'%d/%m/%Y').date()
        return date.fromisoformat(value)
    if field=='scheduled_at':
        return datetime.fromisoformat(value.replace('Z','+00:00')) if value else None
    if field=='time':
        return time.fromisoformat(value) if value else None
    return value


def decode_value(field,value):
    from datetime import datetime, date, time, timezone
    if value is None:
        return '' if field in DATE_FIELDS or field=='time' else None
    if isinstance(value,datetime):
        if field in EPOCH_FIELDS: return int(value.timestamp()*1000)
        return value.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
    if isinstance(value,date): return value.isoformat()
    if isinstance(value,time): return value.isoformat(timespec='minutes')
    return value
