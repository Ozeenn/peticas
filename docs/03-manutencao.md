# Manutenção, testes, publicação e diagnóstico

[Voltar ao guia](README.md) · [Interface](01-interface.md) · [Servidor e banco](02-servidor-e-dados.md)

## 1. Um ciclo de manutenção pequeno e verificável

1. Descreva o problema com uma ação concreta: “ao salvar uma saída, o saldo não muda”.
2. Reproduza no ambiente local com dados de teste.
3. Descubra qual função da tela é executada e qual rota ela chama.
4. Confira a versão final da função, procurando também suas redefinições.
5. Altere a menor parte que explica o comportamento.
6. Execute um teste relevante e confira a tela afetada.
7. Revise o diff, atualize a documentação se a regra mudou e só então prepare a publicação.

Não misture uma alteração de texto, uma refatoração de login e uma migração de banco na mesma manutenção se elas não dependem uma da outra. Mudanças menores são mais fáceis de entender e reverter.

Comandos de pesquisa, executados na raiz:

```powershell
rg -n 'saveMovement|movementMatch' public server
rg -n 'trackingPage|lookupOwnApplication' public
rg -n 'ADMIN_SETUP_KEY|requireAdmin' server
git diff --stat
git diff -- public/community.js
```

O índice complementar aponta funções e linhas da versão analisada. Após alterações, a linha pode mudar: pesquise pelo nome antes de editar.

## 2. Receitas de mudanças comuns

### Alterar endereço, telefone ou horário

Abra `public/community.js`. O conteúdo público está na extensão de `publicPage`; o WhatsApp comercial é construído por `contactLink`. Há também telefone em `tel:`, endereço usado no link do mapa e horários em textos de visitas, Cat Café e voluntariado. Procure todas as ocorrências para não deixar informações divergentes.

```powershell
rg -n '99661|Santana|10h|12h|16h|19h' public
```

Mude os dados, recarregue o site local e confira texto e destino dos links. Não é necessário alterar o banco para esses textos. Informações de entrada/grupo vêm da rota autenticada em `worker.mjs`, não de `publicPage`; não mova esse conteúdo para arquivos públicos.

### Trocar uma imagem

As fotos atuais estão em `public/assets/`; seus caminhos estão em `photos` de `app.js`. Para substituir mantendo o mesmo nome, troque o arquivo e confira a imagem. Para acrescentar, atualize a lista e a forma de escolher o índice `cat.photo`. O formulário atual de gato não permite upload nem escolha completa de fotos, portanto colocar um arquivo na pasta não cria sozinho uma funcionalidade de envio de imagem.

Não use `server/seed.json` como forma de atualizar um gato já cadastrado: `getState` faz `INSERT OR IGNORE`, preservando o estado existente. Alterações do seed afetam instalações ainda não inicializadas.

### Acrescentar uma pergunta à entrevista

Exemplo didático de campo em `community.js`:

```javascript
questions[1].fields.push([
  'screens',
  'As janelas possuem telas de proteção?',
  'select',
  'Sim|Não|Não se aplica'
]);
```

Use chave composta apenas por letras, como a API exige. `questionLabel` obtém o rótulo da mesma estrutura. A resposta entra em `answers` e não exige nova coluna porque esse conteúdo é JSON.

Se for regra obrigatória, valide também em `POST /api/adoptions`: `required` no HTML é só validação do navegador. Decida o comportamento de candidaturas antigas que não têm o campo. Teste ida/volta entre etapas, envio e leitura pela dona. Caso acrescente uma etapa, revise todos os `formStep===4` e o botão final.

### Acrescentar uma categoria de estoque

Atualize a lista `categories` em `management.js` e as listas permitidas nas rotas POST/PATCH de itens em `worker.mjs`. Como a categoria é texto no banco, uma nova opção não exige necessariamente coluna nova, mas pode exigir conversão de registros se você estiver renomeando uma categoria existente.

Teste o cadastro como admin, os filtros e a rejeição de cadastro por staff. Modificar somente o dropdown causa erro na API; modificar somente a API deixa a opção ausente na tela.

### Mudar permissões

