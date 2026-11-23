# JobSeacher

Coleta vagas de **desenvolvedor Java júnior** de várias fontes, filtra as que são júnior de verdade, remove duplicadas e avisa as novas.

```
 Sites com API                                   Sites sem API
 (GitHub, Gupy, Adzuna, Careerjet)               (LinkedIn, ...)
        │                                               │
        ▼                                               ▼
┌──────────── core-java (Spring Boot) ─────────┐   scraper-python
│  Coletores Java ──┐                          │        │ publica 1 mensagem por vaga
│                   ▼                          │        ▼
│            IngestaoService ◄── consumer ◄────┼── RabbitMQ: vagas.coletadas
│                   │                          │        └─► nucleo.ingestao-vagas (+ DLQ)
│   Filtro júnior → Deduplicação → Score       │
│                   ▼                          │
│               MongoDB ──► Telegram            │
└──────────────────────────────────────────────┘
```

- Os **coletores Java** chamam o `IngestaoService` direto (mesmo processo).
- O **scraper Python** não conhece o Java: só publica no RabbitMQ. O núcleo consome a fila quando estiver no ar, e nada se perde se ele estiver fora.
- Todas as regras (filtro, deduplicação, score, aviso) ficam **só no núcleo**. O formato das mensagens está em [`contrato/`](contrato/README.md).

| Pasta | O que é | Etapa |
|---|---|---|
| `contrato/` | Formato das mensagens na fila e topologia do RabbitMQ | 1 ✅ |
| `docker-compose.yml` | MongoDB + RabbitMQ locais | 1 ✅ |
| `core-java/` | Núcleo: APIs, ingestão, filtro, banco, notificação | 2–6 |
| `scraper-python/` | Scraper dos sites sem API; publica na fila | 7 |
| `scripts/` | Utilitários (validação do contrato) | 1 ✅ |

## Pré-requisitos (Windows)

| Ferramenta | Para quê | Instalação (PowerShell) |
|---|---|---|
| Docker Desktop | MongoDB, RabbitMQ e (nas próximas etapas) núcleo e scraper | já instalado ✅ |
| Git | versionamento | `winget install --id Git.Git -e` |

Só isso para **rodar** o projeto. Para **desenvolver** em Java com autocompletar e depuração, instale também um JDK (`winget install --id EclipseAdoptium.Temurin.21.JDK -e`) ou use um Dev Container no VS Code.

## Primeiros passos

Todos os comandos no **PowerShell**, dentro da pasta do projeto.

### 1. Configurar o `.env`

```powershell
Copy-Item .env.example .env
notepad .env   # troque MONGO_PASSWORD e RABBITMQ_PASSWORD
```

### 2. Subir MongoDB e RabbitMQ

Com o Docker Desktop aberto:

```powershell
docker compose up -d
docker compose ps
```

Espere os dois serviços mostrarem `healthy` na coluna **STATUS** (o RabbitMQ leva uns 20 segundos). Para testar:

```powershell
docker compose exec mongo mongosh -u vagas -p SUA_SENHA --authenticationDatabase admin --eval "db.adminCommand({ ping: 1 })"
```

Painel do RabbitMQ: <http://localhost:15672> (usuário e senha do `.env`). As filas só aparecem depois que o núcleo Java subir pela primeira vez (etapa 2): é ele quem as cria.

Comandos úteis:

```powershell
docker compose logs -f            # ver logs (Ctrl+C para sair)
docker compose stop               # parar (os dados ficam)
docker compose down -v            # apagar TUDO, inclusive os dados
```

> **Porta em uso?** Você tem outro MongoDB ou RabbitMQ instalado no Windows. Mude `MONGO_PORT` (ex.: `27018`) ou `RABBITMQ_PORT` no `.env` e rode `docker compose up -d` de novo.
>
> **Trocou a senha do MongoDB ou do RabbitMQ no `.env` e não loga mais?** A senha só é aplicada na primeira vez que o volume é criado. Rode `docker compose down -v` (apaga os dados locais) e suba de novo.

### 3. Validar o contrato

Só com Docker:

```powershell
docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q 'jsonschema[format-nongpl]' && python scripts/validar_contrato.py"
```

Deve terminar com `Contrato válido.`

### 4. Antes de commitar

Confira que o `.env` **não** aparece em `git status` — ele está no `.gitignore` (e o CI falha se ele for commitado).

## GitHub Actions

| Workflow | Quando | O que faz |
|---|---|---|
| `ci.yml` | Push na `main`, pull requests, manual | Valida contrato e compose, sobe MongoDB + RabbitMQ; build/testes do Java e do Python quando existirem |
| `coleta.yml` | **Todo dia às 07:47 (Brasília)** e manual | Roda o núcleo em modo de execução única: coleta das fontes via API, filtra, salva e notifica. Não usa RabbitMQ. Até a etapa 2 só registra que não há nada para coletar |

### Estado entre as coletas

O MongoDB do job é descartado no fim de cada execução. Para lembrar das vagas já vistas/notificadas, o workflow salva um backup (`mongodump`) no **cache do GitHub Actions** e restaura (`mongorestore`) na execução seguinte.

- O cache expira se ficar **7 dias sem uso** (ex.: coleta parada uma semana). Aí a próxima coleta começa do zero e reenvia as vagas ainda abertas — uma vez só.
- Para um banco permanente, crie um cluster gratuito no **MongoDB Atlas** (512 MB, suficiente para anos de vagas) e cadastre o secret `MONGODB_URI` (formato `mongodb+srv://usuario:senha@cluster.../vagas`). Com ele, o cache deixa de ser usado. O Atlas pode desativar clusters gratuitos parados por muito tempo; a coleta diária mantém o seu em uso.

### Secrets

Em **Settings → Secrets and variables → Actions → New repository secret**. Todos são opcionais: fonte sem chave é pulada.

| Secret | Necessário a partir da |
|---|---|
| `VAGAS_GITHUB_TOKEN` | Etapa 3 — opcional; sem ele usa o token automático do Actions |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `CAREERJET_API_KEY` | Etapa 5 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Etapa 6 |
| `MONGODB_URI` | Opcional (banco permanente no MongoDB Atlas) |

> O scraper do LinkedIn (Python) **não** roda no Actions: o LinkedIn costuma bloquear IPs de servidores na nuvem. Ele será agendado no seu computador (etapa 8).
>
> O GitHub desativa workflows agendados em repositórios **públicos** sem nenhum commit por 60 dias. Se acontecer, reative em **Actions → Coleta diária de vagas → Enable workflow**.

## Roadmap

| # | Etapa | Status |
|---|---|---|
| 1 | Monorepo, contrato JSON, Docker Compose com MongoDB e RabbitMQ | ✅ |
| 2 | Núcleo Java: documento `Vaga` + índices no MongoDB, filtro júnior com testes, `IngestaoService`, topologia + consumer do RabbitMQ | |
| 3 | Fonte GitHub (Java) | |
| 4 | Fonte Gupy (Java) | |
| 5 | Fontes Adzuna e Careerjet (Java) | |
| 6 | Deduplicação entre fontes + notificação no Telegram | |
| 7 | Scraper do LinkedIn (Python) → publica no RabbitMQ | |
| 8 | Agendamento: coleta diária no GitHub Actions ✅ (workflow pronto) + Agendador de Tarefas do Windows para o scraper Python | parcial |
