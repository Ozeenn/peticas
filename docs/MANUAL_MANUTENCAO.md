# Manual de manutenção do Peticas

Este manual descreve o código atual: backend Python/FastAPI, PostgreSQL e interface HTML/CSS/JavaScript. Destina-se à equipe que fará manutenção. O trabalho acadêmico aprovado segue o padrão próprio e não deve ser regenerado para alterar a aplicação.

## 1. Como o projeto funciona

O navegador carrega `public/index.html`. Os arquivos JavaScript montam as telas e enviam pedidos para `/api/`. A API identifica a sessão, confere a permissão, valida os campos e lê ou grava no PostgreSQL. A rotina `jobs` processa a fila de avisos; o gateway WhatsApp é opcional. O Docker mantém esses processos separados.

| Pasta / arquivo | O que contém | Quando mexer |
| --- | --- | --- |
| `public/index.html` | Página de entrada e ordem dos scripts e estilos | Incluir um arquivo JS/CSS novo ou alterar metadados |
| `public/app.js` | Estrutura original das páginas, filtros, modal e perguntas | Alterar conteúdo base e componentes existentes; conferir os módulos que sobrescrevem funções |
| `public/management.js` | Cliente HTTP, login, sessão e formulários | Autenticação, mensagens de erro e comunicação com a API |
| `public/community.js` | Conteúdo do gatil e campos adicionais | Visitas, orientações e dados institucionais |
| `public/interview-lookup.js` | Consulta de candidatura e vínculo de CPF | Fluxos de consulta e acompanhamento |
| `public/requirements.js` | Área da equipe, permissões, cadastro e checklist | Gatos, voluntários, cuidados, doações e decisões |
| `public/navigation-motion.js` | Animação e troca de página | Navegação e preferência de redução de movimento |
| `public/care-tracking.js` | Etapas completas, tela resumida e localização | Cuidados dos voluntários e acompanhamento por CPF |
| `public/documents-privacy.js` | Botões PDF, aviso, escolhas e pedidos LGPD | Documentos e interfaces de privacidade |
| `public/*.css` | Layout e identidade visual | Cores, espaçamentos, telas e responsividade |
| `public/assets/` | Logo e imagens estáticas da aplicação | Trocar marca ou ilustrações; não cadastrar fotos de gatos por aqui |
| `backend/app.py` | Rotas, regras e permissões | Alterar comportamento do servidor; o controle de acesso deve estar aqui |
| `backend/repository.py` | Gravação relacional e montagem das respostas | Consultas, novos campos e representação da API |
| `backend/security.py` | CPF, senha, sessão, limites e permissões | Regras de acesso e validação |
| `backend/schema.sql` | Esquema completo para banco novo | Alterar tabelas, índices e restrições; banco existente exige SQL explícito |
| `backend/naming.py` | Nomes físicos e conversão de tipos | Mapear colunas em português para os campos da API |
| `backend/db.py` | Pool, criação inicial e verificação do banco | Configuração de conexão e inicialização |
| `backend/seed.json` | Gatos fictícios para demonstração | Somente mudar exemplos de instalações novas |
| `backend/reports.py` | Layout e conteúdo dos PDFs | Ficha completa e impressão do termo |
| `backend/templates/termo_adocao.json` | Cláusulas e versão do modelo | Revisar texto do termo, sem alterar o restante do código |
| `backend/privacy.py` | Aviso, versões, ciência e pedidos | Atualizar finalidades e regras de privacidade |
| `backend/schedule.py` | Cálculo de doses previstas | Programação conforme a prescrição registrada |
| `backend/jobs.py` | Fila e relatório semanal | Agendamento, tentativas e confirmação de envio |
| `backend/gateway.py`, `backend/whatsapp.py` | Persistência e chamadas à Meta | Integração WhatsApp |
| `backend/tests/`, `tests/interface.test.mjs` | Testes Python e da interface | Verificar regras modificadas e impedir regressões |
| `compose.yaml`, `backend/Dockerfile` | Serviços e imagem Docker | Portas, processos e empacotamento |
| `.env` | Segredos e configuração local | Senha do PostgreSQL, instalação e WhatsApp; nunca commitar |
| `.env.example` | Modelo sem segredos | Documentar novas variáveis de ambiente |
| `backend/requirements.txt`, `backend/requirements.lock.txt` | Dependências declaradas e versões fixadas | Adicionar ou atualizar biblioteca Python e conferir o build |

