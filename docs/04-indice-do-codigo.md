# Índice do código por arquivo e função

[Voltar ao guia](README.md) · [Interface](01-interface.md) · [Servidor](02-servidor-e-dados.md)

Gerado a partir da fonte local por `node docs/gerar-indice.mjs`. Os links abrem os arquivos; a coluna Linha indica onde procurar na versão indexada. Uma função repetida é intencionalmente listada em cada definição/substituição. Consulte a ordem de scripts antes de decidir qual implementação editar.

A extração é textual: lista funções nomeadas, atribuições de funções e helpers arrow reconhecidos. Callbacks anônimos, métodos de objetos, constantes de dados e regras CSS são explicados nos capítulos, não tratados como funções independentes aqui. O gerador não lê `.env`, o banco ou credenciais.

## public/app.js

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`$`](../public/app.js) | 1 | Função arrow | Atalho para document.querySelector. |
| [`icon`](../public/app.js) | 3 | Função arrow | Monta o SVG de um ícone cadastrado em icons. |
| [`ageInMonths`](../public/app.js) | 12 | Declaração | Extrai anos/meses de uma idade textual para aplicar filtros. |
| [`matchesAge`](../public/app.js) | 13 | Declaração | Compara a idade do gato com a faixa selecionada. |
| [`esc`](../public/app.js) | 14 | Função arrow | Escapa caracteres para interpolação em HTML. |
| [`catBy`](../public/app.js) | 15 | Função arrow | Encontra gato por ID ou fornece fallback visual. |
| [`img`](../public/app.js) | 16 | Função arrow | Gera imagem a partir do índice da foto ilustrativa. |
| [`brand`](../public/app.js) | 17 | Função arrow | Monta a logo e o nome do projeto. |
| [`toast`](../public/app.js) | 18 | Declaração | Mostra feedback temporário. |
| [`go`](../public/app.js) | 19 | Declaração | Muda tela/hash e limpa filtros. |
| [`badge`](../public/app.js) | 20 | Declaração | Monta etiqueta visual de status. |
| [`render`](../public/app.js) | 21 | Declaração | Escolhe e insere a tela; veja a cadeia de substituições no guia. |
| [`adminShell`](../public/app.js) | 22 | Declaração | Monta ou estende o layout interno e os menus. |
| [`heading`](../public/app.js) | 23 | Declaração | Cria cabeçalho de uma seção com título, descrição e ação. |
| [`overview`](../public/app.js) | 24 | Declaração | Monta o painel geral com indicadores e resumos legados. |
| [`careRow`](../public/app.js) | 25 | Declaração | Monta linha de cuidado/vacina nos resumos antigos. |
| [`medRow`](../public/app.js) | 26 | Declaração | Monta linha de medicamento legado com controle de marcação. |
| [`catCard`](../public/app.js) | 27 | Declaração | Monta um cartão de gato e sua ação. |
| [`filters`](../public/app.js) | 28 | Declaração | Gera controles de busca, sexo/status e faixa etária. |
| [`filteredCats`](../public/app.js) | 29 | Declaração | Filtra gatos conforme tela e seleções. |
| [`grid`](../public/app.js) | 30 | Declaração | Monta cartões ou estado vazio. |
| [`bindFilters`](../public/app.js) | 31 | Declaração | Reconecta eventos dos filtros após renderizar. |
| [`catsPage`](../public/app.js) | 32 | Declaração | Monta a tela interna de gatos. |
| [`healthPage`](../public/app.js) | 33 | Declaração | Monta cuidados; a versão comunitária apresenta o novo prontuário. |
| [`applicationsPage`](../public/app.js) | 34 | Declaração | Monta cartões administrativos de candidaturas. |
| [`publicShell`](../public/app.js) | 35 | Declaração | Monta cabeçalho, conteúdo e rodapé públicos. |
| [`publicPage`](../public/app.js) | 36 | Declaração | Monta ou amplia a página pública. |
| [`showModal`](../public/app.js) | 37 | Declaração | Insere título/corpo e abre o diálogo nativo. |
| [`closeModal`](../public/app.js) | 38 | Declaração | Fecha o diálogo. |
| [`openCat`](../public/app.js) | 39 | Declaração | Abre detalhes do gato; extensão acrescenta acesso ao prontuário. |
| [`newCat`](../public/app.js) | 40 | Declaração | Abre cadastro de novo gato. |
| [`editCat`](../public/app.js) | 41 | Declaração | Monta formulário de cadastro/edição. |
| [`saveCat`](../public/app.js) | 42 | Declaração | Salva gato; versão final persiste pela API. |
| [`openVaccine`](../public/app.js) | 43 | Declaração | Mostra aplicação existente ou formulário de vacina legado. |
| [`saveVaccine`](../public/app.js) | 44 | Declaração | Registra vacina legada; persiste nome do comprovante, sem upload. |
| [`toggleMed`](../public/app.js) | 45 | Declaração | Alterna marcação de medicamento legado. |
| [`newCare`](../public/app.js) | 46 | Declaração | Abre formulário de cuidado antigo. |
| [`saveCare`](../public/app.js) | 47 | Declaração | Salva cuidado nos arrays legados. |
| [`openApplication`](../public/app.js) | 48 | Declaração | Exibe entrevista e ações da dona; extensão acrescenta CPF. |
| [`saveGuidance`](../public/app.js) | 49 | Declaração | Salva orientação privada de acompanhamento. |
| [`decideApplication`](../public/app.js) | 50 | Declaração | Envia decisão/etapa e escolha do gato. |
| [`questionLabel`](../public/app.js) | 52 | Declaração | Busca rótulo de resposta nas definições de perguntas. |
| [`startForm`](../public/app.js) | 53 | Declaração | Inicia entrevista e limpa seu estado temporário. |
| [`drawForm`](../public/app.js) | 54 | Declaração | Monta uma etapa do formulário de adoção. |
| [`backForm`](../public/app.js) | 55 | Declaração | Guarda campos atuais e retorna à etapa anterior. |
| [`nextForm`](../public/app.js) | 56 | Declaração | Avança ou envia entrevista; versão final usa API. |
| [`trackingPage`](../public/app.js) | 57 | Declaração | Monta acompanhamento por token ou consulta pública por CPF. |

