"""Branded PDFs generated in memory, accessible only to the administrator."""
from io import BytesIO
from datetime import datetime
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether, HRFlowable, Table, TableStyle, PageBreak

from .db import ROOT
from . import repository as repo
from . import privacy
from .security import fail, LOCAL_TZ

NAVY=colors.HexColor('#092d80'); CYAN=colors.HexColor('#00afe6')
KINDS={'treatment':'Tratamento','application':'Aplicação','note':'Evolução clínica','completion':'Encerramento'}
STAGES={-1:'Reprovada',0:'Recebida',1:'Entrevista em análise',2:'Visita domiciliar',3:'Aprovada',4:'Adoção concluída'}
CAT_LABELS={'id':'Identificador','name':'Nome','age':'Idade aproximada','sex':'Sexo','personality':'Personalidade',
 'status':'Situação','story':'História','color':'Cor','entryDate':'Data de entrada','rescueLocation':'Local do resgate',
 'rescuer':'Quem resgatou','rescueReport':'Relatório do resgate','approvedBy':'Identificador de quem aprovou',
 'photo':'Referência de foto ilustrativa','photoId':'Identificador da foto atual','tags':'Características'}
MED_LABELS={'label':'Medicamento / registro','date':'Data','time':'Horário','dose':'Dose prescrita','frequency':'Frequência',
 'endDate':'Fim previsto','prescriber':'Referência da prescrição','notes':'Observações','scheduledAt':'Dose prevista',
 'intervalHours':'Intervalo em horas'}
ANSWER_LABELS={'name':'Nome','cpf':'CPF','email':'E-mail','phone':'Telefone','age':'Idade','address':'Endereço',
 'household':'Pessoas na residência','children':'Convivência com crianças','agreement':'Concordância da casa',
 'home':'Tipo de moradia','permission':'Permissão para animais','moving':'Mudanças','travel':'Viagens',
 'pets':'Experiência com animais','currentPets':'Animais atuais','vet':'Veterinário','work':'Trabalho',
 'routine':'Rotina','preferences':'Preferências','security':'Proteção do lar','occupation':'Ocupação',
 'motivation':'Motivação','vaccinated':'Vacinação dos animais','tests':'Exames dos animais','income':'Renda informada',
 'food':'Cuidados e alimentação','source':'Como conheceu o gatil','allergy':'Informação antiga de saúde - acesso restrito'}


def fonts():
    directory=Path(reportlab.__file__).parent/'fonts'
    if 'Peticas' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('Peticas',directory/'Vera.ttf'))
        pdfmetrics.registerFont(TTFont('Peticas-Bold',directory/'VeraBd.ttf'))
    return 'Peticas'