A interface ainda possui funções sobrescritas por módulos posteriores. Procure a definição **e** as atribuições, como `openCat=function...`. A definição mais recente é a usada pelo site. Ao mudar uma função, use `rg -n 'nomeDaFuncao' public backend tests` para localizar os consumidores.

## 2. Ordem de carregamento e arquivos novos

Leia os `<script>` de `public/index.html`: a ordem faz parte do funcionamento. `documents-privacy.js` vem depois dos demais módulos e chama `boot()` uma única vez. Essa função lê a sessão e os dados antes de abrir a tela.

Para incluir JavaScript:

1. Crie o arquivo em `public/` com nome descritivo.
2. Adicione o `<script src="arquivo.js?v=1"></script>` em `index.html` **antes do módulo que chama `boot()`**, depois das funções das quais ele depende.
3. Inclua o arquivo nas listas de scripts dos testes da interface.
4. Evite criar outro `boot()`, outro cliente HTTP ou controles de permissão apenas no navegador.
5. Reconstrua a imagem Docker e confira a página carregada.

Para incluir CSS, adicione um `<link rel="stylesheet" href="arquivo.css?v=1">` no `<head>`. Regras posteriores podem substituir regras anteriores. Para incluir Python, crie um módulo em `backend/`, importe-o onde for usado e acrescente testes das regras relevantes. Não adicione arquivos de dados pessoais dentro de `public/`: tudo nessa pasta pode ser servido ao visitante.

## 3. Imagens e anexos: onde ficam

Existem duas situações diferentes:

| Tipo | Armazenamento | Como alterar |
| --- | --- | --- |
| Logo e fotos ilustrativas | Arquivos em `public/assets/` e dentro da imagem Docker | Substituir o arquivo, ajustar a referência e reconstruir a imagem |
| Fotos enviadas no cadastro | Conteúdo binário em `anexos.bin_conteudo` no PostgreSQL | Enviar pela tela de fotos; não copiar para uma pasta |
| Vídeo da residência e termo assinado | Mesma tabela `anexos`, vinculados à candidatura | Enviar pelo fluxo autorizado da candidatura |
| PDF gerado da ficha ou do termo | Memória da API durante o pedido | Salvar ou imprimir pelo visualizador; não é arquivado automaticamente |

O upload recebe base64 em JSON, decodifica, confere tamanho e assinatura inicial do formato e grava bytes em `bytea`. São aceitos JPEG/PNG para fotos, MP4/WebM para vídeo e PDF para termo, até 8 MB por arquivo e até dez arquivos de cada tipo por registro. A assinatura inicial não é uma varredura antivírus nem uma validação completa do arquivo.

`anexos` guarda nome, tipo de mídia, tipo de vínculo, data e FK para gato ou candidatura. `fotos_gatos` aponta para a foto atual do gato. Fotos anteriores continuam como anexos. O backup PostgreSQL inclui esses bytes; não existe uma pasta separada de uploads para copiar.

`GET /api/attachments/{id}` confere acesso antes de servir o arquivo. Somente a foto atual de um gato disponível pode ser pública. Vídeos e termos exigem a responsável ou o token privado da candidatura. Não transforme esse endpoint numa listagem pública. Comprovantes antigos de vacina podem conter apenas o nome do arquivo; isso não significa que haja um arquivo armazenado.

O vídeo exige autorização específica registrada pela pessoa candidata. Recusar o vídeo permite combinar uma visita. Revogar a escolha bloqueia novos envios; pedidos sobre vídeos antigos são tratados manualmente pela equipe.

## 4. Relatórios e termo de adoção

Na ficha interna do gato, **Gerar ficha completa (PDF)** abre `/api/cats/{id}/report.pdf`. Somente a responsável pode gerar. O PDF inclui cadastro, resgate, foto atual, vacinas, tarefas, prontuário, localização de aplicações, candidaturas vinculadas, entrevistas, acompanhamentos, devoluções e a relação dos anexos. Vídeos e arquivos originais não são incorporados.

