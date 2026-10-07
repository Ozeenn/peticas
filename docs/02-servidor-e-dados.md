# Servidor, API, permissões e banco

[Voltar ao guia](README.md) · [Interface](01-interface.md) · [Manutenção](03-manutencao.md)

## 1. Entrada do servidor

O export principal de `server/worker.mjs` é um objeto com `async fetch(req, env)`. `req` representa a requisição; `env` fornece `DB`, `ASSETS` e a configuração privada de instalação.

1. Se o caminho começa por `/api/`, exige o banco e chama o roteador `api(req, env)`.
2. Caso contrário, pede o arquivo a `env.ASSETS.fetch(req)`.
3. Erros esperados são lançados como `Fault(status, message)` e viram JSON `{error: mensagem}`.
4. Erros inesperados geram status 500, mensagem genérica ao cliente e registro da mensagem no console do servidor.

As respostas da API usam `Content-Type: application/json`, `Cache-Control: no-store` e `X-Content-Type-Options: nosniff`. Os arquivos estáticos recebem `Cache-Control: no-cache`, `Referrer-Policy: same-origin` e `nosniff`. `no-cache` permite armazenamento com revalidação; é diferente de `no-store`.

### Execução local versus hospedagem

`server/local.mjs` cria um servidor Node, lê `.env`, abre `data/peticas.sqlite` e transforma as requisições do Node em objetos `Request`. Invoca o mesmo Worker e converte a `Response` de volta para HTTP. Seu objeto `ASSETS` lê apenas caminhos dentro da pasta `public/`. A porta padrão é 4173 e o servidor escuta em `127.0.0.1`.

O servidor local limita o corpo recebido a 65536 bytes. O helper `body` do Worker também examina `Content-Length` e o comprimento do texto lido; esse segundo teste usa comprimento de string, não uma contagem exata de bytes UTF-8. A expressão “64 KB” é uma aproximação do limite pretendido, não uma equivalência perfeita entre os ambientes.

Na hospedagem, o Worker recebe o binding D1 em `env.DB` e os assets são fornecidos pela plataforma. Os arquivos Node locais não são o backend de produção. O build empacota apenas `worker.mjs` e suas importações para o ambiente de Worker.

## 2. Helpers do backend

| Símbolo | Responsabilidade |
| --- | --- |
| `now`, `id` | Timestamp em milissegundos e UUID aleatório |
| `json` | Resposta JSON, status e headers comuns |
| `Fault`, `fail` | Erro esperado com código HTTP |
| `text` | Exige string, limita tamanho e remove espaços externos |
| `amount` | Valida quantidade e converte para milésimos inteiros |
| `hash` | SHA-256 em hexadecimal |
| `equal` | Compara strings percorrendo caracteres quando os tamanhos coincidem; não deve ser descrito como garantia formal de tempo constante |
| `passwordHash` | scrypt com salt e parâmetros definidos no código |
| `safeUser` | Seleciona somente `id`, `name`, `email`, `role` para a resposta |
| `body` | Exige JSON, aplica limites e faz parse |
| `limit` | Conta tentativas em janelas fixas de 15 minutos |
| `cookie`, `getUser`, `loginSession` | Cookie, recuperação de conta pela sessão e abertura de sessão |
| `requireStaff`, `requireAdmin` | Verificações de autenticação/perfil |
| `dateToday` | Data civil no fuso America/Sao_Paulo |
| `notify`, `inventory` | Recalcula avisos e carrega o conjunto de dados de estoque |
| `getState` | Inicializa/lê o JSON do gatil em `settings` |
| `normalizeCPF`, `cpfHash` | Valida dígitos do CPF e calcula a chave de busca |
| `api` | Roteia método e caminho para as regras de negócio |

`body` verifica se o JSON é sintaticamente válido, mas não impõe por si só um objeto com esquema completo. Cada rota faz sua própria validação. JSON válido com formato inesperado pode ainda produzir erro 500 em caminhos que assumem um objeto. Uma melhoria é centralizar a validação estrutural.

## 3. Autenticação e autorização

### Senhas e sessão

As senhas são armazenadas como `salt:hash`, usando scrypt (`N=16384`, `r=8`, `p=5`, `dkLen=32`) e salt aleatório de 16 bytes. Não são guardadas em texto puro. Senhas novas devem ter entre 12 e 128 caracteres nas rotas de criação/alteração.

