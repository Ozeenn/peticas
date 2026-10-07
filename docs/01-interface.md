# Interface: como o JavaScript monta o site

[Voltar ao guia](README.md) · [Servidor e dados](02-servidor-e-dados.md) · [Manutenção](03-manutencao.md)

## 1. O HTML inicial é uma base pequena

`public/index.html` carrega três CSS e quatro scripts. O corpo contém `#app`, onde o conteúdo é desenhado, `dialog#modal`, usado pelos formulários e detalhes, e `#toast`, usado para mensagens curtas.

Os scripts são clássicos, sem `type="module"`. Por isso compartilham identificadores no ambiente global da página e os atributos HTML como `onclick="go('stock')"` conseguem chamar funções pelo nome. No servidor, ao contrário, os arquivos `.mjs` usam módulos com `import`/`export`.

Ordem obrigatória atual:

```text
app.js
  → management.js
    → community.js
      → interview-lookup.js
        → boot()
```

`boot()` só é chamado no fim do último script, depois que todas as substituições foram instaladas. Não coloque uma segunda chamada em `management.js`: isso pode iniciar carregamentos antes que as versões finais de `loadData` e `render` existam.

## 2. Por que há funções com o mesmo nome?

O projeto evoluiu por camadas. `app.js` preserva a implementação original do protótipo. Outros arquivos guardam uma referência à função existente e atribuem uma nova função ao mesmo nome.

Exemplo real, simplificado para destacar o mecanismo:

```javascript
const previousPublicPage = publicPage;
publicPage = function () {
  return previousPublicPage() + '<section>Conteúdo adicional</section>';
};
```

`previousPublicPage` continua apontando para a função anterior. `publicPage` passa a apontar para a nova. Se a nova versão chamar `publicPage()` dentro dela mesma, em vez da referência guardada, poderá entrar em recursão sem fim.

Isso não é herança de classes nem um sistema de componentes. É substituição de funções. Funciona, mas exige ler as camadas na ordem de carregamento.

| Função | Evolução relevante |
| --- | --- |
| `render` | Base visual → controle de sessão e telas de gestão → recuperação de senha → restrições de voluntários/guia → consulta interna por CPF → redirecionamento público de `#lookup` |
| `adminShell` | Estrutura base → menus de estoque/equipe e nome da conta → Minha conta → restrições e guia → botão Consultar entrevista |
| `loadData` | Gatos ou dados internos → prontuário → guia interno |
| `publicPage` | Página original → informações públicas de visitas, adoção, voluntariado e campanhas |
| `trackingPage` | Linha do tempo original → uso de token real → formulário público de CPF quando não há token na URL |
| `drawForm` | Formulário original → envio real e texto de privacidade → tipo e limites dos campos de idade e telefone |
| `authPage` | Login/cadastro → recuperação → cadastro público limitado à instalação |
| `openApplication` | Entrevista da responsável → formulário para vincular CPF |
| `healthPage` | Cuidados antigos → prontuário novo, preservando os antigos em uma seção expansível |
| `stockPage`, `itemsTable`, `purchasesPage` | Conteúdo de estoque → retirada dos botões não permitidos a voluntários |

Funções como `saveCat`, `saveCare`, `saveVaccine`, `toggleMed`, `saveGuidance`, `decideApplication` e `nextForm` são substituídas por versões que chamam o servidor. As primeiras versões presentes em `app.js` manipulam dados demonstrativos. Alterar apenas essas versões antigas pode não afetar o fluxo final.

## 3. Inicialização e carregamento

`boot()` faz `GET /api/session`. A resposta informa a conta, quando existe, e se a instalação ainda permite criar a primeira responsável. Em seguida chama a versão final de `loadData()`:

| Condição | Requisições e estado |
| --- | --- |
| Visitante ou conta sem acesso ativo | Carrega `/api/cats`, zera vacinas, medicamentos, candidaturas e estoque no navegador |
| `admin` ou `staff` | Carrega `/api/state` e `/api/inventory` em paralelo; depois `/api/medical` e `/api/volunteer-guide` pelas extensões |

Depois define `ready=true`, interpreta a URL e desenha a página. Se houver `#tracking/TOKEN`, chama `loadTracking` para obter a candidatura correspondente. Uma falha de inicialização mostra a tela “Não foi possível carregar”.

`Promise.all` agrupa os dois pedidos iniciais internos: ambos precisam terminar para a continuação. Não existe cache persistente desses arrays no navegador. Atualizar a página exige novo carregamento.

## 4. Navegação por hash

O trecho depois de `#` é controlado pelo navegador e não é enviado ao servidor como caminho HTTP. `/#tracking` carrega o mesmo HTML de `/#stock`. O código lê `location.hash` e decide o conteúdo.