Comece pela rota no servidor. `requireAdmin(user)` impede a ação a quem não é responsável; somente retirar o botão com `restrictStock` não basta. Em seguida ajuste menu, botões e mensagens. Acrescente teste fazendo a chamada HTTP diretamente com cookie de staff. Confira também as respostas GET: uma ação bloqueada não impede vazamento se os dados forem enviados em outra rota.

Não retire o `requireStaff` central para tornar uma operação pública. Crie uma rota pública específica antes dele e selecione explicitamente os campos que podem sair, como foi feito em `/tracking/cpf`.

### Acrescentar um campo ao prontuário

Você precisa revisar `medicalForm` (entrada), `saveMedical` (conversão quando necessária), o conjunto permitido em POST `/medical` (persistência), suas validações e `healthPage` (exibição). Como `data` é JSON, novo campo textual pode não exigir migração; um novo índice de busca ou coluna, sim.

Os registros antigos não terão o campo. Use fallback explícito na tela. Se o dado representa correção de um evento, mantenha a lógica de acrescentar evolução, em vez de sobrescrever silenciosamente o histórico.

### Criar nova coluna/tabela

1. Modifique `db/schema.ts`.
2. Execute `pnpm db:generate`.
3. Leia o SQL novo; verifique defaults, nulabilidade, FKs e impacto em dados existentes.
4. Teste a migração em uma cópia do banco local e teste uma instalação vazia.
5. Atualize as rotas e a interface.
6. Inclua os arquivos SQL e os metadados novos no versionamento.

Adicionar uma coluna `NOT NULL` sem valor para linhas antigas pode impedir a migração. Renomear ou remover coluna pode exigir uma transformação de dados; o gerador não decide sozinho a intenção de negócio.

## 3. Testes existentes e seus limites

`tests/system.test.mjs` usa `node:test`, `assert`, um banco SQLite temporário e `worker.fetch` diretamente. O helper `request` constrói uma requisição HTTPS fictícia, envia JSON/Origin/cookie e lê a resposta. Não abre navegador nem conecta ao banco de produção.

O arquivo contém **um caso integrado longo**, com muitas asserções sequenciais. “1 teste passou” não significa que apenas uma regra foi exercitada, mas também não é uma medição de cobertura total.

Ele cobre, entre outros:

* Primeira responsável com chave, bloqueio de cadastro público posterior e criação de voluntário.
* Rejeição por origem e por perfil, ficha pessoal e guia restritos.
* Estoque em milésimos, saldo insuficiente, conflito de versão e repetição de movimento.
* Avisos, agendamento e recebimento sem somar duas vezes.
* Persistência após fechar/reabrir SQLite.
* Candidatura, token, avanço de etapas e reserva do gato.
* Consulta por CPF com projeção limitada, validação, resultado vazio e limite público.
* Vínculo de CPF somente por admin e conflito de versão.
* Tratamento, aplicação, encerramento e rejeição de aplicação após encerramento.
* Revogação de sessões e recuperação de senha com rotação de código.

Não há testes automatizados de navegador, cobertura percentual configurada, teste de carga, teste de todos os estados terminais nem simulação completa de concorrência entre conexões. Houve verificações manuais de interface durante o desenvolvimento; elas não substituem uma suíte reproduzível.

Para corrigir um bug de API: faça primeiro uma asserção que falha no cenário, aplique a correção e confirme que passa. Evite testes que só repetem literalmente a implementação, como verificar que a string de um botão contém o texto que acabou de escrever.

### Comandos de verificação

```powershell
node --test tests/system.test.mjs
node --check public/app.js
node --check public/management.js
node --check public/community.js
node --check public/interview-lookup.js
node --check server/worker.mjs
node scripts/build.mjs
git diff --check
```

`--check` verifica sintaxe, não executa os fluxos. Build bem-sucedido não prova que a regra de autorização está correta. Use o conjunto apropriado à mudança; uma correção apenas nesta documentação não exige repetir a suíte da aplicação.

## 4. Diagnóstico no navegador

Abra as ferramentas de desenvolvimento (geralmente F12 no navegador de desktop).

| Aba | O que observar |
| --- | --- |
| Console | Erros de JavaScript e arquivo/linha do problema |
| Network/Rede | Método, URL, status, corpo enviado e JSON de resposta |
| Elements/Elementos | HTML atual e classes CSS realmente aplicadas |
| Application/Storage | Cookie da sessão; não copie seu valor para mensagens ou documentos |

