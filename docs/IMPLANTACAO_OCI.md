# Implantação do Peticas na OCI

Esta configuração prepara a primeira instalação comercial em uma VM OCI Compute: Caddy recebe HTTPS, a API Python atende apenas na rede Docker e PostgreSQL e jobs ficam sem portas publicadas. Não cria recursos na conta Oracle, não faz cobrança e não publica o site automaticamente. A instalação atende uma organização; ainda não é um SaaS com isolamento de vários clientes.

## 1. O que definir na conta Oracle

Como ponto inicial para avaliar o piloto, considere Ubuntu 24.04 LTS, 2 OCPUs e 4 GB de RAM, com disco persistente dimensionado para banco, imagens, vídeos, logs e backups. Isso é uma estimativa inicial, não uma capacidade garantida: medir consumo e espaço antes de aumentar a utilização. Confirme preço, disponibilidade e arquitetura no console antes de criar. Não conte com gratuidade ou disponibilidade de uma configuração específica.

Escolha região e compartment, crie a VM com chave pública SSH e guarde a chave privada no seu computador. Use IP público reservado se desejar um endereço estável. A VCN precisa de sub-rede com rota para Internet Gateway. No NSG e nas security lists, confira as regras efetivas:

| Porta | Origem | Uso |
| --- | --- | --- |
| TCP 22 | Somente seu IP administrativo ou acesso controlado | SSH |
| TCP 80 | Internet | Redirecionamento e validação do certificado |
| TCP 443 | Internet | Site HTTPS |

Não abra 5432, 4173 ou 8001. Confira também o firewall do sistema operacional; regras da OCI e do host precisam permitir o tráfego necessário. Não substitua ou apague regras do host às cegas. As portas publicadas pelo Docker exigem considerar suas regras de firewall próprias, além de UFW.

## 2. Endereço enquanto não há domínio

Não é obrigatório comprar o domínio agora, mas esta configuração exige um hostname público sob seu controle, inclusive um subdomínio temporário de um serviço DNS escolhido por você. Configure um registro A para o IP reservado da VM; só adicione AAAA se o IPv6 estiver efetivamente configurado. Informe apenas o hostname em `SITE_HOST`.

O Caddy solicita e renova o certificado quando DNS e conectividade estão corretos. Acessar somente o IP não substitui o endereço HTTPS configurado aqui. Não use `tls internal` para candidatos: o certificado local não será confiável nos dispositivos deles. A aplicação depende de HTTPS para cookies seguros e localização no navegador. Antes de coletar dados reais, confirme ausência de alertas de certificado.

## 3. Preparar o servidor

Instale Docker Engine e o plugin Compose seguindo a documentação oficial do Docker para Ubuntu. Use uma conta de administração; pertencer ao grupo `docker` concede privilégios equivalentes a root. Não execute scripts de instalação de origem desconhecida.

Transfira um checkout do projeto para `/opt/peticas`, por Git privado ou transferência autenticada. Não copie `.env`, `.git` desnecessariamente, PDFs de exemplo, documentação acadêmica gerada ou backups do seu computador. Garanta que a conta de operação possa acessar a pasta. No servidor:

