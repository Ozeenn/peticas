# Integração do WhatsApp com Python

O backend JavaScript mantém a fila `message_jobs`. O serviço FastAPI em `services/whatsapp/` recebe os avisos e chama a WhatsApp Cloud API da Meta. Ele funciona em um processo separado; o pacote do Worker publicado pelo Sites não inclui nem executa Python.

Fluxo: candidatura ou relatório semanal → fila do Peticas → `POST /messages` no gateway → Meta. O agendador local processa a fila a cada minuto. Na produção, é necessário configurar a invocação periódica do método `scheduled` do Worker; somente hospedar o gateway não ativa o agendamento do site.

## Executar no Windows

Na raiz do projeto, com Python 3.12 ou superior:

```powershell
python -m venv services/whatsapp/.venv
services/whatsapp/.venv/Scripts/python.exe -m pip install -r services/whatsapp/requirements.txt
Copy-Item services/whatsapp/.env.example services/whatsapp/.env
```

Edite `services/whatsapp/.env`. Gere um segredo com `python -c "import secrets; print(secrets.token_urlsafe(32))"` e coloque-o em `PETICAS_GATEWAY_TOKEN`. Informe telefones autorizados com país e DDD, somente dígitos, em `WHATSAPP_OWNER_NUMBERS` e/ou `WHATSAPP_VOLUNTEERS_NUMBERS`. Não use números de exemplo em envios reais.

Mantenha `WHATSAPP_DRY_RUN=true` para o primeiro teste. Abra um terminal na raiz e execute:

```powershell
services/whatsapp/.venv/Scripts/python.exe -m services.whatsapp.run
```

Em outro terminal, edite o `.env` do backend (sem substituir as demais configurações):

```dotenv
WHATSAPP_WEBHOOK_URL=http://127.0.0.1:8001/messages
WHATSAPP_WEBHOOK_TOKEN=mesmo-segredo-do-gateway
WHATSAPP_OWNER_TARGET=owner
WHATSAPP_VOLUNTEERS_TARGET=volunteers
```

Execute `pnpm dev` ou reinicie o servidor existente para carregar a configuração. HTTP é aceito somente em loopback quando o servidor local fornece `LOCAL_FILE_STORAGE=true`; na produção o endereço precisa ser HTTPS.

`GET http://127.0.0.1:8001/health` informa se o processo está funcionando e se está em simulação. Um teste manual em PowerShell:

```powershell
$gatewayToken = Read-Host 'Segredo do gateway' -AsSecureString
$gatewayCredential = [System.Net.NetworkCredential]::new('', $gatewayToken)
$gatewayHeaders = @{ Authorization = 'Bearer ' + $gatewayCredential.Password; 'Idempotency-Key' = 'manual:teste-001' }
$gatewayBody = @{ id = 'manual:teste-001'; target = 'owner'; text = 'Teste de integração Peticas' } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8001/messages -Method Post -ContentType 'application/json' -Headers $gatewayHeaders -Body $gatewayBody
```

Na simulação, a resposta contém `accepted=false` e `simulated=true`. Nenhuma chamada é feita à Meta e nenhuma chave é consumida no gateway. **A fila do backend também permanece pendente**: simulação não confirma envio. O backend registra a tentativa e mantém a política existente de no máximo 10 tentativas; prefira o teste manual acima antes de apontar uma fila com avisos reais para um gateway em simulação.

## Ativar os envios reais

Configure uma conta WhatsApp Business e um telefone na Cloud API, token de acesso com permissão de envio, ID do telefone e versão ativa da Graph API. Coloque os valores somente no `.env` do gateway ou no gerenciador de segredos da hospedagem. O token da Meta nunca vai para o navegador ou para o `.env` do backend JavaScript.

O gateway oferece duas modalidades:

| Modo | Conteúdo enviado | Configuração |
| --- | --- | --- |
| `template` (padrão) | Aviso genérico com link para abrir o sistema; o relatório completo permanece no Peticas | Modelos aprovados em `WHATSAPP_OWNER_TEMPLATE` e `WHATSAPP_VOLUNTEERS_TEMPLATE`, idioma e `WHATSAPP_TEMPLATE_BODY_VALUE` |
| `text` | Texto integral do aviso, até 4096 caracteres, sem truncar | `WHATSAPP_MESSAGE_MODE=text`; o envio precisa ser permitido pela janela de atendimento da Meta |