O login cria token aleatório de 32 bytes, entrega o valor no cookie e guarda **somente SHA-256 do token** na tabela `sessions`. A sessão dura sete dias. Em HTTPS, o nome começa com `__Host-` e o cookie usa `Secure`, `HttpOnly`, `SameSite=Lax` e `Path=/`. Localmente, sem HTTPS, não usa `Secure` nem o prefixo.

`HttpOnly` impede ler o cookie por JavaScript da página; o navegador ainda o envia nas requisições. `getUser` calcula o hash do cookie e procura uma sessão não expirada ligada a um usuário. `requireStaff` aceita apenas `admin` ou `staff`.

### Perfis e limites

| Ação | Visitante | Voluntário (`staff`) | Dona (`admin`) |
| --- | --- | --- | --- |
| Ver gatos disponíveis, enviar entrevista | Sim | Sim | Sim |
| Consultar CPF público | Status/data | Status/data | Status/data |
| Usar link pessoal de acompanhamento | Com token | Com token | Com token |
| Consultar prontuário e registrar novos eventos | Não | Sim | Sim |
| Ver estoque, compras, movimentos e avisos | Não | Sim | Sim |
| Movimentar saldo existente | Não | Sim | Sim |
| Cadastrar/editar descrição, categoria e mínimo do item | Não | Não | Sim |
| Agendar, receber ou cancelar compra | Não | Não | Sim |
| Criar voluntário, ler ficha e mudar acesso | Não | Não | Sim |
| Ver respostas e decidir candidatura | Não | Não | Sim |
| Vincular CPF a candidatura antiga | Não | Não | Sim |
| Alterar gatos e cuidados legados em `/api/state` | Não | Não | Sim |
| Alterar a própria senha/gerar recuperação | Não | Sim | Sim |
| Ler orientações de entrada e grupo | Não | Sim | Sim |

`pending` e `blocked` são valores conservados para gestão de acesso. Podem obter uma resposta de login se as credenciais forem válidas, mas as rotas internas negam o acesso e a interface apresenta a situação. Alterar o perfil exclui as sessões daquele usuário; a rota não permite transformar outro usuário em admin.

### Primeiro acesso e recuperação

`POST /api/register` funciona somente enquanto não existe admin. Exige a chave `ADMIN_SETUP_KEY`. A inserção também inclui condição de inexistência de admin para reduzir a corrida entre duas instalações. Depois, `POST /api/users` é a rota de cadastro de voluntários usada pela responsável.

Recuperação não envia e-mail. A conta usa um código aleatório, cujo hash fica em `settings['recovery:ID']`. Gerar um novo código exige a senha atual e invalida o anterior. Redefinir a senha exige e-mail, código e nova senha; a operação gira o código e revoga as sessões. Enquanto a responsável não tiver um código próprio registrado, a chave de instalação pode funcionar como código inicial. Trate essa chave como segredo de alto privilégio.

### Origem e tentativas

Todas as requisições que não são GET/HEAD exigem que o header `Origin` seja exatamente a origem da URL. Isso é uma defesa contra requisições de outras páginas, mas **não substitui login nem prova identidade**: clientes HTTP não navegadores conseguem definir esse header.

| Operação | Limite por janela fixa de 15 min |
| --- | --- |
| Primeiro cadastro | 8 por IP |
| Login | 30 por IP e 10 por e-mail |
| Envio de candidatura | 5 por IP |
| Acompanhamento por token | 60 por IP |
| Consulta pública por CPF | 10 por IP |
| Consulta interna por CPF | 20 por conta |
| Recuperação | 5 por IP e 5 por e-mail |
| Geração de código de recuperação | 5 por conta |
| Troca autenticada de senha | 5 por conta |

O IP vem de `CF-Connecting-IP`, com fallback `local`. No servidor local, pedidos sem esse header compartilham o mesmo contador. A implementação pressupõe que a plataforma confiável controle o header em produção. A tabela tem `expires`, mas não há rotina de limpeza automática no código atual. Não é uma janela móvel: o contador muda a cada bloco de 15 minutos do relógio.

## 4. Catálogo completo da API

Todas as rotas abaixo têm prefixo `/api`. IDs no caminho são valores reais retornados pelo sistema, não nomes de pessoas. Pedidos de escrita usam JSON. Para rotas privadas, inclua a sessão; no navegador isso é feito automaticamente.

