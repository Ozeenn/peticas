# Peticas — gestão e adoção

HTML/CSS/JavaScript e API Cloudflare Worker. SQLite local e Cloudflare D1 (SQLite gerenciado) no Sites.

## Uso local

Requer Node.js 24 e pnpm. Execute `pnpm install`, copie `.env.example` para `.env`, defina `ADMIN_SETUP_KEY` com uma chave aleatória longa e execute `pnpm dev`. Abra http://127.0.0.1:4173. Banco em `data/peticas.sqlite`, com migrações automáticas no servidor local. Nunca publique `.env` ou `data/`.

## Primeiro acesso

Área da equipe → Criar conta (somente durante a instalação). A primeira responsável informa a chave privada de instalação e define seu próprio e-mail e senha. Depois disso, o cadastro público fica bloqueado: somente a responsável cadastra voluntários em Equipe, com ficha e aceite do termo. Contas antigas pendentes podem ser liberadas pela responsável. Troca de senha autenticada em Minha conta; recuperação por e-mail ainda não configurada.

## Implementado

- Estoque por categoria/unidade, saldo em milésimos, quantidade mínima e observações.
- Entradas, saídas e ajustes com motivo, usuário e data. Proteção contra concorrência e repetição de movimentação.
- Compras agendadas, cancelamento e recebimento atômico, sem duplicar o saldo.
- Alertas internos de falta, estoque baixo e compras previstas/vencidas. Consulta ao abrir a gestão e a cada minuto enquanto aberta. Leitura individual e resolução por reposição.
- Login próprio, scrypt com sal aleatório, cookies HttpOnly/Secure/SameSite, sessão revogável, verificação de origem e limite de tentativas.
- Responsável cadastra voluntários, gerencia acessos, gatos, itens, compras e candidaturas. Voluntários registram tratamentos/aplicações/evoluções, movimentam o saldo de itens existentes e consultam o status de entrevistas por CPF completo. Não acessam respostas, fichas pessoais, criação/edição de itens nem operações de compras. APIs internas protegidas no servidor.
- Prontuário por gato com início e fim previsto do tratamento, medicamento, dose, frequência e referência da prescrição, aplicações datadas, responsável autenticado, evolução e encerramento. Histórico somente de acréscimo; correções são novas evoluções. Registros anteriores ficam disponíveis na seção de registros anteriores.
- CPF validado na candidatura e busca exata limitada a 20 consultas por conta a cada 15 minutos. A busca retorna somente etapa e data. Índice usa hash com segredo aleatório persistido no banco. A responsável pode vincular CPF em candidaturas antigas; sem vínculo, elas não aparecem na busca. Respostas completas (inclusive CPF) ficam apenas na área da responsável.
- Página pública com endereço, telefone comercial, mapa, adoção responsável, clínica parceira, voluntariado, bazar, show de prêmios e Cat Café. Visitas: quarta das 16h às 19h e sábado das 10h às 12h. Na ausência dos links específicos, as campanhas direcionam a uma consulta no WhatsApp comercial. Grupo e instruções de entrada são entregues somente pela API autenticada.
- Persistência de gatos, vacinas, medicamentos e candidaturas. Os seis gatos iniciais ainda são exemplos fictícios do esboço.
- Acompanhamento da candidatura por token aleatório, guardado como hash no banco.

## Limites desta entrega

Notificações aparecem dentro do sistema. Não há envio de WhatsApp/e-mail ou compras/pagamentos automáticos. Fotos/vídeos de candidatos seguem pelo WhatsApp. Carteirinhas de vacinação guardam apenas o nome do arquivo, sem upload real. Não há verificação ou recuperação de e-mail.

## Verificação e publicação

`pnpm test`: testes integrados com SQLite real. `pnpm build`: gera Worker, assets e migrações. `public/` é a fonte da interface; `server/` contém a API; `drizzle/` contém migrações versionadas e imutáveis após publicação. A hospedagem aplica as migrações antes do Worker.

As migrações 0001 e 0002 acrescentam prontuários e índice de CPF sem apagar registros existentes. A interface carrega app.js, management.js, community.js e interview-lookup.js nesta ordem; o último inicia a sessão após registrar todos os fluxos.

Adotantes podem consultar o próprio CPF em Minha candidatura (`/#tracking`), sem login. A API pública `POST /api/tracking/cpf` aceita CPF completo válido e retorna somente data e etapa, sem nomes, respostas, orientações privadas ou tokens. Limite de 10 tentativas por IP a cada 15 minutos e validação de origem. A consulta por CPF não comprova identidade; o link individual continua disponível para orientações da equipe. Entrevistas antigas precisam ter o CPF vinculado pela responsável.

Logo fornecida pelo usuário. Fotos ilustrativas: River Fx, Sergei Karakulov e Meaghan Cafferty / Unsplash.

Recuperação de senha: use Esqueci minha senha com e-mail e código privado. Minha conta permite gerar um código mediante confirmação da senha atual. No primeiro uso do administrador, a chave ADMIN_SETUP_KEY serve como código inicial. Cada redefinição invalida o código anterior e todas as sessões; o novo código é mostrado uma vez. Apenas o hash do código fica em settings. Não há envio de e-mail nesta versão. O banco SQLite local e o D1 de produção são independentes.
