# Peticas — gestão e adoção

Para entender o código e dar manutenção, comece pela [documentação técnica e trilha de aprendizagem](docs/README.md). Ela descreve a interface, a API, o banco, as permissões, os testes, a publicação e as limitações da implementação atual.

HTML/CSS/JavaScript e API Cloudflare Worker. SQLite local e Cloudflare D1 (SQLite gerenciado) no Sites.

## Uso local

Requer Node.js 24 e pnpm. Execute `pnpm install`, copie `.env.example` para `.env`, defina `ADMIN_SETUP_KEY` com uma chave aleatória longa e execute `pnpm dev`. Abra http://127.0.0.1:4173. Banco em `data/peticas.sqlite`, com migrações automáticas no servidor local. Nunca publique `.env` ou `data/`.

## Primeiro acesso

Área da equipe → Criar conta (somente durante a instalação). A primeira responsável informa a chave privada de instalação e define seu próprio e-mail e senha. Depois disso, o cadastro público fica bloqueado: somente a responsável cadastra voluntários em Equipe, com ficha e aceite do termo. Contas antigas pendentes podem ser liberadas pela responsável. Troca de senha autenticada em Minha conta; recuperação por e-mail ainda não configurada.

## Implementado

O escopo atualizado e as configurações estão em [Alterações após a reunião](docs/06-reuniao-e-implementacao.md).

- Cadastro completo dos gatos, propostas de voluntários e revisão pela responsável.
- Fotos reais; situações disponível, em tratamento, reservado e adotado.
- Cadastro de voluntários exclusivo da responsável, com CPF e permissões individuais; ficha sem acesso ao sistema.
- Formulário de adoção, análise, visita domiciliar, aprovação, reserva e conclusão; consulta por CPF e link individual.
- Motivo de reprovação, termo em PDF, vídeo da residência, acompanhamento após adoção e devolução com histórico preservado.
- Prontuário com prescrição, início/fim, intervalo em horas, aplicações e checklist de doses previstas.
- Histórico do gato para o adotante em arquivo legível e imprimível.
- Área pública de doações; Pix e links de campanhas configuráveis pela responsável.
- Fila persistente para avisos de candidatura e relatório do fim de semana, com gateway Python para a WhatsApp Cloud API. O envio real precisa de credenciais, destinatários, hospedagem do gateway e agendamento na hospedagem do site. Veja [configuração e execução](docs/07-whatsapp-python.md).
- Login, sessões revogáveis, restrições no servidor, proteção de origem e limites de tentativas.

Estoque, compras e seus avisos saíram do escopo. Os registros antigos são preservados, e as rotas retiradas retornam 410.

## Limites desta entrega

O gateway WhatsApp está implementado, mas o envio e o agendamento de produção ainda não estão configurados. Pix e links reais devem ser informados pela responsável. Uploads aceitam até 8 MB e usam R2 na hospedagem; comprovantes antigos de vacinação continuam com apenas o nome de arquivo. O termo pode ser anexado, sem assinatura digital. Os seis gatos iniciais continuam sendo exemplos fictícios. Não há envio de e-mail.

## Verificação e publicação

`pnpm test`: testes integrados com SQLite real. `pnpm build`: gera Worker, assets e migrações. `public/` é a fonte da interface; `server/` contém a API; `drizzle/` contém migrações versionadas e imutáveis após publicação. A hospedagem aplica as migrações antes do Worker.

## Versionamento no Git

Versione o código em `public/`, `server/` e `services/`, os testes, as migrações e seus metadados, a documentação técnica, os arquivos de dependências (incluindo `pnpm-lock.yaml`) e os modelos `.env.example`. A configuração `.openai/hosting.json` é usada pelo build e contém o identificador do projeto de hospedagem, sem credenciais; ajuste esse identificador ao usar outra hospedagem.

O `.gitignore` exclui arquivos `.env` e suas variantes locais, bancos SQLite, dependências, caches, logs, builds e entregas geradas. Os modelos `.env.example` continuam disponíveis para configurar uma nova instalação. O `.gitattributes` padroniza as quebras de linha do código em LF.

Antes de criar um commit, execute `pnpm test`, `pnpm build` e os testes Python descritos em [Integração do WhatsApp](docs/07-whatsapp-python.md). Confira `git status --short` e `git diff --check`, depois revise o conteúdo selecionado com `git diff --cached`. Em uma nova instalação, use `pnpm install --frozen-lockfile` para respeitar as versões do lockfile.

As migrações 0001 e 0002 acrescentam prontuários e índice de CPF sem apagar registros existentes. A interface carrega app.js, management.js, community.js e interview-lookup.js nesta ordem; o último inicia a sessão após registrar todos os fluxos.

Adotantes podem consultar o próprio CPF em Minha candidatura (`/#tracking`), sem login. A API pública `POST /api/tracking/cpf` aceita CPF completo válido e retorna somente data e etapa, sem nomes, respostas, orientações privadas ou tokens. Limite de 10 tentativas por IP a cada 15 minutos e validação de origem. A consulta por CPF não comprova identidade; o link individual continua disponível para orientações da equipe. Entrevistas antigas precisam ter o CPF vinculado pela responsável.

Logo fornecida pelo usuário. Fotos ilustrativas: River Fx, Sergei Karakulov e Meaghan Cafferty / Unsplash.

Recuperação de senha: use Esqueci minha senha com e-mail e código privado. Minha conta permite gerar um código mediante confirmação da senha atual. No primeiro uso do administrador, a chave ADMIN_SETUP_KEY serve como código inicial. Cada redefinição invalida o código anterior e todas as sessões; o novo código é mostrado uma vez. Apenas o hash do código fica em settings. Não há envio de e-mail nesta versão. O banco SQLite local e o D1 de produção são independentes.