Ao salvar uma saída, procure `POST /api/items/.../movements`. Se não houve pedido, investigue o evento/validação do formulário. Se houve 403, investigue origem/perfil. Se houve 409, investigue a versão do item. Se houve 200 mas a tela não mudou, confira a chamada seguinte de inventário e o redesenho.

Evite começar limpando o banco ou alterando as permissões. Primeiro leia a mensagem retornada pelo servidor. O campo `error` geralmente explica a recusa.

## 5. Problemas frequentes

| Sintoma | Causa a investigar | Ação |
| --- | --- | --- |
| Site local não abre | Processo Node encerrado | Inicie `node server/local.mjs` na raiz e mantenha-o ativo |
| Porta ocupada (`EADDRINUSE`) | Outro servidor já está na 4173 | Identifique o processo correto; não encerre todos os processos Node |
| Página abre, gravação dá origem inválida | Uso de localhost ou URL diferente da origem montada | Use `http://127.0.0.1:4173` no ambiente local |
| Mudança no servidor não aparece | Processo ainda usa módulos antigos | Reinicie o servidor local |
| Mudança de tela não aparece | Editou função sobrescrita ou saída de build | Procure redefinições e edite a fonte efetiva |
| “Outra pessoa atualizou…” | Versão desatualizada | Recarregue, confira os dados e refaça a alteração intencionalmente |
| “Muitas tentativas…” | Limite atingido | Aguarde a próxima janela; em testes locais os IPs podem compartilhar `local` |
| CPF não encontra entrevista antiga | `cpf_hash` ausente ou CPF diferente | Dona vincula CPF pelo formulário da candidatura |
| Todos os CPFs deixam de encontrar registros | Segredo de índice alterado/perdido | Restaure o segredo correto ou planeje recálculo consistente dos hashes |
| Conta funciona local, não online | Bancos diferentes | Use o cadastro correto do ambiente; não copie credenciais por suposição |
| Equipe aparece vazia ao abrir hash direto | `team` só é carregado por `loadTeam()` | Abra pelo botão Equipe; melhoria futura: carregar por rota |
| Saldo multiplicado/dividido por 1000 | Confusão entre formulário e banco | Revise `amount` no backend e `quantity` no frontend |
| Aviso não chegou por WhatsApp | Não existe envio automático | O site só oferece links e notificações internas |
| Upload “salvo”, mas arquivo não existe | Campo legado guarda só nome | Implementar armazenamento real é uma funcionalidade nova |
| Build com acesso negado | Permissões do ambiente ao resolver dependências | Execute em terminal com acesso ao projeto/dependências; não altere regras do app para contornar |
| Git acusa propriedade duvidosa | Checkout criado por outro usuário do sistema | Confira o caminho/proprietário antes de marcar apenas esse checkout como confiável |

O servidor local engole a falha ao tentar carregar `.env` (`try/catch` vazio). Se o primeiro cadastro não funciona, confira se a configuração foi realmente carregada, sem imprimir o segredo.

## 6. Backup e restauração

Código e dados exigem backups diferentes. Git guarda fonte e migrações; não guarda automaticamente usuários, candidaturas e estoque. Um deploy novo usa o banco existente, não recria o banco a partir do seu computador.

### Banco local

O SQLite usa WAL: podem existir arquivos `peticas.sqlite-wal` e `peticas.sqlite-shm`. Não copie apenas o `.sqlite` com o servidor escrevendo e suponha que o backup está completo.

Procedimento simples: pare conscientemente o servidor local, mantenha a pasta `data` íntegra e faça uma cópia dela para armazenamento privado. Use uma cópia para ensaiar restauração; nunca substitua o único banco existente sem antes guardar a versão anterior. Alternativamente, um mantenedor pode implementar backup consistente com a API SQLite apropriada.

Verifique a restauração abrindo a cópia, conferindo contagens e executando operações controladas. O teste automatizado fecha/reabre um banco temporário; isso não é teste de restauração do banco real.

### Banco de produção

