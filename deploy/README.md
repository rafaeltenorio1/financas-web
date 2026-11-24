# Publicação na Oracle Cloud

Passo a passo para colocar o Finanças no ar numa VM ARM gratuita da Oracle, com HTTPS pelo Caddy, e-mail pelo Resend e backup cifrado no Cloudflare R2.

Troque `seudominio.com.br` pelo domínio escolhido em todos os comandos.

## Visão geral

```
internet ── 80/443 ──> Caddy (deploy/proxy) ──┬── /       front-end (arquivos estáticos)
                       172.30.0.10             └── /api/*  financas-api:8000 ── rede banco ── Postgres
```

- `deploy/proxy/`: Caddy compartilhado entre os projetos do servidor. Sobe **antes** dos projetos, porque cria a rede `proxy`.
- `docker-compose.yml`: API e banco do Finanças. Em produção, sempre com `-f docker-compose.yml`, para o override de desenvolvimento ficar de fora.
- `deploy/deploy.sh`: atualiza o código, faz backup, aplica as migrações e confere a saúde.
- `deploy/backup.sh` e `deploy/restaurar.sh`: backup cifrado no R2 e restauração com conferência.

## 1. Contas e domínio

1. **Domínio:** registre o `.com.br` no [registro.br](https://registro.br), com renovação automática.
2. **Cloudflare:** crie a conta, adicione o domínio no plano Free e troque, no registro.br, os servidores DNS pelos dois que o Cloudflare indicar. A propagação leva de minutos a algumas horas.
3. **Oracle Cloud:** crie a conta com a região **Brazil East (São Paulo)** como região principal. Ela não pode ser trocada depois.
   - Em *Billing → Upgrade and Manage Payment*, passe para **Pay As You Go**. Isso evita que a VM seja recuperada por ociosidade.
   - Em *Billing → Budgets*, crie um orçamento de **US$ 1** com alerta por e-mail a partir de 1%. O alerta **só avisa, não bloqueia**.
   - Ao criar qualquer recurso, use só opções marcadas como **Always Free-eligible**.
4. **Resend:** crie a conta. O domínio entra no passo 9.
5. **Healthchecks.io** e **UptimeRobot:** crie as contas, as duas grátis. Elas entram no passo 12.

## 2. Criar a VM

Em *Compute → Instances → Create instance*:

- **Image:** Canonical Ubuntu 24.04 (aarch64).
- **Shape:** `VM.Standard.A1.Flex` (Ampere), com até **4 OCPUs e 24 GB** no Always Free.
  - Se aparecer *Out of capacity*, tente outro *availability domain* ou tente de novo mais tarde.
- **Boot volume:** até 200 GB no Always Free. 100 GB é suficiente.
- **SSH:** cole a sua chave pública. Se ainda não tiver uma, gere no WSL com `ssh-keygen -t ed25519` e use o conteúdo de `~/.ssh/id_ed25519.pub`.
- **IP público:** depois de criar, em *Attached VNICs → IPv4 Addresses*, troque o IP efêmero por um **Reserved public IP**. Assim o IP não muda se a VM for recriada. Confira se ele aparece como Always Free.

No Cloudflare, crie os registros DNS:

| Tipo | Nome | Conteúdo | Proxy |
|---|---|---|---|
| A | `@` | IP da VM | **DNS only** (nuvem cinza) |

A nuvem precisa ficar **cinza**. Com o proxy do Cloudflare ligado, ele entra na frente do Caddy e o IP real dos visitantes deixa de chegar à API.

## 3. Liberar as portas

A Oracle tem **duas** camadas de firewall, e as duas precisam ser abertas.

**3.1. Security List (no console):** em *Networking → Virtual Cloud Networks → (sua VCN) → Security Lists → Default*, adicione regras de *Ingress* com origem `0.0.0.0/0`:

| Protocolo | Porta |
|---|---|
| TCP | 80 |
| TCP | 443 |
| UDP | 443 |

A porta 22 (SSH) já vem liberada.

**3.2. iptables (dentro da VM):** a imagem Ubuntu da Oracle vem com regras que bloqueiam tudo menos o SSH, inclusive o tráfego **encaminhado** para containers. Acesse a VM:

```bash
ssh ubuntu@IP_DA_VM
```

Edite `/etc/iptables/rules.v4` (com `sudo nano`):

- Logo depois da linha `-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT`, acrescente:
  ```
  -A INPUT -p tcp -m state --state NEW -m tcp --dport 80 -j ACCEPT
  -A INPUT -p tcp -m state --state NEW -m tcp --dport 443 -j ACCEPT
  -A INPUT -p udp -m udp --dport 443 -j ACCEPT
  ```
- **Apague** a linha `-A FORWARD -j REJECT --reject-with icmp-host-prohibited`. Sem isso, o Docker não consegue entregar o tráfego ao Caddy.

Aplique e confira:

```bash
sudo iptables-restore < /etc/iptables/rules.v4
sudo iptables -L INPUT -n --line-numbers
```

Não use `ufw` junto com essas regras. Lembre também que portas publicadas pelo Docker passam por cima do firewall do sistema. Por isso só o Caddy publica portas.

## 4. Proteger o servidor

```bash
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y fail2ban unattended-upgrades git age
sudo timedatectl set-timezone UTC
```

**SSH só com chave:** crie `/etc/ssh/sshd_config.d/10-endurecer.conf` com:

```
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

Depois rode `sudo systemctl restart ssh`. **Antes de fechar a sessão atual**, abra outro terminal e confirme que `ssh ubuntu@IP_DA_VM` continua entrando.

**Atualizações automáticas:** rode `sudo dpkg-reconfigure -plow unattended-upgrades` e responda *Yes*. Para permitir reinício automático quando um update de kernel exigir, edite `/etc/apt/apt.conf.d/50unattended-upgrades`:

```
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "07:00";
```

07:00 UTC equivale a 04:00 em Brasília. Os containers voltam sozinhos, porque usam `restart: unless-stopped`.

O `fail2ban` já protege o SSH com a configuração padrão. Confira com `sudo fail2ban-client status sshd`.

## 5. Docker e rclone

**Docker:** instale pelo repositório oficial ([docs.docker.com/engine/install/ubuntu](https://docs.docker.com/engine/install/ubuntu/)), com os pacotes `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin` e `docker-compose-plugin`. Depois:

```bash
sudo usermod -aG docker ubuntu
```

Saia e entre de novo no SSH. Atenção: estar no grupo `docker` equivale a ter acesso de root. Proteja bem a chave SSH.

**rclone:** a versão do `apt` é antiga. Instale o pacote oficial para ARM:

```bash
curl -fLO https://downloads.rclone.org/rclone-current-linux-arm64.deb
sudo apt install ./rclone-current-linux-arm64.deb
rm rclone-current-linux-arm64.deb
rclone version
```

## 6. Código no servidor

```bash
sudo mkdir -p /srv/financas && sudo chown ubuntu:ubuntu /srv/financas
git clone https://github.com/rafaeltenorio1/financas-web.git /srv/financas
```

Se o repositório for privado, crie uma **deploy key** só de leitura:

1. Na VM, gere a chave: `ssh-keygen -t ed25519 -f ~/.ssh/financas_deploy -N ""`.
2. No GitHub, cadastre o conteúdo de `~/.ssh/financas_deploy.pub` em *Settings → Deploy keys*, **sem** marcar *Allow write access*.
3. Clone por SSH com `git@github.com:...`, e configure em `~/.ssh/config` um `Host github.com` com `IdentityFile ~/.ssh/financas_deploy`.

## 7. Proxy (Caddy)

Crie `/srv/financas/deploy/proxy/.env`:

```
ACME_EMAIL=seu-email@exemplo.com
FINANCAS_DOMINIO=seudominio.com.br
```

Suba o proxy:

```bash
cd /srv/financas/deploy/proxy
docker compose up -d
docker compose logs -f caddy
```

Use só o domínio principal, sem `www`: o `CORS_ORIGINS` do passo 8 só lista o domínio principal, e um `POST` vindo de `www.` seria recusado pelo `verificar_origem`. Espere a linha `certificate obtained successfully`. Se o DNS ainda não estiver propagado, o Caddy tenta de novo sozinho. **Não apague** o volume `caddy_data`: ele guarda os certificados, e emitir certificados demais esbarra no limite do Let's Encrypt.

## 8. `.env` de produção da API

Crie `/srv/financas/.env` com `chmod 600`. **Use segredos novos.** Nunca reaproveite os do desenvolvimento.

Para gerar os segredos, rode na VM:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
docker run --rm python:3.15-slim sh -c "pip -q install cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
```

Use o primeiro para `SECRET_KEY`, o segundo para `POSTGRES_PASSWORD` e o terceiro para `TOTP_CHAVE`. Depois preencha o arquivo:

```
POSTGRES_USER=financas
POSTGRES_PASSWORD=<gerado>
POSTGRES_DB=financas

AMBIENTE=producao
PROXIES_CONFIAVEIS=["172.30.0.10"]
COOKIE_SECURE=true
SECRET_KEY=<gerado>
TOTP_CHAVE=<gerado>
CORS_ORIGINS=["https://seudominio.com.br"]

SMTP_HOST=smtp.resend.com
SMTP_PORTA=587
SMTP_SEGURANCA=starttls
SMTP_USUARIO=resend
SMTP_SENHA=<API key do Resend>
EMAIL_REMETENTE=Nome do Site <nao-responda@seudominio.com.br>

FRONT_URL=https://seudominio.com.br
```

- **Guarde uma cópia deste arquivo fora do servidor**, num gerenciador de senhas. Sem a mesma `TOTP_CHAVE`, um backup restaurado perde o 2FA de todo mundo. Sem a mesma `SECRET_KEY`, só os tokens CSRF mudam.
- `PROXIES_CONFIAVEIS` é o IP fixo do Caddy (`deploy/proxy/docker-compose.yml`). **Nunca** use a rede inteira nem `*`.
- Em produção, a API se recusa a subir com configuração insegura (cookie sem `Secure`, origem `http`, SMTP sem TLS, `SECRET_KEY` fraca). Se ela não subir, leia `docker compose -f docker-compose.yml logs api`.

## 9. E-mail (Resend) e DNS do domínio

1. No Resend, em *Domains → Add domain*, informe `seudominio.com.br` e a região `sa-east-1` (São Paulo), se estiver disponível.
2. Copie para o Cloudflare **exatamente** os registros que o Resend mostrar (MX e TXT de SPF no subdomínio `send`, TXT de DKIM `resend._domainkey`), todos com a nuvem cinza.
3. Acrescente o **DMARC**: tipo TXT, nome `_dmarc`, conteúdo:
   ```
   v=DMARC1; p=quarantine; adkim=s; aspf=s; rua=mailto:seu-email@exemplo.com
   ```
4. Espere o Resend marcar o domínio como *Verified*. Em *API Keys*, crie uma chave com permissão **Sending access** só para esse domínio, e use-a como `SMTP_SENHA`.

Comece o DMARC com `p=quarantine`. Depois de algumas semanas sem relatórios de falha, troque para `p=reject`.

## 10. Backup (Cloudflare R2)

**10.1. Bucket.** No Cloudflare, em *R2 → Create bucket*, crie o `financas-backups` com *Location: Automatic*. Depois:

- Em *Settings → Object lifecycle rules*, crie uma regra para **apagar objetos com mais de 30 dias**.
- Em *R2 → Manage API tokens*, crie um token **Object Read & Write** restrito ao bucket `financas-backups`. Guarde o *Access Key ID*, o *Secret Access Key* e o endpoint `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.

**10.2. rclone na VM.** Crie `~/.config/rclone/rclone.conf` com `chmod 600`:

```
[r2]
type = s3
provider = Cloudflare
access_key_id = <Access Key ID>
secret_access_key = <Secret Access Key>
endpoint = https://<ACCOUNT_ID>.r2.cloudflarestorage.com
acl = private
no_check_bucket = true
```

Teste com `rclone lsf r2:financas-backups`. A saída vazia, sem erro, indica que funcionou.

**10.3. Chave do age: gerada no seu computador, nunca na VM.**

```bash
age-keygen -o ~/financas-backup-chave.txt
```

- O comando mostra a chave **pública** (`age1...`). Só ela vai para a VM.
- A **privada** fica no arquivo gerado. Guarde-a em dois lugares fora do servidor: num gerenciador de senhas e numa cópia offline (pendrive ou papel).
- **Sem ela, nenhum backup pode ser lido.**

**10.4. Configuração na VM.** Crie `/srv/financas/deploy/.env` com `chmod 600`:

```
AGE_DESTINATARIO=age1...
RCLONE_DESTINO=r2:financas-backups
BACKUP_PING_URL=<URL do healthchecks.io, passo 12>
```

## 11. Primeiro deploy

```bash
cd /srv/financas
./deploy/deploy.sh
```

No primeiro deploy, o banco está vazio, então o script pula o backup ("primeiro deploy, sem backup"). Ele aplica todas as migrações, incluindo as categorias padrão, e confere o `/saude`.

Confira:

- `https://seudominio.com.br` abre a tela de entrada com o cadeado do HTTPS.
- `https://seudominio.com.br/api/saude` responde `{"api":"ok","banco":true}`.
- O cadastro envia o e-mail de verificação, e o link abre o site.
- [securityheaders.com](https://securityheaders.com) e [ssllabs.com/ssltest](https://www.ssllabs.com/ssltest/) mostram nota A ou melhor.

Em seguida, rode o primeiro backup e o teste de restauração. A chave privada vai para a VM só durante o teste:

```bash
./deploy/backup.sh
scp ~/financas-backup-chave.txt ubuntu@IP_DA_VM:/tmp/chave.txt
./deploy/restaurar.sh --chave /tmp/chave.txt ultimo
shred -u /tmp/chave.txt
docker compose -f docker-compose.yml exec -T db psql -U financas -d postgres -c "DROP DATABASE financas_restauracao;"
```

O `scp` roda no seu computador; os demais comandos, na VM.

## 12. Agendamento e monitoramento

**Backup diário.** Rode `crontab -e` e acrescente:

```
0 6 * * * /srv/financas/deploy/backup.sh >> /home/ubuntu/backup.log 2>&1
```

06:00 UTC equivale a 03:00 em Brasília.

**Healthchecks.io.** Crie um *check* com período de 1 dia e tolerância de 2 horas. Use a URL de ping dele em `BACKUP_PING_URL`. Se o backup falhar ou deixar de rodar, você recebe um e-mail.

**UptimeRobot.** Crie um monitor do tipo *HTTP(s) - Keyword*:

- URL: `https://seudominio.com.br/api/saude`;
- palavra-chave: `"banco":true`;
- intervalo: 5 min.

Ele avisa se o site cair **ou** se a API perder o banco.

**Logs.**

- API e banco: `docker compose -f docker-compose.yml logs -f --tail=100`.
- Caddy: `docker compose -f deploy/proxy/docker-compose.yml logs -f`.
- Os logs giram sozinhos (3 arquivos de 10 MB por container).

## Rotina

| Quando | O quê |
|---|---|
| A cada atualização | `git push` no seu computador, depois `./deploy/deploy.sh` na VM. |
| Todo mês | Teste de restauração (passo 11, `restaurar.sh` em modo conferência). |
| Todo mês | Confira a fatura da Oracle, que deve ser US$ 0, e o espaço em disco com `df -h`. |
| A cada versão nova do Caddy | Troque a tag em `deploy/proxy/docker-compose.yml` e rode `docker compose up -d` na pasta do proxy. |

**Migrações e deploy.** Entre a migração e a API nova, a API antiga roda alguns segundos com o banco já migrado. Para remover ou renomear uma coluna, faça em dois deploys: primeiro o código para de usar a coluna, depois a migração a remove.

## Se a Oracle der problema (plano de fuga)

1. Crie uma VM em outro provedor (Hetzner, DigitalOcean, Magalu Cloud) e repita os passos 3 a 7. Na Oracle, o passo 3.2 não se aplica a outros provedores: use o firewall do provedor.
2. Copie o `.env` guardado (passo 8) e o `deploy/.env` (passo 10.4).
3. Rode `./deploy/deploy.sh`.
4. Restaure com `./deploy/restaurar.sh --chave <chave> --substituir ultimo`.
5. No Cloudflare, aponte o registro A para o novo IP.

Os registros do Resend e o R2 não mudam. Com a chave em mãos, o processo leva menos de uma hora.
