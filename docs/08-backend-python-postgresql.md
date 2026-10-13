# Backend Python e PostgreSQL

Esta é a documentação técnica da implementação atual, iniciada em 13 de outubro de 2026. A execução principal usa FastAPI, Psycopg 3 e PostgreSQL 17. O frontend continua em `public/`, com a mesma API `/api/`. Não houve publicação nem migração de dados antigos: o usuário optou por banco novo com exemplos.

## Executar com Docker

Requer Docker Desktop em execução, com suporte a contêineres Linux.

1. Copie `.env.example` para `.env` somente se `.env` ainda não existir.
2. Defina `POSTGRES_PASSWORD` com uma senha aleatória longa usando letras e números, e `ADMIN_SETUP_KEY` com uma chave aleatória longa. A senha é interpolada na URL de conexão, portanto caracteres especiais precisam de codificação na URL; a configuração local usa letras e números para simplificar.
3. Execute `docker compose up --build -d` na raiz do projeto.
4. Abra `http://127.0.0.1:4173`. Crie a responsável com a chave de instalação.
5. Confira `docker compose ps` e, se necessário, `docker compose logs api jobs`.

`pnpm dev` executa `docker compose up --build` em primeiro plano. `pnpm build` constrói as imagens Docker. Node não é necessário para executar a nova API.

Serviços:

| Serviço | Responsabilidade |
| --- | --- |
| `db` | PostgreSQL, sem porta publicada no host |
| `api` | API Python e arquivos do frontend, porta local 4173 |
| `jobs` | Relatório semanal e processamento da fila a cada minuto |
| `gateway` | Integração WhatsApp opcional, habilitada pelo perfil `whatsapp` |

O banco usa o volume nomeado `postgres_data`. `docker compose down` encerra os serviços e mantém o volume. Faça backup antes de remover volumes. Os arquivos SQLite antigos ficam separados e não são utilizados pela API Python.

`SEED_DEMO=true` insere seis gatos fictícios uma única vez, sem cadastrar usuários. Os gatos são disponíveis ou estão em tratamento; não são criadas reservas sem candidatura. Os exemplos antigos de vacina com datas textuais desatualizadas não são carregados. Use `SEED_DEMO=false` para instalação sem gatos de exemplo. A flag não apaga dados já inseridos.

## Nomes em português e prefixos

Todos os nomes físicos de tabelas e colunas do novo banco estão em português. Cada coluna tem um prefixo de três letras que identifica seu tipo ou finalidade:

| Prefixo | Finalidade | Exemplo |
| --- | --- | --- |
| `cod_` | Identificador ou referência | `cod_identificador`, `cod_gato`, `cod_usuario` |
| `txt_` | Texto | `txt_nome`, `txt_endereco`, `txt_senha_hash` |
| `num_` | Número | `num_versao`, `num_etapa`, `num_intervalo_horas` |
| `dat_` | Data ou instante | `dat_cadastro`, `dat_entrada`, `dat_expiracao` |
| `hor_` | Horário | `hor_horario` |
| `flg_` | Valor lógico | `flg_realizado`, `flg_devolvido` |
| `bin_` | Conteúdo binário | `bin_conteudo` |

Os instantes técnicos, como cadastro, expiração e envio, usam `timestamptz`. Datas de domínio usam `date`; horários usam `time`; campos `flg_` usam `boolean`. Datas opcionais ficam nulas quando não informadas. A camada de compatibilidade converte esses tipos para o JSON esperado pela interface, incluindo instantes em milissegundos. O tipo SQL exato está na migração e os testes verificam a correspondência dos prefixos.

`backend/naming.py` mapeia nomes físicos para os campos utilizados pela interface. Isso preserva `cat_id`, `created` e os demais campos JSON já existentes sem manter tabelas em inglês. Códigos de permissões e estados usados no protocolo existente continuam compatíveis com o frontend.

## Modelo relacional