### Rotas públicas

| Método e caminho | Entrada | Saída principal / efeito |
| --- | --- | --- |
| `GET /session` | Nenhuma | `{user, setupRequired}` |
| `POST /register` | `name`, `email`, `password`, `setupKey` | Primeira responsável e cookie de sessão |
| `POST /login` | `email`, `password` | `{user}` e cookie |
| `POST /logout` | Objeto vazio | Revoga a sessão apresentada e expira cookie |
| `GET /cats` | Nenhuma | `{cats}` apenas com status Disponível |
| `POST /adoptions` | `{cat: número ou null, answers: objeto}` | HTTP 201, `{token, request}` |
| `POST /tracking` | `{token}` | `{request:{id,name,cat,stage,guidance}}` |
| `POST /tracking/cpf` | `{cpf}` | `{results:[{stage,date}]}`; lista vazia quando não encontra |
| `POST /reset-password` | `email`, `code`, `password` | `{ok, recoveryCode}`; muda senha e revoga sessões |

`POST /adoptions` valida CPF, idade de 18 a 120, telefone, nome, endereço e segurança, além de limites gerais dos valores. O formulário exige mais respostas do que a API verifica individualmente. As chaves aceitas em `answers` devem conter apenas letras, e os valores devem ser strings de até 2500 caracteres. O gato, quando informado, precisa estar disponível.

### Conta ativa: admin ou staff

| Método e caminho | Entrada | Saída principal / efeito |
| --- | --- | --- |
| `POST /password` | `current`, `password` | Muda senha, revoga sessões e abre uma nova |
| `POST /recovery-code` | `current` | Novo `recoveryCode`, mostrado uma vez |
| `GET /state` | Nenhuma | Gatos, cuidados legados, versão; candidaturas completas somente para admin |
| `GET /inventory` | Nenhuma | `{items,purchases,notifications,movements}` |
| `POST /items/:id/movements` | `id`, `type`, `quantity`, `reason`, `version` | Altera saldo e insere movimento |
| `POST /notifications/read` | `{id}` do aviso | Marca leitura para a conta atual |
| `POST /adoptions/lookup` | `{cpf}` | Somente lista de status/data |
| `GET /medical` | Nenhuma | `{records}` com JSON decodificado e nome do responsável |
| `POST /medical` | Evento clínico descrito abaixo | Acrescenta registro ao histórico |
| `GET /volunteer-guide` | Nenhuma | Dados de entrada e link do grupo interno |

### Somente admin

| Método e caminho | Entrada | Saída principal / efeito |
| --- | --- | --- |
| `GET /users` | Nenhuma | Lista de `id,name,email,role,created` |
| `POST /users` | Nome, e-mail, senha e campos da ficha | Cria usuário staff e ficha; HTTP 201 `{id}` |
| `GET /users/:id/profile` | ID no caminho | `{profile}` ou `null` para ficha inexistente |
| `PATCH /users/:id` | `{role}`: staff, pending ou blocked | Altera perfil de não-admin e revoga sessões |
| `PUT /state` | `cats`, `vaccines`, `meds`, `version` | Substitui JSON do gatil e incrementa versão |
| `PATCH /adoptions/:id` | `cat`, `stage`, `guidance`, `version` | Atualiza candidatura e situação do gato |
| `PATCH /adoptions/:id/cpf` | `cpf`, `version` | Atualiza CPF em respostas e seu índice de busca |
| `POST /items` | `name,category,unit,quantity,minimum,notes` | Cria item e movimento inicial, HTTP 201 `{id}` |
| `PATCH /items/:id` | `name,category,minimum,notes,version` | Edita cadastro; unidade/saldo não são alterados aqui |
| `POST /purchases` | `itemId,quantity,due,supplier,notes` | Agenda compra, sem alterar saldo; HTTP 201 |
| `PATCH /purchases/:id` | `{status:'received' ou 'cancelled'}` | Recebe uma vez ou cancela |

O roteador é uma sequência de `if`, não uma biblioteca de roteamento. A posição importa: `/adoptions/:id/cpf` precisa ser tratada antes do `startsWith('/api/adoptions/')` usado na atualização geral. O limite entre rotas públicas e privadas é a linha que executa `getUser` e `requireStaff`.

### Evento de prontuário