## public/management.js

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`quantity`](../public/management.js) | 5 | Função arrow | Converte milésimos para número apresentado em português. |
| [`localDate`](../public/management.js) | 6 | Função arrow | Produz data civil de São Paulo para formulários. |
| [`dateLabel`](../public/management.js) | 7 | Função arrow | Formata data/timestamp para exibição. |
| [`activeAccount`](../public/management.js) | 8 | Função arrow | Verifica se o estado local tem admin ou staff. |
| [`lowItems`](../public/management.js) | 9 | Função arrow | Seleciona itens com saldo menor ou igual ao mínimo. |
| [`unread`](../public/management.js) | 10 | Função arrow | Seleciona avisos não resolvidos e não lidos. |
| [`api`](../public/management.js) | 11 | Declaração | Cliente fetch no frontend; roteador HTTP no Worker. |
| [`formError`](../public/management.js) | 12 | Declaração | Apresenta erro no formulário ou em toast. |
| [`submit`](../public/management.js) | 13 | Declaração | Coleta FormData, controla botão e trata falhas de envio. |
| [`loadData`](../public/management.js) | 14 | Declaração | Carrega dados iniciais; extensões acrescentam saúde e guia. |
| [`boot`](../public/management.js) | 15 | Declaração | Obtém sessão, carrega dados e interpreta a URL inicial. |
| [`go`](../public/management.js) | 16 | Atribuição de função | Muda tela/hash e limpa filtros. |
| [`render`](../public/management.js) | 17 | Atribuição de função | Escolhe e insere a tela; veja a cadeia de substituições no guia. |
| [`adminShell`](../public/management.js) | 18 | Atribuição de função | Monta ou estende o layout interno e os menus. |
| [`authPage`](../public/management.js) | 20 | Declaração | Monta login/primeiro cadastro ou estado de acesso pendente/bloqueado. |
| [`authSubmit`](../public/management.js) | 21 | Declaração | Envia login/cadastro inicial e carrega a conta. |
| [`logout`](../public/management.js) | 22 | Declaração | Encerra sessão e retorna ao público. |
| [`accountPage`](../public/management.js) | 23 | Declaração | Monta conta/senha e, na extensão, recuperação. |
| [`changePassword`](../public/management.js) | 24 | Declaração | Envia troca de senha autenticada. |
| [`loadTeam`](../public/management.js) | 25 | Declaração | Busca lista de usuários e abre equipe. |
| [`teamPage`](../public/management.js) | 26 | Declaração | Monta equipe; extensão adiciona cadastro e acesso a fichas. |
| [`setRole`](../public/management.js) | 27 | Declaração | Altera perfil e recarrega equipe. |
| [`stockPage`](../public/management.js) | 28 | Declaração | Monta indicadores, abas e conteúdo do estoque. |
| [`stockSituation`](../public/management.js) | 29 | Declaração | Classifica saldo como falta, baixo ou regular. |
| [`itemsTable`](../public/management.js) | 30 | Declaração | Monta tabela de itens filtrados. |
| [`bindStock`](../public/management.js) | 31 | Declaração | Reconecta filtros específicos do estoque. |
| [`itemForm`](../public/management.js) | 32 | Declaração | Monta cadastro/edição do item. |
| [`refreshStock`](../public/management.js) | 33 | Declaração | Relê inventário e redesenha a página. |
| [`saveItem`](../public/management.js) | 34 | Declaração | Cria ou atualiza cadastro de item pela API. |
| [`movementForm`](../public/management.js) | 35 | Declaração | Monta movimentação com ID idempotente. |
| [`saveMovement`](../public/management.js) | 36 | Declaração | Envia movimentação com versão atual do item. |
| [`purchaseForm`](../public/management.js) | 37 | Declaração | Monta agendamento de compra. |
| [`savePurchase`](../public/management.js) | 38 | Declaração | Envia nova compra e abre sua aba. |
| [`purchasesPage`](../public/management.js) | 39 | Declaração | Monta agenda e ações de compras. |
| [`confirmPurchase`](../public/management.js) | 40 | Declaração | Pede confirmação visual de recebimento. |
| [`cancelPurchase`](../public/management.js) | 41 | Declaração | Pede confirmação visual de cancelamento. |
| [`finishPurchase`](../public/management.js) | 42 | Declaração | Envia recebimento/cancelamento e atualiza estoque. |
| [`alertsPage`](../public/management.js) | 43 | Declaração | Monta lista de notificações. |
| [`readNotification`](../public/management.js) | 44 | Declaração | Registra leitura de aviso da conta atual. |
| [`historyPage`](../public/management.js) | 45 | Declaração | Monta os últimos movimentos retornados. |
| [`persistState`](../public/management.js) | 49 | Declaração | Envia snapshot do gatil com versão e atualiza arrays locais. |
| [`saveCat`](../public/management.js) | 50 | Atribuição de função | Salva gato; versão final persiste pela API. |
| [`saveVaccine`](../public/management.js) | 51 | Atribuição de função | Registra vacina legada; persiste nome do comprovante, sem upload. |
| [`toggleMed`](../public/management.js) | 52 | Atribuição de função | Alterna marcação de medicamento legado. |
| [`saveCare`](../public/management.js) | 53 | Atribuição de função | Salva cuidado nos arrays legados. |
| [`saveGuidance`](../public/management.js) | 54 | Atribuição de função | Salva orientação privada de acompanhamento. |
| [`decideApplication`](../public/management.js) | 55 | Atribuição de função | Envia decisão/etapa e escolha do gato. |
| [`drawForm`](../public/management.js) | 56 | Atribuição de função | Monta uma etapa do formulário de adoção. |
| [`nextForm`](../public/management.js) | 57 | Atribuição de função | Avança ou envia entrevista; versão final usa API. |
| [`loadTracking`](../public/management.js) | 58 | Declaração | Obtém candidatura pelo token e abre acompanhamento. |
| [`trackingPage`](../public/management.js) | 60 | Atribuição de função | Monta acompanhamento por token ou consulta pública por CPF. |
| [`adminShell`](../public/management.js) | 63 | Atribuição de função | Monta ou estende o layout interno e os menus. |
| [`render`](../public/management.js) | 65 | Atribuição de função | Escolhe e insere a tela; veja a cadeia de substituições no guia. |
| [`authPage`](../public/management.js) | 67 | Atribuição de função | Monta login/primeiro cadastro ou estado de acesso pendente/bloqueado. |
| [`accountPage`](../public/management.js) | 69 | Atribuição de função | Monta conta/senha e, na extensão, recuperação. |
| [`showRecoveryCode`](../public/management.js) | 70 | Declaração | Exibe código de recuperação retornado uma vez. |
| [`generateRecovery`](../public/management.js) | 71 | Declaração | Solicita novo código usando senha atual. |
| [`resetPassword`](../public/management.js) | 72 | Declaração | Valida confirmação local e envia redefinição por código. |