Esta ficha contém dados pessoais de candidatos e voluntários. Não a entregue como documento público. Para a pessoa adotante, use o histórico específico da candidatura, que já limita os dados ao contexto daquela adoção.

Na candidatura aprovada, com gato vinculado e sem devolução, **Gerar e imprimir termo de adoção** abre `/api/adoptions/{id}/term.pdf`. O modelo é preenchido com os dados das partes e do gato, inclui ciência de privacidade, a escolha separada do vídeo e campos de assinatura. Revise o texto, imprima, colha as assinaturas e anexe a cópia digitalizada. Gerar ou imprimir não assina nem conclui a adoção.

O layout fica em `backend/reports.py`: margens, fontes, cabeçalho, logo, cores, seções e rodapé. As cláusulas ficam em `backend/templates/termo_adocao.json`. Altere a versão do modelo ao revisar suas cláusulas. Gere exemplos, renderize os PDFs e confira todas as páginas, inclusive registros longos. Os modelos foram preparados para revisão da responsável e adequação jurídica ao funcionamento real do gatil.

## 5. Manutenção do PostgreSQL

O banco do Docker persiste no volume `postgres_data`. `docker compose down` mantém o volume. Remover o volume apaga o banco. `SEED_DEMO=false` não exclui gatos já inseridos. Editar o seed não altera registros existentes.

O esquema tem nomes em português e prefixos de três letras: `cod_`, `txt_`, `num_`, `dat_`, `hor_`, `flg_`, `bin_`. Datas usam `date` ou `timestamptz`; horários usam `time`; valores lógicos usam `boolean`. FKs e índices únicos fazem parte das regras, como reserva única, dose única e devolução única.

Não há arquivos ou tabela de histórico de migrações, por escolha do projeto. `initialize_database()` usa `backend/schema.sql` somente quando o banco está vazio. Num banco existente, confere tabelas e colunas e não reaplica o esquema.

Ao adicionar um campo ou tabela:

1. Faça backup e trabalhe primeiro numa cópia de teste.
2. Atualize `backend/schema.sql`, mantendo o esquema completo para instalações novas.
3. Planeje e execute o SQL equivalente no banco já existente, por exemplo `ALTER TABLE ... ADD COLUMN ...`; confira nulabilidade, valores anteriores, FK e índice.
4. Atualize `backend/naming.py` quando a coluna participar das respostas ou gravações genéricas. Instantes em milissegundos têm conversão em `EPOCH_FIELDS`.
5. Atualize consultas, validação, permissões, tela e testes.
6. Só então publique uma API que dependa da nova estrutura.

Não execute todo `schema.sql` sobre um banco preenchido. Não recrie tabelas para acrescentar campos. Não renumere gatos nem troque IDs usados por FKs. Para corrigir dados, prefira os fluxos do site e preserve históricos. Uma correção direta deve usar parâmetros, transação, filtro pelo ID correto e conferência do resultado.

Para abrir o console SQL local:

```powershell
docker compose exec db psql -U peticas -d peticas
```

Exemplos de inspeção, sem alteração:

```sql
\dt
\d gatos
SELECT cod_identificador, txt_nome, txt_situacao FROM gatos ORDER BY cod_identificador;
SELECT pg_size_pretty(pg_database_size(current_database()));
```

## 6. Backup e teste de restauração

Não confunda commit com backup: o Git não guarda os registros, fotos ou vídeos do PostgreSQL. O dump contém dados pessoais; restrinja o acesso, proteja o arquivo e guarde uma cópia segura fora da máquina. A pasta `backups/` e arquivos `.dump` ficam fora do Git.

Para gerar um backup sem redirecionar bytes pelo PowerShell:

```powershell
New-Item -ItemType Directory -Force backups
docker compose exec -T db pg_dump -U peticas -d peticas -Fc -f /tmp/peticas-backup.dump
docker compose cp db:/tmp/peticas-backup.dump backups/peticas-AAAAMMDD-HHMM.dump
docker compose exec -T db pg_restore --list /tmp/peticas-backup.dump
```

Use um nome real com data/hora e confira se os comandos terminaram sem erro. O backup inclui anexos binários. Uma cópia vazia ou um arquivo que não foi testado não comprova recuperação.

