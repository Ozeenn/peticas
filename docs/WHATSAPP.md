# WhatsApp

O gateway está em `backend/gateway.py`; `backend/whatsapp.py` monta as chamadas à Meta e valida os avisos recebidos. A fila e a deduplicação usam PostgreSQL, junto com a API.

No `.env` da raiz, defina `WHATSAPP_WEBHOOK_URL=http://gateway:8001/messages`, `WHATSAPP_WEBHOOK_TOKEN` com pelo menos 32 caracteres ASCII e os aliases `owner` e `volunteers`. Os telefones ficam em `WHATSAPP_OWNER_NUMBERS` e `WHATSAPP_VOLUNTEERS_NUMBERS`, separados por vírgulas e escritos somente com dígitos, incluindo país e DDD.

Execute `docker compose --profile whatsapp up --build -d`. O gateway só é exposto na rede interna do Compose. A rotina `jobs` processa a fila a cada minuto. Sem configuração do gateway, os avisos continuam pendentes.

Comece com `WHATSAPP_DRY_RUN=true`, que simula o envio. Para enviar realmente, defina `WHATSAPP_DRY_RUN=false`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_GRAPH_VERSION` conforme a conta e a versão da Graph API utilizada.

`WHATSAPP_MESSAGE_MODE=text` usa o texto do aviso. `template` usa modelos aprovados, configurados em `WHATSAPP_OWNER_TEMPLATE` e `WHATSAPP_VOLUNTEERS_TEMPLATE`, com idioma em `WHATSAPP_TEMPLATE_LANGUAGE` e um parâmetro de corpo em `WHATSAPP_TEMPLATE_BODY_VALUE`. O parâmetro deve ter até 1024 caracteres, sem quebras de linha. Confirme as regras de envio e os modelos disponíveis na sua conta Meta.

Uma mensagem só sai da fila depois de receber o mesmo ID, `accepted=true` e `simulated=false`. Simulação e respostas incompletas não confirmam envio.

Cada destinatário tem um resultado persistido em `entregas_whatsapp`. Uma resposta explícita de rejeição permite nova tentativa. Timeout, erro de servidor e resposta sem identificação mantêm o resultado incerto e bloqueiam repetição automática daquele destinatário; confira o painel da Meta antes de liberar nova tentativa.

Os testes do gateway fazem parte de `backend/tests/`, usam PostgreSQL e simulam a Meta. Os avisos de candidatura não contêm CPF nem respostas da entrevista. Não publique tokens ou telefones em arquivos versionados.