```bash
cd /opt/peticas
cp deploy/oci/.env.example deploy/oci/.env
chmod 600 deploy/oci/.env
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Gere dois segredos independentes e edite o arquivo com `nano deploy/oci/.env`: senha PostgreSQL e chave para criar a primeira responsável. Preencha também hostname e e-mail de operação. Não envie segredos pelo chat nem os inclua no Git. O arquivo local de desenvolvimento não é reutilizado; os gatos de demonstração ficam desativados.

```bash
docker compose --env-file deploy/oci/.env -f deploy/oci/compose.yaml config --quiet
docker compose --env-file deploy/oci/.env -f deploy/oci/compose.yaml up --build -d
docker compose --env-file deploy/oci/.env -f deploy/oci/compose.yaml ps
curl --fail https://SEU_HOSTNAME/api/health
```

Não execute `config` sem `--quiet` ao compartilhar a saída: ele expande segredos. A rede do proxy usa `172.30.250.0/29`. Se houver conflito com VCN, VPN ou outra rede Docker, escolha outra faixa livre e altere conjuntamente subnet, os dois endereços e `--forwarded-allow-ips`. A API confia apenas no IP privado do Caddy para reconhecer HTTPS e IP do visitante. Não substitua essa restrição por `*`, nem publique a porta da API.

Cadastre a primeira responsável pelo site HTTPS usando a chave de instalação. Após criar a conta, troque a chave no arquivo e recrie a API; o servidor também impede novo cadastro público quando já existe administradora. Configure identificação, política de guarda e contato, revise os modelos de privacidade e adoção e valide o fluxo sem usar dados de pessoas reais.

Esta composição não ativa o gateway Meta local. Se precisar dele, prepare sua implantação e credenciais separadamente; `WHATSAPP_WEBHOOK_URL` deve apontar para um gateway HTTPS protegido pelo token. Campo vazio não habilita entrega real. A rotina jobs continua processando a fila conforme a configuração existente.

## 4. Backup e recuperação

### Piloto gratuito com 1 GB de RAM

Use uma imagem Ubuntu suportada (22.04, 24.04 ou 26.04), configure swap de 2 GB e teste o consumo real. Swap usa disco e pode tornar o sistema lento; não aumenta a RAM física. `deploy/oci/compose.micro.yaml` limita a memória dos processos e reduz parâmetros do PostgreSQL. Para esse perfil, acrescente `-f deploy/oci/compose.micro.yaml` a todos os comandos da composição, inclusive atualizações. O backup usa a composição base para acessar o mesmo serviço e volume.

Construa a imagem fora da VM e transfira-a com `docker save`/`docker load` por SSH autenticado. Configure `PETICAS_APP_IMAGE` com o tag da release enviada e inicie com `up --no-build -d`. API e jobs compartilham essa imagem. O tag deve existir localmente no servidor antes da inicialização. Se limites de memória encerrarem um processo, examine `docker stats`, eventos/OOM e carga, e dimensione a VM antes de aumentar a utilização. Esse perfil é destinado a um piloto com poucos acessos, sem promessa de capacidade comercial.

Fotos, vídeos e documentos enviados estão no PostgreSQL e entram no dump. Certificados do Caddy ficam no volume `caddy_data`. A VM única e seus volumes são um ponto de falha; não equivalem a alta disponibilidade.

```bash
cd /opt/peticas
bash deploy/oci/backup.sh
```

O script usa permissões restritas, cria um dump completo e verifica a estrutura do arquivo. Não apaga backups antigos. A verificação não substitui um teste de restauração. Para agendar diariamente, por exemplo às 03:00 UTC, use o crontab da conta que tem acesso ao Docker e confirme o fuso do servidor:

```cron
0 3 * * * /usr/bin/flock -n /opt/peticas/backups/oci/backup.lock /bin/bash /opt/peticas/deploy/oci/backup.sh >> /opt/peticas/backups/oci/backup.log 2>&1
```

Execute o script uma vez antes de cadastrar o cron para criar a pasta. Verifique periodicamente horário, resultado e tamanho; cron sozinho não envia alertas. Defina retenção, cópia externa e alertas antes de atender clientes pagantes. Uma cópia apenas na mesma VM pode ser perdida com o servidor. OCI Object Storage é uma opção para a cópia externa, com bucket privado, IAM restrito e política de retenção definida. Esta configuração não provisiona bucket nem envia arquivos para ele.

Teste restauração em banco separado, sem trocar o banco ativo. Use um dump previamente copiado ao servidor com permissões restritas:

```bash
docker compose --env-file deploy/oci/.env -f deploy/oci/compose.yaml exec -T db createdb -U peticas peticas_validacao
docker compose --env-file deploy/oci/.env -f deploy/oci/compose.yaml exec -T db pg_restore -U peticas -d peticas_validacao --no-owner --no-privileges --exit-on-error < backups/oci/ARQUIVO.dump
```

O banco de validação também contém dados pessoais: restrinja o acesso e descarte-o após verificar tabelas, contagens e anexos. Não use `--clean` contra produção. Recuperar o banco ativo exige janela de manutenção, interrupção de API/jobs e plano de retorno; siga o manual e revise o alvo antes de executar. Nunca rode `docker compose down -v` para atualizar o site: isso remove os volumes.

## 5. Atualizar e operar

### Acessar o banco a partir do Windows

Na raiz do projeto, execute no PowerShell:

```powershell
.\deploy\oci\acessar-banco.ps1 -Servidor SEU_IP_PUBLICO -Chave 'C:\caminho\chave.key'
```

O modo padrão abre `psql` via SSH, com o usuário PostgreSQL de administração `peticas`. Para consultar, use `\dt`, `\d gatos` e `SELECT cod_identificador, txt_nome FROM gatos LIMIT 10;`; saia com `\q`. Esse acesso também permite alterações: confira o alvo e faça backup antes de modificar dados ou estrutura.

Para DBeaver/pgAdmin, acrescente `-Modo Tunel`. Mantenha a janela aberta e configure o cliente para PostgreSQL, host `127.0.0.1`, porta `15433`, banco `peticas`, usuário `peticas`. A senha é `POSTGRES_PASSWORD` de `/opt/peticas/deploy/oci/.env` na VM, não a senha do banco local. O túnel SSH já protege o trajeto; PostgreSQL neste perfil não tem TLS próprio, portanto não exija TLS na conexão interna do cliente. Não compartilhe a senha ou capturas de configuração com credenciais. Não crie regra de entrada 5432 na OCI.

O script usa uma cópia temporária da chave com ACL restrita e apaga a cópia ao encerrar. A chave original é preservada. Se o PowerShell bloquear scripts, revise o arquivo e execute usando `powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\oci\acessar-banco.ps1` com os mesmos parâmetros; isso vale apenas para esse processo, sem alterar a política permanente. A identidade do servidor usa o arquivo de hosts da implantação; uma divergência deve ser investigada, não ignorada. Para uso frequente só de consulta, crie um usuário PostgreSQL com privilégios de leitura em vez de compartilhar o usuário administrativo.

1. Teste a nova versão, registre o commit e faça backup antes da atualização.
2. Se o esquema mudou, planeje e aplique SQL explícito durante uma janela de manutenção. O projeto não migra bancos existentes automaticamente.
3. Atualize o checkout e rode `up --build -d` com o mesmo `--env-file` e `-f` acima.
4. Confira saúde, HTTPS, login, PDF, anexos, candidatura e permissão de localização. Faça rollback de código apenas se o esquema continuar compatível.

Para a versão da loja com carrinho no servidor, aplique explicitamente `python -m backend.shop_migrate` a partir da nova imagem, com `DATABASE_URL` apontando para o PostgreSQL privado, antes de trocar a API. O comando instala as tabelas adicionais e o catálogo inicial em uma transação, sem alterar as tabelas de adoção. Não reutilize o banco de produção para os testes: utilize um PostgreSQL temporário em rede Docker isolada. Consulte [LOJA_BANCO.md](LOJA_BANCO.md) para estrutura, endpoints e limites da implementação.

Use `docker compose ... logs --tail 100 api jobs proxy` para diagnóstico; não compartilhe logs com dados pessoais. Acesso HTTP não é registrado pelo proxy/API, mas erros ainda podem conter informações sensíveis. Os logs Docker têm rotação. Monitore disponibilidade externa, CPU/RAM, espaço em disco, certificados e sucesso dos backups; configure notificações de falha. Mantenha sistema, Docker e imagens atualizados após testar. Para versões reproduzíveis, fixe os digests das imagens de PostgreSQL/Caddy da release homologada e registre-os; os tags deste modelo recebem atualizações.

Os backups são ignorados pelo Git e pelo contexto de build Docker. Um arquivo `.env` em produção continua sendo um segredo sob sua responsabilidade. Nenhuma porta de banco precisa ficar aberta na internet para manutenção: use SSH e `docker compose exec`.

## 6. Fontes e próximos passos

- [OCI: criar instância](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm)
- [OCI: Network Security Groups](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm)
- [Docker Engine no Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Caddy: HTTPS automático](https://caddyserver.com/docs/automatic-https)
- [Uvicorn: confiança nos cabeçalhos do proxy](https://www.uvicorn.org/settings/)

Antes da implantação real faltam: criar e autorizar acesso à VM, escolher hostname temporário, confirmar custo/recursos, preparar cópia externa de backup e revisão dos termos. Para ampliar a vários clientes, definir isolamento de organizações e atualização versionada dos bancos antes de compartilhar uma instalação.