def printable(value):
    if isinstance(value,list): value=', '.join(map(str,value))
    if value is None or value=='': return 'Não informado'
    if isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        return datetime.fromisoformat(value).strftime('%d/%m/%Y')
    if isinstance(value,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T[0-9:.]+(?:Z|[+-][0-9:]+)',value):
        return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(LOCAL_TZ).strftime('%d/%m/%Y %H:%M')
    return str(value)


class Document:
    def __init__(self,title,subtitle,confidential=True):
        fonts(); self.title=title; self.subtitle=subtitle; self.confidential=confidential; self.story=[]
        self.styles={
          'body':ParagraphStyle('body',fontName='Peticas',fontSize=9,leading=14,spaceAfter=5,splitLongWords=True),
          'label':ParagraphStyle('label',fontName='Peticas-Bold',fontSize=8,leading=12,textColor=NAVY,spaceBefore=4,spaceAfter=2,keepWithNext=True),
          'heading':ParagraphStyle('heading',fontName='Peticas-Bold',fontSize=13,leading=18,textColor=NAVY,spaceBefore=14,spaceAfter=8,keepWithNext=True),
          'title':ParagraphStyle('title',fontName='Peticas-Bold',fontSize=23,leading=29,textColor=NAVY,spaceAfter=10),
          'appendix':ParagraphStyle('appendix',fontName='Peticas',fontSize=8.5,leading=11.5,spaceAfter=4),
        }
        self.paragraph(title,'title'); self.paragraph(subtitle)

    def paragraph(self,value,style='body'):
        value=escape(printable(value)).replace('\n','<br/>')
        self.story.append(Paragraph(value,self.styles[style]))

    def section(self,title): self.paragraph(title,'heading')

    def field(self,label,value):
        self.paragraph(label,'label'); self.paragraph(value)

    def grid(self,fields):
        cells=[Paragraph('<font name="Peticas-Bold">'+escape(label)+'</font><br/>'+escape(printable(value)),self.styles['body']) for label,value in fields]
        if len(cells)%2: cells.append('')
        table=Table([cells[i:i+2] for i in range(0,len(cells),2)],colWidths=[87*mm,87*mm],hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#eaf4fb')),('VALIGN',(0,0),(-1,-1),'TOP'),
                                   ('LEFTPADDING',(0,0),(-1,-1),3*mm),('RIGHTPADDING',(0,0),(-1,-1),3*mm),
                                   ('TOPPADDING',(0,0),(-1,-1),2*mm),('BOTTOMPADDING',(0,0),(-1,-1),2*mm)]))
        self.story.extend([table,Spacer(1,4*mm)])

    def photo(self,content):
        try:
            from PIL import Image as PILImage
            with PILImage.open(BytesIO(content)) as source:
                source.thumbnail((900,900)); source=source.convert('RGB'); output=BytesIO(); source.save(output,format='JPEG'); output.seek(0)
                image=Image(output); image._restrictSize(75*mm,65*mm); image.hAlign='LEFT'; self.story.extend([image,Spacer(1,4*mm)])
        except Exception:
            self.paragraph('A foto não pôde ser reproduzida. Consulte o anexo no sistema.')

    def signature(self,label):
        self.story.append(KeepTogether([Spacer(1,13*mm),HRFlowable(width='85%',thickness=.5,color=NAVY,hAlign='LEFT'),Paragraph(escape(label),self.styles['body'])]))

    def build(self):
        output=BytesIO()
        def page(canvas,doc):
            canvas.saveState(); width,height=A4
            canvas.setFillColor(NAVY); canvas.rect(0,height-10*mm,width,10*mm,fill=1,stroke=0)
            canvas.drawImage(str(ROOT/'public/assets/peticas.jpg'),18*mm,height-31*mm,width=18*mm,height=18*mm,preserveAspectRatio=True,mask='auto')
            canvas.setFillColor(NAVY); canvas.setFont('Peticas-Bold',12); canvas.drawString(40*mm,height-21*mm,'GATIL PETICAS')
            canvas.setFont('Peticas',8); canvas.drawString(40*mm,height-27*mm,'Cuidado que encontra um lar')
            canvas.setStrokeColor(CYAN); canvas.line(18*mm,18*mm,width-18*mm,18*mm)
            canvas.setFont('Peticas',7); canvas.setFillColor(NAVY)
            canvas.drawString(18*mm,13*mm,'Uso interno - contém dados pessoais' if self.confidential else 'Modelo para revisão e assinatura manuscrita')
            canvas.drawRightString(width-18*mm,13*mm,f'Página {doc.page}'); canvas.restoreState()
        doc=SimpleDocTemplate(output,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=38*mm,bottomMargin=24*mm,
                              title=self.title,author='Gatil Peticas')
        doc.build(self.story,onFirstPage=page,onLaterPages=page)
        return output.getvalue()


