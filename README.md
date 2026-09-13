# Peticas — gestão e adoção

HTML/CSS/JavaScript e API Cloudflare Worker. SQLite local e Cloudflare D1 (SQLite gerenciado) no Sites.

## Uso local

Requer Node.js 24 e pnpm. Execute `pnpm install`, copie `.env.example` para `.env`, defina `ADMIN_SETUP_KEY` com uma chave aleatória longa e execute `pnpm dev`. Abra http://127.0.0.1:4173. Banco em `data/peticas.sqlite`, com migrações automáticas no servidor local. Nunca publique `.env` ou `data/`.

## Primeiro acesso

Área da equipe → Criar conta. A primeira responsável informa a chave privada de instalação e define seu próprio e-mail e senha. Demais cadastros ficam pendentes e são aprovados em Equipe. A chave não permite criar outra responsável. Troca de senha autenticada em Minha conta; recuperação por e-mail ainda não configurada.

## Implementado

- Estoque por categoria/unidade, saldo em milésimos, quantidade mínima e observações.
- Entradas, saídas e ajustes com motivo, usuário e data. Proteção contra concorrência e repetição de movimentação.
- Compras agendadas, cancelamento e recebimento atômico, sem duplicar o saldo.
- Alertas internos de falta, estoque baixo e compras previstas/vencidas. Consulta ao abrir a gestão e a cada minuto enquanto aberta. Leitura individual e resolução por reposição.
- Login próprio, scrypt com sal aleatório, cookies HttpOnly/Secure/SameSite, sessão revogável, verificação de origem e limite de tentativas.
- Responsável aprova acessos e edita gatos, cuidados e candidaturas. Equipe autorizada consulta e gerencia estoque/compras. APIs internas protegidas no servidor.
- Persistência de gatos, vacinas, medicamentos e candidaturas. Os seis gatos iniciais ainda são exemplos fictícios do esboço.
- Acompanhamento da candidatura por token aleatório, guardado como hash no banco.

## Limites desta entrega

Notificações aparecem dentro do sistema. Não há envio de WhatsApp/e-mail ou compras/pagamentos automáticos. Fotos/vídeos de candidatos seguem pelo WhatsApp. Carteirinhas de vacinação guardam apenas o nome do arquivo, sem upload real. Não há verificação ou recuperação de e-mail.

## Verificação e publicação

`pnpm test`: testes integrados com SQLite real. `pnpm build`: gera Worker, assets e migrações. `public/` é a fonte da interface; `server/` contém a API; `drizzle/` contém migrações versionadas e imutáveis após publicação. A hospedagem aplica as migrações antes do Worker.

Logo fornecida pelo usuário. Fotos ilustrativas: River Fx, Sergei Karakulov e Meaghan Cafferty / Unsplash.
