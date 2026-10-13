# Peticas — gestão e adoção

Backend Python com FastAPI e PostgreSQL 17 normalizado. O frontend permanece em HTML, CSS e JavaScript. O banco usa tabelas e colunas em português, com prefixos de três letras por tipo ou finalidade: `cod_`, `txt_`, `num_`, `dat_`, `hor_`, `flg_` e `bin_`.

A configuração, o modelo relacional, o esquema SQL e os testes estão no [guia do backend Python e PostgreSQL](docs/08-backend-python-postgresql.md).

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
| `pnpm test` | Testes JavaScript da interface |

## Estrutura

`backend/` contém a API Python, a rotina de mensagens, o acesso PostgreSQL, o esquema SQL e os testes. `public/` contém a interface. `compose.yaml` configura a execução local. A integração Python com a Meta também está em `backend/`.

O esquema completo está em `backend/schema.sql`. A API cria as tabelas quando o banco está vazio e valida um banco existente sem recriá-lo. Não há arquivos nem tabela de histórico de migrações. Mudanças futuras da estrutura de um banco preenchido devem ser aplicadas explicitamente por SQL, depois de backup. A [documentação técnica](docs/README.md) reúne os guias atuais.

Logo fornecida pelo usuário. Fotos ilustrativas: River Fx, Sergei Karakulov e Meaghan Cafferty / Unsplash.