| Hash | Tela e acesso esperado |
| --- | --- |
| vazio / `#public` | Página pública de adoção |
| `#tracking` | Consulta pública por CPF |
| `#tracking/TOKEN` | Acompanhamento individual pelo token |
| `#login` | Login da equipe |
| `#register` | Primeira responsável, quando `setupRequired` |
| `#forgot` | Recuperação por código privado |
| `#overview`, `#cats`, `#applications` | Gestão da responsável |
| `#stock` | Estoque para responsável e voluntários, com ações diferentes |
| `#health` | Prontuário e cuidados |
| `#team` | Equipe e fichas; dona deve abrir pelo botão que chama `loadTeam()` |
| `#account` | Senha e recuperação da própria conta |
| `#guide` | Orientações internas |
| `#lookup` | Consulta interna de status; visitante é redirecionado para `#tracking` |

`go(v)` atualiza a variável `view`, limpa filtros gerais, modifica o hash, chama `render()` e rola para o topo. Existe também um listener de `hashchange`. Isso pode causar mais de um redesenho na mesma navegação; não se deve colocar gravações no banco dentro de uma função de renderização.

Restrições visuais são conveniência. A segurança efetiva continua no backend, pois qualquer pessoa pode escrever uma URL ou enviar HTTP sem usar os botões.

## 5. Estado do navegador

| Grupo | Variáveis importantes | Observação |
| --- | --- | --- |
| Gatil | `cats`, `vaccines`, `meds`, `applications` | Dados substituídos ao carregar a API |
| Navegação | `view`, `healthTab`, `query`, `filter`, `ageFilter` | Escolha de tela e filtros |
| Entrevista | `formStep`, `formData`, `selectedCat`, `trackingId` | Respostas ainda não enviadas ficam só na memória |
| Sessão | `account`, `setupRequired`, `ready` | `account` não contém a senha nem o token de sessão |
| Estoque | `stock`, `stockTab`, `stockQuery`, `stockCategory`, `stockStatus` | `stock` reúne itens, compras, movimentos e notificações |
| Concorrência | `stateVersion`, `item.version`, `application.version` | Precisam acompanhar a gravação |
| Equipe | `team` | Carregada por `loadTeam()` |
| Saúde | `medicalRecords`, `medicalCat` | Histórico e filtro selecionado |
| Orientações | `internalGuide` | Carregado somente para conta ativa |

**Detalhe de manutenção:** `applications` serve tanto à listagem administrativa quanto ao acompanhamento individual. `loadTracking` substitui esse array por uma candidatura. Uma evolução futura deve separar esses estados, para a consulta individual não interferir na listagem interna até a próxima recarga.

## 6. HTML produzido por funções

`publicShell` e `adminShell` são molduras. `publicPage`, `stockPage`, `healthPage` e demais funções retornam strings HTML. `render` coloca esse texto em `#app.innerHTML`. `showModal` monta o conteúdo do diálogo e usa `showModal()` do elemento nativo; `closeModal` o fecha.

`map(...).join('')` transforma uma lista de objetos em uma lista de cartões ou linhas. `filter` seleciona os elementos. `find` procura um único registro. `esc` substitui caracteres especiais por entidades HTML; use-o para valores vindos de usuários antes de inseri-los no HTML. Ele não é uma autorização nem uma validação de URL.

O redesenho com `innerHTML` destrói os elementos antigos e os listeners conectados a eles. Por isso `bindFilters()` e `bindStock()` precisam ser chamados para elementos recém-criados. Referências antigas ao DOM podem deixar de existir enquanto uma resposta de rede chega; `lookupOwnApplication` já usa `result.isConnected` para evitar atualizar um resultado removido.

## 7. Comunicação e tratamento de erros

Há duas funções chamadas `api`, mas em ambientes separados:

* `public/management.js`: cliente HTTP, chama `fetch('/api/' + path, ...)`.
* `server/worker.mjs`: roteador do servidor, decide o que fazer com o pedido.

O cliente envia JSON e `credentials: 'same-origin'`, para o navegador encaminhar o cookie de sessão. Lê JSON da resposta e lança `Error` se o status não for bem-sucedido. Uma resposta 401 de uma operação diferente de login limpa a conta local e redesenha a interface.

`submit(e, action)` é a função comum dos formulários. Executa `preventDefault()`, desabilita o botão, cria um objeto com `FormData`, chama `action`, mostra erros por `formError` e reabilita o botão no `finally`. Atenção: valores de formulários geralmente são strings. `saveMedical` converte `catId` para número; o backend também precisa validar tipos.

`toast` é feedback temporário, enquanto `formError` deixa a mensagem no formulário. Não capture um erro e mostre mensagem de sucesso em seguida. O polling de estoque tem um `catch {}` silencioso: falhas nele não são necessariamente mostradas ao usuário.

## 8. Fluxos de interface

### Adoção