## public/community.js

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`contactLink`](../public/community.js) | 2 | Função arrow | Cria link WhatsApp com mensagem codificada. |
| [`publicPage`](../public/community.js) | 4 | Atribuição de função | Monta ou amplia a página pública. |
| [`drawForm`](../public/community.js) | 15 | Atribuição de função | Monta uma etapa do formulário de adoção. |
| [`authPage`](../public/community.js) | 18 | Atribuição de função | Monta login/primeiro cadastro ou estado de acesso pendente/bloqueado. |
| [`render`](../public/community.js) | 20 | Atribuição de função | Escolhe e insere a tela; veja a cadeia de substituições no guia. |
| [`adminShell`](../public/community.js) | 22 | Atribuição de função | Monta ou estende o layout interno e os menus. |
| [`volunteerGuide`](../public/community.js) | 23 | Declaração | Monta orientações gerais e, na extensão, dados internos carregados. |
| [`teamPage`](../public/community.js) | 27 | Atribuição de função | Monta equipe; extensão adiciona cadastro e acesso a fichas. |
| [`newVolunteer`](../public/community.js) | 28 | Declaração | Monta ficha/cadastro exclusivamente oferecido à dona. |
| [`createVolunteer`](../public/community.js) | 29 | Declaração | Envia novo usuário/ficha e atualiza equipe. |
| [`volunteerProfile`](../public/community.js) | 30 | Declaração | Busca ficha restrita e abre detalhes. |
| [`restrictStock`](../public/community.js) | 32 | Declaração | Remove botões de cadastro/compras da string HTML para não-admin. |
| [`stockPage`](../public/community.js) | 34 | Função arrow | Monta indicadores, abas e conteúdo do estoque. |
| [`itemsTable`](../public/community.js) | 34 | Função arrow | Monta tabela de itens filtrados. |
| [`purchasesPage`](../public/community.js) | 34 | Função arrow | Monta agenda e ações de compras. |
| [`loadData`](../public/community.js) | 38 | Atribuição de função | Carrega dados iniciais; extensões acrescentam saúde e guia. |
| [`healthPage`](../public/community.js) | 40 | Atribuição de função | Monta cuidados; a versão comunitária apresenta o novo prontuário. |
| [`newTreatment`](../public/community.js) | 41 | Declaração | Abre medicalForm com tipo treatment. |
| [`medicalForm`](../public/community.js) | 42 | Declaração | Monta formulário de tratamento, aplicação, evolução ou encerramento. |
| [`saveMedical`](../public/community.js) | 43 | Declaração | Converte catId, envia evento e recarrega prontuário. |
| [`loadData`](../public/community.js) | 46 | Atribuição de função | Carrega dados iniciais; extensões acrescentam saúde e guia. |
| [`volunteerGuide`](../public/community.js) | 48 | Atribuição de função | Monta orientações gerais e, na extensão, dados internos carregados. |
| [`openCat`](../public/community.js) | 50 | Atribuição de função | Abre detalhes do gato; extensão acrescenta acesso ao prontuário. |