| Tabelas | Relação e função |
| --- | --- |
| `usuarios`, `fichas_voluntarios` | Conta e ficha em relação 1:1; CPF, contato, disponibilidade e aceite em colunas próprias |
| `permissoes`, `permissoes_usuarios` | Catálogo e associação N:N; sem lista JSON de permissões |
| `sessoes`, `limites_requisicoes` | Sessões revogáveis e limites persistentes de tentativas |
| `gatos`, `caracteristicas_gatos`, `fotos_gatos` | Cadastro, características 1:N e foto atual vinculada a anexo |
| `propostas_gatos` | Proposta independente com autor, revisão, versão e referência ao gato aprovado |
| `vacinas`, `tarefas_cuidados` | Cuidados simplificados da interface, cada registro ligado a um gato |
| `candidaturas_adocao`, `respostas_entrevistas` | Candidatura e respostas por pergunta, sem documento JSON contendo toda a entrevista |
| `historico_etapas_adocao`, `eventos_adocao` | Mudanças de etapa, acompanhamento, termo e devolução em registros separados |
| `registros_clinicos` | Prescrições, doses, evolução e encerramento; FK composta garante gato correspondente ao tratamento |
| `anexos` | Arquivos binários e metadados; FK para gato ou candidatura, com restrição de vínculo exclusivo |
| `campanhas`, `configuracoes` | Campanhas em linhas próprias; configuração escalar, como Pix e segredo do índice de CPF |
| `fila_mensagens` | Avisos com chave única, tentativas, prazo da próxima tentativa e confirmação de envio |
| `envios_whatsapp`, `entregas_whatsapp` | Deduplicação e resultado por destinatário no gateway, também no PostgreSQL |
| `revisoes_estado`, `migracoes_esquema` | Versão de compatibilidade da interface e migrações aplicadas com hash |

Listas e históricos que antes ficavam em `settings` e `data` passaram a relações com chaves primárias e estrangeiras. As tabelas de estoque não são recriadas: esse módulo já havia saído do escopo. Suas rotas continuam respondendo 410 após autenticação.

Reservar um gato e mudar a candidatura acontece na mesma transação. Há bloqueio de registros, comparação de versões e índice único que impede duas adoções ativas para o mesmo gato. Devolver preserva a candidatura concluída e libera o gato. O banco impede duplicar uma dose programada, encerrar duas vezes o mesmo tratamento ou registrar duas devoluções para a mesma candidatura.