def cat_report(db,cat_id,operator):
    cat=next((c for c in repo.cats(db) if c['id']==cat_id),None)
    if not cat: fail(404,'Gato não encontrado.')
    document=Document('Ficha completa do gato',f"{cat['name']} | Cadastro {cat_id} | Gerado em {datetime.now(LOCAL_TZ):%d/%m/%Y %H:%M} por {operator['name']}")
    document.paragraph('Uso interno: esta ficha contém dados de terceiros. Para a pessoa adotante, use o histórico específico da candidatura. Vídeos e arquivos originais são relacionados, mas não incorporados ao PDF.','appendix')
    document.section('Cadastro e resgate')
    if cat.get('photoId'):
        f=db.execute('SELECT bin_conteudo FROM anexos WHERE cod_identificador=%s',(cat['photoId'],)).fetchone()
        if f: document.photo(bytes(f['content']))
    else: document.paragraph('Sem foto própria cadastrada. A imagem ilustrativa do site não representa um registro real do gato.')
    short=('id','name','age','sex','status','color','entryDate')
    document.grid([(CAT_LABELS[key],cat.get(key,'')) for key in short])
    for key,value in cat.items():
        if key not in short: document.field(CAT_LABELS.get(key,key),value)
    document.section('Vacinas e cuidados simplificados')
    care=repo.state(db)
    for v in [v for v in care['vaccines'] if v['cat']==cat_id]:
        document.field(v['label'],f"Prevista: {v['date']}; aplicada: {v['applied'] or 'pendente'}; responsável: {v['person'] or 'não informado'}; próxima: {v['next'] or 'não informada'}; comprovante: {v['proof'] or 'não informado'}; código: {v['id']}; versão: {v['version']}.")
    for m in [m for m in care['meds'] if m['cat']==cat_id]: document.field(m['label'],f"Horário: {m['time']}; realizado: {'sim' if m['done'] else 'não'}.")
    if not any(v['cat']==cat_id for v in care['vaccines']+care['meds']): document.paragraph('Nenhum cuidado simplificado cadastrado.')
    document.section('Prontuário completo')
    locations=repo.application_locations(db); records=[r for r in repo.medical(db) if r['cat_id']==cat_id]
    for r in reversed(records):
        document.section(KINDS[r['kind']]+' - '+r['data']['date'])
        document.field('Identificação e responsável',f"{r['id']} | Tratamento vinculado: {r['treatment_id'] or 'não se aplica'} | {r['responsible']} | Registro: {datetime.fromtimestamp(r['created']/1000,LOCAL_TZ):%d/%m/%Y %H:%M}")
        for key,value in r['data'].items():
            if value!='': document.field(MED_LABELS.get(key,key),value)
        if r['id'] in locations:
            l=locations[r['id']]
            document.field('Localização da aplicação',f"Latitude: {l['latitude']}; longitude: {l['longitude']}; precisão: {l['accuracy']} m; coleta: {datetime.fromtimestamp(l['capturedAt']/1000,LOCAL_TZ):%d/%m/%Y %H:%M}")
    if not records: document.paragraph('Nenhum registro clínico cadastrado.')
    document.section('Candidaturas, adoções e devoluções - uso interno')
    applications=db.execute('SELECT * FROM candidaturas_adocao WHERE cod_gato=%s ORDER BY dat_cadastro',(cat_id,)).fetchall()
    for row in applications:
        a=repo.adoption(db,row); document.section(a['name']+' - '+STAGES[a['stage']])
        document.field('Candidatura',f"{a['id']} | {a['date']} | Versão {a['version']} | Devolução: {'sim' if a['returned'] else 'não'}")
        for k,v in a['answers'].items(): document.field(ANSWER_LABELS.get(k,k),v)
        document.field('Orientações e anotações',a['guidance']+'\n'+a['note']+'\n'+a['rejectionReason'])
        for stage in repo.stage_history(db,row): document.field(STAGES.get(stage['stage'],'Etapa'),stage['date'])
        for event in a['history']: document.field({'followup':'Acompanhamento','return':'Devolução','term':'Termo'}.get(event['kind'],event['kind']),event['date']+' | '+event['notes']+' | Usuário '+event['userId'])
        for message in repo.adoption_messages(db,row['id']): document.field('Mensagem da responsável',message['text'])
    if not applications: document.paragraph('Nenhuma candidatura vinculada a este gato.')
    document.section('Anexos vinculados')
    files=db.execute('SELECT cod_identificador,txt_nome,txt_tipo_midia,txt_tipo_vinculo,dat_cadastro FROM anexos WHERE cod_gato=%s OR cod_candidatura IN (SELECT cod_identificador FROM candidaturas_adocao WHERE cod_gato=%s) ORDER BY dat_cadastro',(cat_id,cat_id)).fetchall()
    for f in files: document.field(f['name'],f"{f['id']} | {f['mime']} | Tipo: { {'cat':'Foto do gato','video':'Vídeo da residência','term':'Termo assinado'}[f['owner_type']]} | {datetime.fromtimestamp(f['created']/1000,LOCAL_TZ):%d/%m/%Y %H:%M}")
    if not files: document.paragraph('Nenhum anexo vinculado.')
    return document.build()