## public/interview-lookup.js

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`adminShell`](../public/interview-lookup.js) | 2 | Atribuição de função | Monta ou estende o layout interno e os menus. |
| [`render`](../public/interview-lookup.js) | 4 | Atribuição de função | Escolhe e insere a tela; veja a cadeia de substituições no guia. |
| [`lookupInterview`](../public/interview-lookup.js) | 5 | Declaração | Consulta interna por CPF, apenas status/data. |
| [`openApplication`](../public/interview-lookup.js) | 7 | Atribuição de função | Exibe entrevista e ações da dona; extensão acrescenta CPF. |
| [`linkApplicationCPF`](../public/interview-lookup.js) | 8 | Declaração | Vincula CPF em candidatura com proteção de versão. |
| [`trackingPage`](../public/interview-lookup.js) | 10 | Atribuição de função | Monta acompanhamento por token ou consulta pública por CPF. |
| [`lookupOwnApplication`](../public/interview-lookup.js) | 11 | Declaração | Consulta pública por CPF e exibe resultado limitado. |
| [`render`](../public/interview-lookup.js) | 13 | Atribuição de função | Escolhe e insere a tela; veja a cadeia de substituições no guia. |

## server/worker.mjs

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`now`](../server/worker.mjs) | 6 | Função arrow | Timestamp atual em milissegundos. |
| [`json`](../server/worker.mjs) | 7 | Função arrow | Cria resposta JSON com headers comuns. |
| [`fail`](../server/worker.mjs) | 9 | Função arrow | Lança Fault com status e mensagem. |
| [`text`](../server/worker.mjs) | 10 | Função arrow | Valida string, limite e obrigatoriedade. |
| [`amount`](../server/worker.mjs) | 11 | Função arrow | Valida quantidade e converte para milésimos. |
| [`hash`](../server/worker.mjs) | 12 | Função arrow | Calcula SHA-256 hexadecimal. |
| [`equal`](../server/worker.mjs) | 13 | Função arrow | Compara strings por tamanho e caracteres. |
| [`passwordHash`](../server/worker.mjs) | 14 | Declaração | Deriva hash de senha com scrypt e salt. |
| [`safeUser`](../server/worker.mjs) | 15 | Função arrow | Seleciona campos públicos da conta. |
| [`body`](../server/worker.mjs) | 16 | Declaração | Lê e interpreta JSON com limites. |
| [`limit`](../server/worker.mjs) | 17 | Declaração | Incrementa contador na janela de 15 minutos e aplica limite. |
| [`cookie`](../server/worker.mjs) | 18 | Declaração | Monta cookie de sessão conforme HTTP/HTTPS. |
| [`getUser`](../server/worker.mjs) | 19 | Declaração | Recupera usuário por token de sessão não expirado. |
| [`loginSession`](../server/worker.mjs) | 20 | Declaração | Cria sessão e resposta com cookie. |
| [`requireStaff`](../server/worker.mjs) | 21 | Função arrow | Exige sessão admin/staff. |
| [`requireAdmin`](../server/worker.mjs) | 22 | Função arrow | Exige perfil admin. |
| [`dateToday`](../server/worker.mjs) | 23 | Função arrow | Data de São Paulo para regras do servidor. |
| [`notify`](../server/worker.mjs) | 24 | Declaração | Atualiza notificações de estoque e compras. |
| [`inventory`](../server/worker.mjs) | 30 | Declaração | Carrega itens, compras, avisos e últimos movimentos. |
| [`getState`](../server/worker.mjs) | 31 | Declaração | Inicializa seed uma vez e lê JSON do gatil. |
| [`normalizeCPF`](../server/worker.mjs) | 32 | Declaração | Normaliza CPF e verifica seus dígitos. |
| [`cpfHash`](../server/worker.mjs) | 33 | Declaração | Calcula índice do CPF usando segredo persistido. |
| [`api`](../server/worker.mjs) | 34 | Declaração | Cliente fetch no frontend; roteador HTTP no Worker. |