As transações são confirmadas ao concluir a operação e desfeitas em caso de falha, conforme o [gerenciamento de transações do Psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html). O frontend é servido pela mesma aplicação usando [StaticFiles do FastAPI](https://fastapi.tiangolo.com/tutorial/static-files/), mantendo a origem única para os formulários.

## Código e migrações

- `backend/app.py`: autenticação, equipe, gatos, candidaturas, anexos e prontuário.
- `backend/repository.py`: gravações relacionais e reconstrução das respostas para o navegador.
- `backend/security.py`: senha scrypt, CPF, sessão, permissões e limites.
- `backend/schedule.py`: cálculo de doses previstas.
- `backend/jobs.py`: rotina de mensagens e relatório de sábado/domingo, enfileirado às sextas no horário de São Paulo.
- `backend/gateway.py`: armazenamento PostgreSQL para o gateway Python existente.
- `backend/db.py`: pool, migrações transacionais e carga opcional dos exemplos.
- `backend/migrations/001_initial.sql`: estrutura do PostgreSQL; acrescente migrações numeradas para mudanças futuras.

Migrações são aplicadas no início da API sob bloqueio exclusivo entre instâncias. Alterar o conteúdo de uma migração já aplicada gera erro de verificação; crie uma nova migração. Uma restauração exige backup do volume ou exportação com `pg_dump`, não apenas o código do Git.

`server/`, `db/schema.ts`, `drizzle/` e os testes `.mjs` do Worker continuam disponíveis como legado de referência. `pnpm dev:legacy` e `pnpm build:legacy` executam explicitamente essa versão. Ela tem banco independente; não use suas migrações para o PostgreSQL. Os guias 01–07 descrevem principalmente essa implementação anterior.

## WhatsApp opcional

Use `WHATSAPP_WEBHOOK_URL=http://gateway:8001/messages`, um `WHATSAPP_WEBHOOK_TOKEN` de pelo menos 32 caracteres ASCII e os aliases `owner`/`volunteers`. Configure `WHATSAPP_OWNER_NUMBERS` e `WHATSAPP_VOLUNTEERS_NUMBERS` com telefones completos, separados por vírgulas.

Execute `docker compose --profile whatsapp up --build -d`. O gateway fica somente na rede interna do Compose e usa as tabelas PostgreSQL da API. `WHATSAPP_DRY_RUN=true` simula e não confirma envio real. A fila permanece pendente até receber `accepted=true`, `simulated=false` e o ID correto. Para envio real, configure os dados da Meta e as opções de modelo já descritas no guia 07. Não foram configuradas credenciais reais nem enviados avisos durante os testes.

## Testes

Para executar os testes com o PostgreSQL do Compose:

Use a URL já disponível no contêiner, sem informar a senha na linha de comando:

```powershell
docker compose exec api python -c "import os,pytest; os.environ['PETICAS_TEST_DATABASE_URL']=os.environ['DATABASE_URL']; raise SystemExit(pytest.main(['backend/tests','-q']))"
```

Os testes criam esquemas exclusivos e removem apenas esses esquemas ao terminar. Não limpam tabelas existentes. Use um banco destinado a testes; sem `PETICAS_TEST_DATABASE_URL`, os testes integrados são marcados como ignorados.

Sem Docker, instale `backend/requirements.txt` em um ambiente virtual, defina `DATABASE_URL`, `ADMIN_SETUP_KEY` e opcionalmente `SEED_DEMO` no ambiente e execute `python -m backend.run`. A rotina de mensagens é outro processo: `python -m backend.jobs`. O servidor Python não carrega `.env` automaticamente nessa modalidade.

Os testes cobrem sessões, permissões, recuperação, privacidade da consulta por CPF, propostas, concorrência na reserva, devolução, anexos, doses, encerramento, fila, gateway, migrações e padrão dos nomes. A integração real com a Meta exige credenciais e não é exercitada pelos testes.

## Acompanhamento e rotina dos voluntários

A consulta por CPF lista todas as candidaturas vinculadas, com as cinco etapas do processo e as datas das etapas registradas. Respostas da entrevista, nomes, identificadores privados e mensagens da responsável não são retornados nessa consulta. Etapas antigas sem data registrada são identificadas sem inventar uma data. O link individual mostra o histórico e as mensagens da responsável, preservadas em `mensagens_candidaturas`; o candidato pode atualizar o acompanhamento pelo botão da página.

Voluntários têm uma tela resumida com as doses programadas e as vacinas previstas. Quem possui `medical.write` pode registrar uma aplicação de medicamento ou uma vacina; quem possui apenas `medical.read` consulta sem botões de registro. A aplicação de vacina usa a conta autenticada como responsável, registra data e versão e impede duplicidade. IDs e atribuição das vacinas são preservados ao adicionar outros cuidados.

Aplicações de medicamento exigem uma leitura recente de localização, solicitada apenas na confirmação do registro. Sem permissão ou sem localização, a aplicação não é gravada. Coordenadas, precisão e instante da coleta são armazenados em `localizacoes_aplicacoes`, com vínculo ao registro clínico; a API verifica os valores e aceita uma leitura de até dois minutos. A responsável visualiza esses dados e pode abrir o ponto no mapa. Voluntários, adotantes e consultas públicas não recebem as coordenadas. Registros anteriores à mudança permanecem sem localização.

A localização depende da permissão explícita do dispositivo e de contexto seguro, conforme a [documentação da Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition). Em produção, use HTTPS; para desenvolvimento, use a origem local. As coordenadas são informadas pelo navegador e não são uma comprovação de presença no gatil nem uma restrição por distância. Não há rastreamento contínuo.

A migração `002_acompanhamento_cuidados.sql` acrescenta os históricos de mensagens e localização sem modificar a migração inicial nem apagar registros existentes. O frontend carrega `care-tracking.js` por último, depois de `requirements.js`, e só então inicia a sessão.