def adoption_term(db,rid,operator):
    row=db.execute('SELECT * FROM candidaturas_adocao WHERE cod_identificador=%s',(rid,)).fetchone()
    if not row: fail(404,'Candidatura não encontrada.')
    if row['stage'] not in (3,4) or row['returned']: fail(400,'O termo exige candidatura aprovada, gato vinculado e adoção sem devolução.')
    cat=next((c for c in repo.cats(db) if c['id']==row['cat_id']),None)
    if not cat: fail(400,'Vincule um gato antes de gerar o termo.')
    a=repo.adoption(db,row); cfg=privacy.config(db); accepted=privacy.latest(db,rid)
    model=json.loads((ROOT/'backend/templates/termo_adocao.json').read_text(encoding='utf-8'))
    d=Document(model['title'],f"MODELO PARA REVISÃO | Versão {model['version']} | Candidatura {rid}",False)
    d.section('Identificação das partes')
    d.field('Gatil / responsável pelo tratamento',cfg['controller']+' | '+(cfg['identifier'] or 'CPF/CNPJ: ____________________'))
    d.field('Endereço e canal de privacidade',(cfg['address'] or 'Endereço: ____________________')+' | '+(cfg['contact'] or 'Contato: ____________________'))
    d.grid([(ANSWER_LABELS[key],a['answers'].get(key,'')) for key in ('name','cpf','age','email','phone')])
    d.field('Endereço da pessoa adotante',a['answers'].get('address',''))
    d.section('Identificação do gato')
    d.grid([(CAT_LABELS[key],cat.get(key,'')) for key in ('id','name','age','sex','color','entryDate')])
    d.field('Personalidade',cat.get('personality',''))
    for clause in model['clauses']: d.section(clause['title']); d.paragraph(clause['text'])
    d.section('Ciência sobre o tratamento necessário de dados')
    d.paragraph('Recebi informações sobre o uso de meus dados para analisar, formalizar e acompanhar a adoção solicitada, o acesso restrito e os canais para exercer meus direitos. Esta declaração não autoriza usos genéricos, publicidade nem tratamento de dados de terceiros. O aviso de privacidade vigente integra a documentação da candidatura.')
    d.field('Registro eletrônico do aviso',f"Versão: {accepted['version']} | Data: {datetime.fromtimestamp(accepted['date']/1000,LOCAL_TZ):%d/%m/%Y %H:%M}" if accepted else 'Candidatura anterior ao registro eletrônico de ciência. Conferir e colher ciência presencialmente.')
    if accepted and accepted['version']!=privacy.notice(db)['version']:
        d.paragraph('A ciência eletrônica refere-se a uma versão anterior do aviso. Apresente a versão atual e confira a ciência presencial antes da assinatura.')
    d.section('Consentimento opcional e destacado - vídeo da residência')
    d.paragraph('Autorizo o uso do vídeo que eu enviar exclusivamente para avaliar a proteção do lar, com acesso restrito à responsável. Posso recusar ou revogar esta autorização gratuitamente, sem impedir a candidatura, combinando uma visita ou alternativa adequada. Não autorizo publicidade nem uso de imagens de terceiros.')
    d.paragraph(('( X ) AUTORIZO     (   ) NÃO AUTORIZO' if accepted and accepted['homeVideoConsent'] else '(   ) AUTORIZO     ( X ) NÃO AUTORIZO')+' - escolha registrada no site; conferir antes de assinar.')
    signatures_start=len(d.story)
    d.signature('Assinatura específica da pessoa adotante sobre a escolha do vídeo')
    d.field('Local e data de entrega','____________________________________, ____ / ____ / ________')
    d.signature('Pessoa adotante: '+a['name']); d.signature('Responsável pelo gatil: '+operator['name'])
    d.paragraph('Entregar uma via a cada parte. Após assinatura, digitalizar e anexar à candidatura. Modelo sujeito à revisão da responsável e à adequação jurídica ao funcionamento real do gatil.')
    signature_group=d.story[signatures_start:]; d.story[signatures_start:]=[KeepTogether(signature_group)]
    d.story.append(PageBreak())
    d.section('Anexo - aviso apresentado na ciência eletrônica')
    d.paragraph(privacy.acknowledged_text(db,rid) or privacy.notice(db)['snapshot'],'appendix')
    return d.build()