Campos comuns: `id` gerado pelo cliente, `kind`, `catId`, `date`, `time`, `notes`. O servidor determina `user_id` pela sessão e `created` pelo relógio; não confia em um nome de responsável enviado pelo formulário.

| `kind` | Exigências adicionais |
| --- | --- |
| `treatment` | `label`, `dose`, `frequency`, `prescriber`; `endDate` opcional |
| `application` | `treatmentId` válido para o mesmo gato e `time` obrigatório |
| `note` | `notes` não vazio |
| `completion` | `treatmentId` válido para o mesmo gato |

Datas usam `YYYY-MM-DD`, horário `HH:mm`. O fim previsto não pode ser anterior à data do registro. Aplicações/encerramentos não podem anteceder o início e não são aceitos depois de já haver encerramento. A API não gera automaticamente as próximas doses nem impede toda possível data futura. O estoque não é descontado automaticamente ao registrar medicamento.

### Exemplo didático de requisição

No PowerShell, este exemplo consulta um CPF fictício no servidor local, sem criar candidatura:

```powershell
$payload = @{ cpf = '11144477735' } | ConvertTo-Json
Invoke-RestMethod `
  -Uri 'http://127.0.0.1:4173/api/tracking/cpf' `
  -Method Post `
  -ContentType 'application/json' `
  -Headers @{ Origin = 'http://127.0.0.1:4173' } `
  -Body $payload