O código não fornece um comando de backup/exportação/restauração de D1. Use os recursos autenticados da hospedagem para esse banco específico e valide o procedimento em um ambiente apropriado. Não considere a função de leitura de tabelas como backup completo.

Um backup deve incluir dados e os valores de `settings` necessários à operação. Perder `cpf-secret` quebra o índice existente; recuperar somente tabelas de cadastro sem as relações pode quebrar histórico. Controle acesso e retenção: respostas, CPF, endereço e informações de renda podem estar presentes.

### Reverter versão não é desfazer migração

Voltar a um Worker anterior não remove automaticamente colunas nem converte dados novos para o formato antigo. Prefira migrações aditivas e compatíveis quando possível. Antes de reverter, compare os formatos que cada versão consegue ler e escrever.

## 7. Build e publicação

`scripts/build.mjs` executa estas etapas:

1. Cria `dist/client` e copia `public/` para lá.
2. Empacota `server/worker.mjs` em `dist/server/index.js`, formato ESM, alvo ES2022, plataforma browser/Worker.
3. Copia `.openai/hosting.json` para `dist/.openai/hosting.json`.
4. Copia migrações para `dist/.openai/drizzle`.

Não há minificação/bundling dos quatro scripts da interface nesse processo: eles são copiados. O build também não limpa arquivos antigos de `dist/client`. Se remover ou renomear um asset, confira a saída para não manter um arquivo obsoleto no pacote; uma melhoria é limpar apenas diretórios gerados, com caminhos conferidos.

### Configuração de hospedagem

O manifest guarda o ID do Site existente, `d1: "DB"` e `r2: null`. `DB` é o nome lógico que vira `env.DB`; não é o nome de um arquivo local. R2 não está configurado, coerente com a ausência de upload real. Segredos como `ADMIN_SETUP_KEY` ficam na configuração privada da hospedagem, nunca nesse manifest.

O endereço é metadado da hospedagem, não um texto que precise ser trocado em todos os arquivos. Os pedidos usam `/api/...` e os links novos de acompanhamento usam `location.origin`, de modo que seguem o domínio usado no acesso. Links pessoais antigos já enviados não são reescritos pelo código quando o domínio muda; verifique a política de redirecionamento antes de prometer continuidade.

### Fluxo de publicação utilizado

O plugin Sites realiza: obter credencial temporária → reconciliar a fonte → build/checks necessários → commit/push da fonte exata → pacote → salvar versão → publicar → esperar status `succeeded`. A versão publicada nesta base foi a 7. Use o projeto existente; não crie outro Site para uma atualização comum.

O script externo do plugin é `site-workflow.mjs`, sob `scripts/` da instalação de Sites. Ele recebe o ID por argumento e os demais dados por JSON em stdin. A credencial não deve ser gravada em arquivos, parâmetros do shell, URLs de Git ou documentação. O arquivo de pacote precisa corresponder ao commit enviado.

No ambiente Windows desta entrega, o empacotador exigiu o Bash instalado com Git no PATH, em vez de `C:\Windows\System32\bash.exe` que dependia de WSL não configurado. O GNU tar precisou de `TAR_OPTIONS=--force-local` para não interpretar `C:` como máquina remota. Esses ajustes eram do processo de publicação, não do site. A versão/caminho do plugin pode mudar: leia as instruções da instalação atual ao repetir.

O pacote inclui assets, Worker, manifest e migrações; não deve incluir `.env`, `data/`, `node_modules/`, capturas, logs nem documentos pessoais. Não envie o banco local como solução para uma falha de login de produção.

## 8. Limitações observadas e evolução recomendada

Esta seção é uma leitura técnica do código, não uma afirmação de que houve incidente. As correções abaixo **não foram feitas apenas por serem documentadas**.