Para o modo template, cadastre e obtenha aprovação de um modelo com **um único parâmetro de texto no corpo**, sem cabeçalhos ou botões parametrizados. Exemplo de conteúdo para aprovação: “Há uma atualização no Peticas. Consulte o sistema: {{1}}”. Configure o nome aprovado, o idioma exato e o link do site como valor do parâmetro. Pode usar modelos diferentes para responsável e voluntários. O serviço não cria nem aprova modelos. Essa modalidade envia o aviso e o link, não os detalhes da candidatura nem as doses do relatório semanal.

Depois da configuração, altere `WHATSAPP_DRY_RUN=false` e reinicie o gateway. Envie um teste para um destinatário que autorizou as notificações. O retorno `accepted=true` significa que a Meta aceitou o pedido; **não comprova entrega ou leitura no telefone**. Webhooks de confirmação de entrega/leitura não fazem parte desta implementação.

`owner` e `volunteers` são aliases internos. O gateway resolve cada alias para uma lista de telefones individuais, com até 20 números. Esta implementação não envia para links de convite ou grupos de WhatsApp. Em um lote, os números já aceitos não são reenviados se outro número falhar.

## Hospedagem e persistência

Execute o gateway em uma hospedagem Python ou contêiner com HTTPS na entrada. Exemplo de criação da imagem:

```powershell
docker build -t peticas-whatsapp services/whatsapp
docker run --rm --env-file services/whatsapp/.env -p 127.0.0.1:8001:8001 -v peticas-whatsapp-data:/app/data peticas-whatsapp
```

Use um proxy HTTPS para acesso pelo Worker. O contêiner roda como usuário sem privilégios. O banco `/app/data/whatsapp-gateway.sqlite` precisa de volume persistente. Sem persistência, reiniciar ou republicar o serviço perde o registro dos envios e pode causar duplicações. Use uma instância do serviço e armazenamento local persistente; não compartilhe o SQLite em volume de rede entre réplicas.

No backend publicado, configure os quatro valores `WHATSAPP_*` do exemplo, usando `https://seu-gateway/messages`. Configure o agendamento do Worker no provedor. As credenciais, hospedagem do gateway e configuração do agendador continuam pendentes até serem fornecidas/aplicadas; criar os arquivos não publica essa integração.

## Falhas e prevenção de duplicação

O gateway exige token compartilhado, `Idempotency-Key` igual ao `id` e destinos predefinidos. Ele limita o corpo da requisição a 64 KB. O SQLite registra hashes do conteúdo e dos destinatários, estados e IDs retornados pela Meta; não grava o texto dos avisos ou o telefone em claro. Trate esse banco e os IDs como dados internos e mantenha backups.

Repetir um ID já aceito retorna a confirmação gravada. Reusar o ID com conteúdo, telefone remetente, destinatários ou modelo alterados retorna 409. Uma resposta explícita de rejeição 4xx permite nova tentativa; destinatários aceitos em um lote são preservados.

Timeout, falha de transporte, resposta de servidor 5xx ou sucesso sem ID ficam como `uncertain`. Se o processo parar durante a chamada, o registro permanece `sending`. As tentativas seguintes ficam bloqueadas com 409: repetir cegamente poderia enviar duas vezes. Não existe uma garantia absoluta de envio único entre o SQLite e a API externa.

Para recuperar um envio incerto, pare o gateway, faça backup do banco, localize `deliveries` pelo `job_id` e confira no painel/registros da Meta cada destinatário. A chave `recipient_hash` é SHA-256 do telefone completo, somente dígitos. Se confirmar a aceitação, atualize somente essa linha para `state='accepted'` e informe o `meta_id` real. Se confirmar que não foi enviado, atualize somente essa linha para `state='rejected'`. Nunca libere lotes inteiros sem conferir. Se o job do Peticas esgotou as 10 tentativas, reative somente o ID correspondente na fila, ajustando `attempts=0` e `next_attempt=0`, após a reconciliação e backup. Esse procedimento é administrativo e não é feito automaticamente pelo serviço.

## Verificação

```powershell
services/whatsapp/.venv/Scripts/python.exe -m unittest services.whatsapp.test_gateway -v
pnpm test
pnpm build
```

Os testes Python usam uma Meta simulada e bancos temporários: autenticação, limites, payload, templates, simulação, persistência após reinício, lote parcial e falhas incertas. Os testes JavaScript verificam o contrato do gateway e preservação da fila em simulações ou respostas inválidas. Nenhum teste envia mensagens reais.

Referências: [WhatsApp Cloud API — coleção oficial da Meta](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api), [modelos — SDK da Meta](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/template/), [execução do FastAPI](https://fastapi.tiangolo.com/deployment/manually/).