## server/db.mjs

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`statement`](../server/db.mjs) | 1 | Função arrow | Prepara SQL e vincula parâmetros. |
| [`first`](../server/db.mjs) | 2 | Função arrow | Executa consulta de uma linha. |
| [`rows`](../server/db.mjs) | 3 | Função arrow | Retorna results de consulta de várias linhas. |
| [`run`](../server/db.mjs) | 4 | Função arrow | Executa instrução e devolve metadados. |

## server/local-db.mjs

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`openDB`](../server/local-db.mjs) | 3 | Declaração | Abre SQLite, aplica migrações e cria adaptador D1 local. |
| [`result`](../server/local-db.mjs) | 4 | Função arrow | Helper interno do adaptador para executar uma instrução. |

## server/local.mjs

Código executado no nível do módulo e callbacks anônimos. Veja o capítulo de manutenção/build ou servidor local.

## scripts/build.mjs

Código executado no nível do módulo e callbacks anônimos. Veja o capítulo de manutenção/build ou servidor local.

## tests/system.test.mjs

| Símbolo | Linha | Forma | Responsabilidade |
| --- | ---: | --- | --- |
| [`request`](../tests/system.test.mjs) | 12 | Declaração | Helper de teste que chama worker.fetch com dados/cookie/origem fictícios. |