Para testar uma restauração, use um banco separado, nunca o banco ativo:

```powershell
docker compose exec -T db createdb -U peticas peticas_restauracao_teste
docker compose exec -T db pg_restore -U peticas --no-owner --exit-on-error -d peticas_restauracao_teste /tmp/peticas-backup.dump
docker compose exec -T db psql -U peticas -d peticas_restauracao_teste -c "SELECT count(*) FROM gatos;"
```

Se o banco de teste já existir, escolha outro nome antes de criar. Confira também usuários, candidaturas, prontuários e leitura dos anexos. Para restaurar o banco real, planeje a interrupção dos serviços, confirme o destino e preserve um backup anterior. Esses comandos de teste não substituem essa decisão.

## 7. Privacidade e atendimento de pedidos

Consulte [PRIVACIDADE_LGPD.md](PRIVACIDADE_LGPD.md). Em **Doações e avisos**, a responsável informa nome legal, identificação documental para os termos, endereço, canal público e política de guarda. O documento de identificação da responsável não é exposto pelo aviso público.

O site oferece o aviso antes da conclusão da candidatura. A ciência é separada da autorização opcional para vídeo. `registros_privacidade` guarda o texto apresentado, versão, escolhas e data. Mudar a versão não cria aceite retroativo em candidaturas antigas. A versão é derivada do texto e muda ao alterar o aviso.

O formulário público de pedidos guarda protocolo, nome, e-mail, tipo e descrição em `solicitacoes_privacidade`. A responsável vê a fila nas configurações e registra situação e providências. Não há envio automático de resposta por e-mail, exclusão automática, verificação automática de identidade ou decisão automática sobre o direito solicitado.

## 8. Testar, publicar e commitar

```powershell
node --test tests/interface.test.mjs
docker compose build
docker compose run --rm --no-deps -T api python -c "import os,pytest; os.environ['PETICAS_TEST_DATABASE_URL']=os.environ['DATABASE_URL']; raise SystemExit(pytest.main(['backend/tests','-q','-p','no:cacheprovider']))"
docker compose up -d
docker compose ps
```

Os testes Python criam esquemas isolados. Configure banco destinado a testes; a ausência de `PETICAS_TEST_DATABASE_URL` faz os testes integrados serem ignorados, não aprovados.

O Docker copia os arquivos para a imagem. Editar o arquivo no computador e recarregar o navegador não atualiza o contêiner: reconstrua e recrie o serviço. Mudanças em `.env` também exigem recriação do serviço. `docker compose restart` apenas reinicia o contêiner existente.

Antes de commitar, execute `git diff --check`, confira `git status --short`, selecione somente o trabalho realizado e revise `git diff --cached`. Não inclua `.env`, dumps, dados pessoais nem documentos gerados. Toda alteração de código do agente deve ser commitada; envio ao remoto exige pedido do usuário.

## 9. Problemas comuns

| Sintoma | Conferir |
| --- | --- |
| Compose exige `POSTGRES_PASSWORD` | Valor no `.env`, sem expor a senha em logs |
| Dockerfile não encontrado | `build.context: .` e `build.dockerfile: backend/Dockerfile` |
| Mudança não aparece | Imagem reconstruída, contêiner recriado e script incluído na ordem correta |
| “Banco incompleto” | SQL da nova estrutura aplicado ao banco existente, sem apagar as tabelas |
| 403 numa ação | Papel e permissões conferidos no servidor; não basta mostrar o botão |
| 409 ao salvar | Outro registro mudou; recarregar antes de tentar novamente |
| 413 num anexo | Arquivo dentro do limite de 8 MB |
| Vídeo bloqueado | Escolha de consentimento da candidatura no link privado |
| Medicação sem localização | Permissão do navegador e serviço de localização; não simular coordenadas |
| Termo não disponível | Candidatura aprovada, gato vinculado, sem devolução e sessão da responsável |
| WhatsApp não envia | [Configuração do gateway](WHATSAPP.md), destinatários, modo de simulação e confirmação real |

Para diagnosticar, comece por `docker compose ps` e logs do serviço envolvido. Compartilhe apenas o trecho necessário, removendo tokens, contatos e dados pessoais. Não publique prints de entrevistas ou arquivos privados como evidência de um erro.
