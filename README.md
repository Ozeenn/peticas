# Peticas — gestão e adoção

Backend Python com FastAPI e PostgreSQL 17 normalizado. O frontend permanece em HTML, CSS e JavaScript. O banco usa tabelas e colunas em português, com prefixos de três letras por tipo ou finalidade: `cod_`, `txt_`, `num_`, `dat_`, `hor_`, `flg_` e `bin_`.

A configuração, o modelo relacional, as migrações e os testes estão no [guia do backend Python e PostgreSQL](docs/08-backend-python-postgresql.md).

## Executar localmente

Requer Docker Desktop em execução com contêineres Linux.

1. Copie `.env.example` para `.env` se esse arquivo ainda não existir.
2. Configure `POSTGRES_PASSWORD` com senha aleatória longa de letras e números e `ADMIN_SETUP_KEY` com chave privada aleatória longa.
3. Execute `docker compose up --build -d`.
4. Abra http://127.0.0.1:4173.

A primeira responsável cria a conta com a chave de instalação. Depois, somente ela cadastra voluntários e define suas permissões. `SEED_DEMO=true` cria seis gatos fictícios uma única vez; use `false` para instalação sem exemplos. Não há importação automática dos bancos SQLite anteriores.

`docker compose down` encerra os serviços preservando o volume PostgreSQL. Os serviços `api` e `jobs` usam o mesmo banco. O gateway WhatsApp opcional também usa esse PostgreSQL. Não publique `.env` nem arquivos de banco.

## Funcionalidades

- Cadastro de gatos, propostas de voluntários, revisão, fotos e situações.
- Fichas de voluntários, aceite, contas, permissões individuais e sessões revogáveis.
- Entrevista de adoção, análise, visita, aprovação, reserva e conclusão.
- Consulta por CPF de todas as candidaturas e suas etapas; mensagens da responsável pelo link privado.
- Histórico, acompanhamento após adoção, devolução e anexos de vídeo e termo PDF.
- Prontuário, prescrições, aplicações, encerramentos e checklist de doses previstas; localização obrigatória nas aplicações de medicamento, acessível somente à responsável.
- Área resumida dos voluntários para consultar medicações e registrar aplicações de medicamentos e vacinas.
- Pix e campanhas configuráveis.
- Fila persistente de mensagens e relatório do fim de semana, processados por Python.
- Transações, chaves estrangeiras e restrições para proteger reservas, doses e históricos.

Estoque e compras permanecem fora do escopo. O envio WhatsApp depende das credenciais e destinatários da Meta; a configuração padrão simula os envios. Não há envio de e-mail ou assinatura digital. Os anexos aceitam até 8 MB e são armazenados no PostgreSQL. Comprovantes de vacinas na interface anterior ainda guardam somente o nome do arquivo.

## Comandos

| Comando | Função |
| --- | --- |
| `docker compose up --build -d` | Iniciar API, PostgreSQL e rotina de mensagens |
| `pnpm dev` | Iniciar os serviços em primeiro plano |
| `pnpm build` | Construir imagens Docker |
| `docker compose --profile whatsapp up --build -d` | Ativar também o gateway WhatsApp |
| `python -m pytest backend/tests -q` | Testar a API com `PETICAS_TEST_DATABASE_URL` configurada |
| `python -m unittest services.whatsapp.test_gateway -q` | Testar os contratos do gateway existente |
| `pnpm test` | Testes JavaScript da interface e da implementação legada |
| `pnpm dev:legacy` / `pnpm build:legacy` | Executar/construir explicitamente o Worker/SQLite anterior |

## Estrutura

`backend/` contém a API Python, a rotina de mensagens, o acesso PostgreSQL, as migrações e os testes. `public/` contém a interface. `compose.yaml` configura a execução local. `services/whatsapp/` contém a integração Python com a Meta, reutilizada com armazenamento PostgreSQL no novo Compose.

A implementação anterior em `server/`, `db/` e `drizzle/` foi preservada para referência e continua com banco independente. Os guias técnicos 01–07 descrevem principalmente essa versão. A [documentação técnica](docs/README.md) indica o novo guia. O Docker local não publica o site em produção; a hospedagem Python/PostgreSQL ainda será escolhida.

Logo fornecida pelo usuário. Fotos ilustrativas: River Fx, Sergei Karakulov e Meaghan Cafferty / Unsplash.