## Blocos sem função nomeada

| Arquivo | Bloco | Responsabilidade |
| --- | --- | --- |
| `public/app.js` | `icons`, `photos`, arrays iniciais e `questions` | Ícones, imagens, exemplos e definição de campos |
| `public/management.js` | `setInterval` e listener `hashchange` | Consulta periódica de estoque e navegação |
| `public/community.js` | `questions[...]`, `volunteerFields` e referências `community...` | Ampliação da entrevista, ficha e encadeamento das funções |
| `public/interview-lookup.js` | `boot()` final | Inicia a aplicação depois de instalar as extensões |
| `server/worker.mjs` | `Fault` e export `fetch` | Classe de erro esperado e entrada HTTP |
| `server/local-db.mjs` | `binding.prepare`, `bind`, `first`, `all`, `run`, `batch`, `close` | Interface de banco local compatível com as chamadas usadas no Worker |
| `server/local.mjs` | `ASSETS.fetch`, `http.createServer`, `listen` | Arquivos públicos, adaptação HTTP e porta local |
| `scripts/build.mjs` | Instruções top-level | Cópia de assets, bundle do Worker, manifest e migrações |
| `tests/system.test.mjs` | `test(...)` | Cenário integrado sequencial com asserções |
| `db/schema.ts` | Declarações `sqliteTable` | Tabelas, defaults, FKs e índices; dicionário no capítulo 02 |
| `drizzle.config.ts` | `defineConfig` | Dialeto SQLite e caminhos de entrada/saída do gerador |
| `public/*.css` | Seletores e media queries | Famílias de estilos descritas no capítulo 01 |

## Como atualizar este índice

Execute `node docs/gerar-indice.mjs` na raiz. Se acrescentar uma função, inclua sua descrição no mapa do gerador. Depois revise os capítulos: regenerar nomes e linhas não atualiza a explicação das regras de negócio.