`startForm` limpa o formulário e abre a primeira etapa. `questions` define os campos básicos; `community.js` acrescenta CPF, idade, telefone, profissão, motivação, vacinação, exames, renda, alimentação e origem do contato. Cada campo usa uma tupla `[chave, rótulo, tipo, opções]`.

`nextForm` e `backForm` guardam os valores em `formData`. Ao finalizar, `nextForm` envia `{cat, answers}` para `/api/adoptions`. O servidor devolve o token pessoal uma vez; a interface monta `location.origin + '/#tracking/' + token` e orienta o usuário a guardar o link. Fechar ou recarregar a página antes de enviar perde as respostas ainda locais.

Há referências explícitas à etapa de índice `4` em várias funções. Adicionar uma sexta etapa exige revisar essas condições, não apenas fazer `questions.push(...)`.

### Consulta por CPF

`trackingPage` desenha o formulário público quando o hash não contém token. `lookupOwnApplication` envia CPF no corpo de `POST /api/tracking/cpf`, apresenta etapa/data e uma explicação genérica escrita no frontend. **Essa explicação não é a orientação privada `guidance` armazenada pela dona.**

`lookupInterview` usa `/api/adoptions/lookup` na área interna. `linkApplicationCPF` permite à dona vincular CPF a uma candidatura antiga, passando sua versão. As duas consultas não oferecem busca parcial por nome ou CPF.

### Voluntários

`volunteerFields` descreve a ficha. `newVolunteer` cria o formulário; `createVolunteer` chama `POST /api/users`; `volunteerProfile` lê a ficha restrita à dona. `setRole` ativa/desativa acesso e o servidor revoga sessões. O guia combina conteúdo geral com informações recebidas da API autenticada; não copie informações internas para strings de um arquivo público.

### Saúde

`medicalForm` aceita quatro tipos: tratamento, aplicação, evolução e encerramento. `saveMedical` envia o evento e recarrega `/api/medical`. A aplicação aponta para o tratamento por `treatmentId`; ela não altera a linha do tratamento. `healthPage` identifica encerrados pela existência de um evento `completion` e monta a linha do tempo.

Os arrays antigos `vaccines` e `meds` continuam existindo e aparecem separadamente. Eles não foram convertidos automaticamente para o novo prontuário. Voluntários os veem como leitura; a responsável ainda tem os controles legados.

### Estoque e notificações

`itemForm` trata o cadastro do item. `movementForm` cria o identificador da movimentação quando abre o formulário; um novo clique de envio do mesmo formulário reutiliza esse identificador. `purchaseForm` agenda e `finishPurchase` recebe ou cancela. `restrictStock` retira botões da string HTML para contas que não são admin.

O intervalo de 60 segundos busca estoque quando há conta ativa e a aba está visível. Não é um serviço de envio de mensagens e não roda depois que o navegador é fechado. `historyPage` apresenta no máximo os 100 movimentos retornados pela API.

## 9. CSS, imagens e responsividade

A ordem de CSS é `styles.css → peticas-theme.css → management.css`. Uma regra posterior pode prevalecer se tiver especificidade equivalente. No DevTools, a aba **Computed/Calculado** mostra o valor efetivo e **Styles/Estilos** mostra regras sobrescritas.

As variáveis `--navy`, `--pink`, `--cyan`, `--yellow`, `--ink`, `--muted`, `--line`, `--bg`, `--green` e `--radius` centralizam parte do visual. Nem todas as cores são variáveis: o tema também tem cores literais.

| Família de classes | Uso |
| --- | --- |
| `.shell`, `.sidebar`, `.topbar`, `.content` | Estrutura da área interna |
| `.public-header`, `.public-main`, `.hero`, `.footer` | Estrutura pública |
| `.panel`, `.panel-head`, `.row`, `.row-main` | Blocos e listas |
| `.btn`, `.secondary`, `.soft`, `.small`, `.pink` | Botões e variações |
| `.cats`, `.cat`, `.cat-image`, `.tags`, `.badge` | Cartões de gatos e status |
| `.filters`, `.tabs`, `.table-wrap` | Busca, abas e tabelas |
| `.form-grid`, `.form-actions`, `.modal-body`, `.form-error` | Formulários, diálogos e erros |
| `.timeline`, `.timeline-item`, `.track` | Acompanhamento de adoção |
| `.stock-actions`, `.stock-summary`, `.unread-row` | Gestão do estoque |
| `.community-section` | Conteúdo adicionado de visitas e voluntariado |

Os principais breakpoints são 1450px, 1100px e 720px, com ajustes comunitários também em 600px. No celular, o menu interno vira navegação horizontal e diversas grades passam a uma coluna. Tabelas permitem rolagem horizontal.

`photos` em `app.js` é uma lista de três caminhos. `cat.photo` é um índice nessa lista, não uma URL nem arquivo enviado pelo usuário. `brand()` usa a logo estática. As fontes DM Sans e Manrope vêm de Google Fonts por `@import`; o CSS define fallback `sans-serif`.
