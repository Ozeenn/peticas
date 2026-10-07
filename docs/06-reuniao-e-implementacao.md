# Alterações após o levantamento com a dona do gatil

Registro de implementação local em 7 de outubro de 2026. Este guia técnico complementa os guias anteriores; os trechos antigos sobre estoque e permissões fixas descrevem a versão anterior.

## Escopo aplicado

- Estoque, compras e seus avisos deixam de aparecer na interface. As antigas rotas retornam HTTP 410 após autenticação. Tabelas e registros existentes permanecem no banco.
- O cadastro de gatos passa a incluir entrada, cor, local, responsável e relatório do resgate. Campos antigos não são preenchidos com informações inventadas; devem ser completados pela responsável quando editar o cadastro.
- A responsável cadastra diretamente. Voluntários com permissão enviam propostas, que só entram na lista de gatos após aprovação da Cris. A reprovação exige um motivo. Decisões concorrentes são protegidas pela versão do registro.
- Fotos são enviadas de verdade. O cadastro pode ser publicado somente como disponível ou em tratamento; reserva e adoção seguem a candidatura.
- Somente a responsável cadastra voluntários. CPF é validado. Uma ficha pode existir sem acesso; para ativá-la, a responsável define uma senha inicial e escolhe as permissões. As contas anteriores conservam consulta/registro de prontuário e consulta limitada de candidaturas até revisão das permissões.
- O formulário de adoção mantém as etapas existentes e acrescenta e-mail. O vídeo da residência é enviado pelo link individual. A responsável pode anexar o termo assinado em PDF; o sistema não assina nem gera um contrato jurídico.
- Recusa exige motivo. Acompanhamento e devolução são registros adicionais. A devolução torna o gato disponível e preserva a candidatura concluída, seus arquivos e histórico.
- O adotante pode baixar um histórico legível em HTML, que pode abrir e imprimir. O acesso é pelo link individual, após a conclusão da adoção. Registros clínicos novos, posteriores à conclusão, não são incluídos no histórico daquela adoção.
- A área de doações informa os itens aceitos e a restrição de ração. A responsável configura a chave Pix e os links das campanhas em **Doações e avisos**. Nenhuma chave foi inventada.

## Permissões

`cats.submit`, `cats.photos`, `cats.status`, `medical.read`, `medical.write` e `adoptions.lookup` são conferidas no servidor. A responsável tem todas. Mudanças de acesso e de permissões encerram as sessões do voluntário. `cats.status` permite alternar disponível/em tratamento; reserva, adoção e devolução dependem da responsável.

## Medicação

Novos tratamentos recebem intervalo em horas, horário inicial e fim previsto conforme a prescrição informada pela equipe. O checklist calcula as doses no período escolhido, até sete dias, e identifica quem registrou a aplicação e seu horário real. O horário previsto fica separado do horário aplicado. Um índice único impede duas aplicações para a mesma dose prevista.

Tratamentos anteriores sem intervalo estruturado continuam no prontuário e são sinalizados como não programados. O sistema não deduz horários de um texto livre nem recomenda medicamentos ou doses.

## Arquivos

JPEG/PNG para fotos, MP4/WebM para vídeo e PDF para o termo; até 8 MB por arquivo e dez arquivos de cada tipo por registro. O servidor confere tamanho, formato e acesso. Fotos atuais de gatos disponíveis podem ser públicas; arquivos de adoção exigem a responsável ou o token individual.

Na hospedagem, `.openai/hosting.json` declara `r2: "BUCKET"`; os arquivos vão para R2 e os metadados para D1. Sem o armazenamento configurado, uploads hospedados retornam uma mensagem de indisponibilidade. No servidor local e nos testes, os arquivos ficam em SQLite. Vídeos maiores precisam ser reduzidos antes de envio.

## WhatsApp: configuração ainda necessária

A implementação prepara uma fila persistente para novas candidaturas e relatórios de fim de semana. Não há envio real enquanto o serviço não estiver configurado. A tela da responsável mostra essa condição e a situação dos avisos.

O adaptador usa um gateway HTTPS, a ser contratado/configurado pelo gatil, que efetivamente envia mensagens para os destinatários acordados. Não é uma integração pronta com a API da Meta e não pressupõe que qualquer serviço suporte grupos.

Variáveis de ambiente, mantidas fora do código:

- `WHATSAPP_WEBHOOK_URL`: endpoint HTTPS do gateway.
- `WHATSAPP_WEBHOOK_TOKEN`: segredo usado no cabeçalho `Authorization: Bearer`.
- `WHATSAPP_OWNER_TARGET`: destinatário da responsável.
- `WHATSAPP_VOLUNTEERS_TARGET`: destino de voluntários suportado pelo gateway, incluindo grupo somente se o serviço permitir.

Contrato: `POST` JSON `{ "id": "identificador", "target": "destinatário", "text": "mensagem" }`, com cabeçalho `Idempotency-Key`. O gateway deve garantir idempotência por esse identificador e responder 2xx somente após aceitar o envio de modo durável. O aviso de candidatura não contém CPF, endereço nem respostas pessoais.

Falhas recebem até dez tentativas com espera crescente; a fila registra a falha. Ausência de configuração mantém os avisos pendentes. `scheduled()` prepara o relatório às sextas-feiras, usando o horário de São Paulo, e processa a fila. A hospedagem precisa de um agendamento que invoque esse handler regularmente; ele **não foi configurado nem publicado neste trabalho**. O servidor local verifica a fila a cada minuto enquanto estiver ligado.

Antes de ativar: definir gateway, destinatários, credenciais e agendamento, conferir suporte ao destino dos voluntários, testar entrega real e avaliar custo mensal. R$ 150 é uma referência de disposição de pagamento, sem custo garantido.

## Arquivos e validação

- `public/requirements.js`: camada final dos fluxos, carregada após os quatro scripts anteriores; inicia `boot()` uma única vez.
- `server/workflows.mjs`: permissões, revisão de gatos, devolução, doações, programação de medicação e fila de mensagens.
- `server/worker.mjs`: autenticação, candidaturas, arquivos, validações e pontos de integração.
- Migração `0003_sour_mantis.sql`: acrescenta arquivos, fila e identificação da dose prevista, preservando as tabelas antigas.
- Testes integrados com SQLite temporário cobrem autenticação, autorização, aprovação, devolução, privacidade de arquivos, fila e aplicações duplicadas. Um teste de carregamento dos scripts verifica a navegação e os formulários finais; não substitui conferência visual no navegador.

Build e testes são locais. O banco de produção e os documentos acadêmicos aprovados não foram alterados.