| Prioridade sugerida | Situação atual | Evolução e critério de conclusão |
| --- | --- | --- |
| Alta | Consulta pública por CPF não autentica identidade | Se for mostrar mais dados, exigir prova adicional; testar que uma pessoa sem token não lê respostas/orientações |
| Alta | Dados pessoais em JSON e ausência de fluxo de retenção/exportação/exclusão | Definir e implementar ciclo de vida dos dados e backup testado; limitar quem pode exportar |
| Alta | Transições terminais de adoção incompletas no servidor | Definir máquina de estados explícita e testar cada transição permitida/proibida |
| Alta | Validação desigual entre HTML e API; alguns formatos inesperados podem causar 500 | Validar esquemas por rota e devolver 400 para payload inválido |
| Média | Funções sobrescritas em cadeia e HTML manipulado por `.replace`/regex | Refatorar por funcionalidade com renderização explícita, mantendo testes dos fluxos |
| Média | Gatos e cuidados antigos em um único JSON com uma versão global | Migrar para tabelas próprias com IDs/FKs e estratégia de conversão/reversão |
| Média | Dados internos de entrada/grupo literais no Worker | Mover para configuração restrita ou cadastro administrável; nunca para `public/` |
| Média | Vários arrays são carregados inteiros; histórico de estoque limitado aos últimos 100 | Paginar listagens e oferecer busca/histórico com filtros server-side |
| Média | Mesma variável `applications` para gestão e acompanhamento | Separar estados; testar ida/volta entre consulta individual e listagem da dona |
| Média | Datas e dados demonstrativos persistem, inclusive algumas datas fixas de 2026 | Remover exemplos por fluxo explícito e validar datas reais antes de uso operacional |
| Média | Sem geração automática de doses, sem baixa de estoque por aplicação | Implementar apenas com regra de negócio definida e transação adequada |
| Média | Idempotência/concorrência não totalmente cobertas por testes paralelos | Criar testes de corrida e comparar o payload de IDs repetidos |
| Baixa | `teamPage` depende do carregamento via botão | Carregar dados no ciclo de entrada da rota, incluindo acesso direto pelo hash |
| Baixa | `rate_limits` e sessões expiradas não têm limpeza | Implementar tarefa de manutenção com retenção definida |
| Baixa | Estilos e handlers inline; arquivos densos em uma linha | Formatar o código e evoluir eventos/módulos gradualmente; revisar CSP antes de ativá-la |

Outros limites importantes: não há recuperação por e-mail, upload de documentos real, cadastro de foto completo, agenda de voluntários no banco, pagamentos, compra automática, integração de mensagens nem gestão de conteúdo pública pela dona. O guia de voluntariado direciona a escala ao WhatsApp. As informações de castração no modal original incluem texto demonstrativo, não laudo individual.

### Ordem prática para refatorar sem perder o sistema

1. Formatar os arquivos em uma alteração exclusivamente de legibilidade.
2. Separar funções puras, estado e chamadas HTTP, mantendo os nomes públicos usados pelos handlers.
3. Substituir uma família de sobrescritas por vez, começando pela consulta de CPF ou estoque.
4. Centralizar regras/labels de permissões e etapas, mantendo o servidor como autoridade.
5. Separar rotas do Worker em módulos com contratos de entrada e saída.
6. Migrar dados estruturais somente depois que os fluxos estiverem cobertos por testes.

Não transforme todos os scripts em `type="module"` de uma vez: os `onclick` atuais deixariam de encontrar funções que não estivessem expostas, e as variáveis hoje compartilhadas precisariam de imports/exports explícitos.

## 9. Roteiro de aprendizagem aplicado

| Sessão | Exercício | O que você deve conseguir explicar ao final |
| --- | --- | --- |
| 1 | Alterar um texto de visita e um espaçamento local | Diferença entre HTML, CSS, fonte e saída de build |
| 2 | Seguir `startForm → drawForm → nextForm` | Estado temporário e coleta de formulários |
| 3 | Observar uma consulta por CPF na aba Network | Método, caminho, JSON, status e limite da resposta |
| 4 | Seguir uma movimentação até o SQL | Validação, milésimos, versão e transação |
| 5 | Ler o teste de bloqueio de staff e acrescentar um cenário | Por que segurança precisa ser testada na API |
| 6 | Criar campo opcional em uma cópia de trabalho | Mudanças coordenadas de entrada, backend e exibição |
| 7 | Ensaiar migração e restauração em banco descartável | Diferença entre versão de código e dados persistentes |

Quando conseguir explicar uma funcionalidade sem recorrer ao código inteiro, escreva esse caminho na documentação. Isso transforma manutenção em uma sequência de decisões compreensíveis, em vez de uma nova rodada de alterações às cegas.