```

Sem registro correspondente, a resposta é `{"results":[]}`. Não use dados pessoais de terceiros para testes. Para experimentar criação, login ou mudanças de saldo, use banco descartável/local.

### Códigos HTTP que aparecem

| Código | Interpretação |
| --- | --- |
| 200 / 201 | Operação concluída / registro criado |
| 400 | Dados inválidos ou regra de negócio não atendida |
| 401 | Sessão ausente/inválida ou credenciais incorretas |
| 403 | Origem inválida, perfil insuficiente ou primeiro cadastro bloqueado |
| 404 | Registro/recurso não encontrado |
| 409 | Conflito de versão, duplicidade ou tratamento encerrado |
| 413 / 415 | Corpo grande demais / formato não JSON |
| 429 | Limite de tentativas atingido |
| 500 / 503 | Erro inesperado / binding de banco indisponível |

Uma rota desconhecida na área protegida pode responder 401/403 antes de chegar ao 404, porque a autorização é executada antes da seleção final da rota.

## 5. Dicionário do banco

O esquema atual mistura tabelas relacionais com objetos JSON guardados em colunas `TEXT`. Não há uma tabela `cats`: gatos ainda vivem no JSON da chave `gatil`.

| Tabela | Colunas e finalidade |
| --- | --- |
| `users` | `id` PK texto; `name,email,password,role` texto; `created` timestamp. E-mail único |
| `sessions` | `id` PK: hash do token; `user_id` FK; `expires` timestamp com índice |
| `rate_limits` | `key` PK hash da chave/janela; `count`; `expires` |
| `settings` | `key` PK; `value` texto; `version` inteiro padrão 1 |
| `items` | `id` PK; `name,category,unit,notes`; `quantity,minimum` em milésimos; `version`; `created,updated` |
| `movements` | `id` PK; `item_id,user_id` FKs; `delta` em milésimos; `reason`; `created`. Índice item/data |
| `purchases` | `id` PK; `item_id,user_id` FKs; `quantity`; `due` data; `supplier,notes,status`; `created,completed`. Índice status/data |
| `notifications` | `id` PK; `kind`; `item_id,purchase_id` FKs opcionais; `message`; `created,resolved`. Índice resolução/data |
| `notification_reads` | `id` PK; `notification_id,user_id` FKs; combinação usuário/aviso única |
| `adoption_requests` | `id` PK; `token_hash` único; `cpf_hash` indexado e opcional; `data` JSON; `version`; `created` |
| `medical_records` | `id` PK; `cat_id` inteiro; `treatment_id` texto opcional; `kind`; `data` JSON; `user_id` FK; `created`. Índice gato/data |

PK é chave primária: identifica uma linha. FK é chave estrangeira: referencia uma linha de outra tabela. `cat_id` e `treatment_id` no prontuário **não possuem FKs declaradas**; sua consistência é validada na API. Os gatos não estão em tabela própria para permitir uma FK relacional direta.

### Chaves de `settings`

| Chave | Conteúdo |
| --- | --- |
| `gatil` | JSON `{cats, vaccines, meds}` com versão compartilhada |
| `volunteer:ID` | JSON da ficha pessoal de um voluntário |
| `recovery:ID` | Hash do código privado de recuperação |
| `cpf-secret` | Segredo aleatório usado para o índice de busca de CPF |

Não publique exportações de `settings`: além de dados de gatos, a tabela contém dados pessoais e valores sensíveis. A ficha inclui idade, endereço, telefone, ocupação, transporte, experiência, habilidades, disponibilidade, preferências, motivação, aceites, nome de quem aceitou e data. O nome digitado como aceite não implementa assinatura digital.

### Formatos JSON principais

* Gato: `id,name,age,sex,personality,tags,photo,status,story`. A idade é texto, como “2 anos”; o filtro tenta convertê-la para meses.
* Vacina antiga: `cat,label,date,status,done`, com `applied,person,next,proof` quando registrada. `proof` guarda nome de arquivo, não o arquivo.
* Medicamento antigo: `cat,label,time,done`; não possui um histórico completo de cada aplicação.
* Candidatura: `id,name,cat,stage,date,answers,guidance,note`. `date` é texto para exibição; `created` da tabela é a data técnica ordenável.
* Registro médico: `label,date,time,dose,frequency,endDate,prescriber,notes`. Mesmo campos não utilizados no tipo de evento podem existir como strings vazias.

As migrações não impõem enums para roles, categorias ou tipos; grande parte das regras está no JavaScript. Editar o banco manualmente pode introduzir valores que a aplicação não espera.

## 6. Por que o estoque guarda 2500 para representar 2,5?

`amount(2.5)` retorna `2500`. Isso evita somar valores fracionários usando ponto flutuante no saldo persistido. `quantity(2500)` no frontend divide por 1000 e apresenta “2,5”. Valores enviados pela tela são unidades humanas; valores retornados nas linhas do banco são milésimos.

| Operação | Cálculo |
| --- | --- |
| Entrada de 2 kg | `delta = +2000` |
| Saída de 0,5 kg | `delta = -500` |
| Ajustar saldo para 3 kg quando há 2 kg | `delta = 3000 - 2000 = 1000` |

Categorias aceitas: Ração, Medicamento, Sachê, Areia, Higiene, Outros. Unidades: kg, g, un, caixa, frasco, l. A aplicação não converte kg para g nem caixa para unidade. A unidade de um item não é editável na rota de atualização. Não altere essa convenção sem migrar também o histórico e as compras.

## 7. Versões, transações e idempotência

### Concorrência otimista

Imagine que duas pessoas carregam um item na versão 3. A primeira salva e o banco passa à versão 4. A segunda envia versão 3. O SQL `WHERE id=? AND version=?` não encontra a combinação e a API responde 409. A segunda pessoa precisa recarregar e revisar sua intenção.

Essa proteção existe no saldo/cadastro do item, estado do gatil e candidaturas. Não substitua por atualização sem `version` para “eliminar o erro”: isso permitiria sobrescrever alterações de outra pessoa.

### Transações

`env.DB.batch` agrupa operações. No adaptador local isso é implementado com `BEGIN IMMEDIATE`, execução dos comandos e `COMMIT`; exceção causa `ROLLBACK`. A aplicação usa esse padrão para saldo + movimento, compra + recebimento, usuário + ficha e candidatura + situação do gato.

Vários comandos dependem de `changes()=1`, que se refere às linhas alteradas pela instrução anterior na conexão. A ordem do lote é parte da lógica. Inserir uma consulta ou gravação entre esses comandos sem analisar a dependência pode quebrar a atomicidade pretendida.

### Idempotência

Uma operação idempotente pode ser repetida sem duplicar o efeito. O movimento usa um `id` criado no formulário; recebimento usa `received-` seguido do ID da compra. O registro médico reconhece um ID já gravado e compara seu conteúdo. O teste cobre repetição sequencial de operações importantes.

Limites atuais: o teste não simula concorrência real de várias conexões; no prontuário, duas inserções simultâneas do mesmo ID podem atingir a restrição única após ambas passarem pela leitura inicial. No movimento, encontrar qualquer ID existente retorna sucesso sem comparar todo o payload. São pontos para testes e endurecimento, não provas de que toda corrida possível esteja resolvida.

## 8. Estados de adoção e saúde

| `stage` | Rótulo |
| --- | --- |
| -1 | Recusada |
| 0 | Recebida |
| 1 | Entrevista em análise |
| 2 | Visita domiciliar |
| 3 | Aprovada |
| 4 | Adoção concluída |

A API normalmente aceita manter a etapa, avançar uma ou recusar. Na aprovação, exige gato e o marca Reservado. Na conclusão, marca Adotado. Ao recusar uma candidatura que estava aprovada, libera o gato antigo. A tela deixa de oferecer ações quando a etapa é -1 ou 4.

**Limite do código atual:** a validação do servidor usa `[a.stage, a.stage+1, -1]`, sem declarar -1 e 4 como estados terminais. Assim, uma chamada manual pode tentar reabrir uma recusada ou recusar uma concluída, embora a interface não ofereça isso. Revise essas transições antes de implementar reabertura/cancelamento; a situação do gato precisa continuar coerente.

Prontuários novos são somente de acréscimo pela API. Não existem rotas para apagar/editar eventos antigos; correções são registradas como evolução. Isso preserva os registros pela interface, mas não é uma trilha criptograficamente imutável nem impede alterações por um administrador direto do banco.

## 9. Notificações

`notify` cria aviso quando `quantity <= minimum`; saldo zero recebe texto de falta. Resolve o aviso quando o saldo fica acima do mínimo. Também cria aviso de compra com data prevista menor ou igual à data atual e resolve quando a compra deixa de estar agendada. As leituras individuais ficam em `notification_reads`.

Esses cálculos acontecem em consultas/alterações de estoque. Não há agendador de servidor, e-mail, WhatsApp automático ou push. A tela aberta consulta periodicamente. Não prometa que o site avisará alguém com o navegador fechado.

## 10. CPF e dados pessoais

`normalizeCPF` remove pontuação/espaços e verifica os dois dígitos verificadores. Isso verifica a forma matemática do número, não sua titularidade. `cpfHash` calcula SHA-256 de segredo persistido + separador + CPF normalizado. Não apague nem troque `cpf-secret` sem recalcular os índices: registros existentes deixariam de ser encontrados.

O índice com hash não significa que o CPF desapareceu do banco: ele também está em `answers.cpf`, no JSON completo da candidatura. Respostas e fichas não têm criptografia em nível de aplicação. Um backup deve ser tratado como sensível.

A consulta pública mostra somente etapa/data, mas qualquer pessoa que saiba um CPF válido pode tentar consultá-lo. O limite de tentativas reduz abuso, não autentica o adotante. O link pessoal é outro mecanismo: quem possui o token consegue ver nome, gato, etapa e orientação. Não exponha esse link em logs, redes sociais ou exemplos reais da documentação.

`GET /cats` devolve os objetos completos dos gatos disponíveis, sem selecionar uma lista explícita de campos públicos. Se você acrescentar observações privadas ao objeto do gato, terá de filtrar a resposta antes de publicar. Hoje o prontuário novo está em outra tabela, acessível somente pela API interna.

## 11. Migrações e adaptador SQL

| Arquivo | Alteração |
| --- | --- |
| `0000_nervous_squirrel_girl.sql` | Estrutura inicial de contas, sessões, limites, settings, estoque, compras, avisos e adoção |
| `0001_broken_tenebrous.sql` | Tabela de registros médicos e índice |
| `0002_loving_cyclops.sql` | Coluna `cpf_hash` e índice em candidaturas |

Os nomes foram gerados pelo Drizzle; não têm significado de negócio. A numeração e o journal determinam o histórico. Migrações já publicadas devem ser preservadas: escreva uma nova para uma nova alteração.

`server/db.mjs` encapsula `prepare(sql).bind(...args)`. `first` devolve uma linha, `rows` a lista de resultados, `run` metadados de gravação e `statement` a instrução preparada usada em batches. Use parâmetros `?`; não concatene conteúdo de formulário em SQL.

`server/local-db.mjs` usa `node:sqlite`, ativa FKs e WAL e aplica arquivos `.sql` ordenados. Registra os já executados em `_local_migrations`, tabela técnica local que não integra as 11 tabelas do esquema da aplicação. O adaptador imita os métodos D1 suficientes para este projeto; passar no SQLite local não é uma garantia de todas as características operacionais do ambiente remoto.
