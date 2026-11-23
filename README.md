# vagas-bot

Coleta vagas de **desenvolvedor Java júnior** de várias fontes, filtra as que são júnior de verdade, remove duplicadas e avisa as novas.

```
┌──────────────────────── core-java (Spring Boot) ────────────────────────┐
│  Fontes via API: GitHub · Gupy · Adzuna · Careerjet · Greenhouse/Lever  │
│                                 │                                        │
│  POST /api/ingestao/vagas ◄─────┼──────────────── scraper-python        │
│                                 ▼                  (LinkedIn, ...)       │
│        Filtro júnior → Deduplicação → Score → PostgreSQL → Telegram      │
└──────────────────────────────────────────────────────────────────────────┘
```

| Pasta | O que é | Etapa |
|---|---|---|
| `contrato/` | Formato JSON das vagas, compartilhado entre Java e Python | 1 ✅ |
| `docker-compose.yml` | PostgreSQL local | 1 ✅ |
| `core-java/` | Núcleo: APIs, ingestão, filtro, banco, notificação | 2–6 |
| `scraper-python/` | Scraper dos sites sem API | 7 |
| `scripts/` | Utilitários (validação do contrato) | 1 ✅ |

## Pré-requisitos (Windows)

| Ferramenta | Para quê | Instalação (PowerShell) |
|---|---|---|
| Docker Desktop | PostgreSQL | já instalado ✅ |
| Git | versionamento | `winget install --id Git.Git -e` |
| uv | Python e validação do contrato | `winget install --id astral-sh.uv -e` |
| JDK 21 ou 25 | núcleo Java (etapa 2) | `winget install --id EclipseAdoptium.Temurin.21.JDK -e` |

Depois de instalar, **feche e abra o terminal** para o `PATH` atualizar. O uv baixa o Python sozinho quando precisa.

## Primeiros passos

Todos os comandos no **PowerShell**, dentro da pasta do projeto.

### 1. Configurar o `.env`

```powershell
Copy-Item .env.example .env
notepad .env   # troque POSTGRES_PASSWORD
```

### 2. Subir o PostgreSQL

Com o Docker Desktop aberto:

```powershell
docker compose up -d
docker compose ps
```

Espere a coluna **STATUS** mostrar `healthy` (uns 10 segundos). Para testar a conexão:

```powershell
docker compose exec postgres psql -U vagas -d vagas -c "select version();"
```

Comandos úteis:

```powershell
docker compose logs -f postgres   # ver logs (Ctrl+C para sair)
docker compose stop               # parar (os dados ficam)
docker compose down -v            # apagar TUDO, inclusive os dados
```

> **Erro de porta 5432 em uso?** Você tem outro Postgres instalado no Windows. Mude `POSTGRES_PORT=5433` no `.env` e rode `docker compose up -d` de novo.

### 3. Validar o contrato

```powershell
uv run --with "jsonschema[format-nongpl]" python scripts/validar_contrato.py
```

Deve terminar com `Contrato válido.`

### 4. Versionar

```powershell
git init
git add .
git commit -m "Etapa 1: monorepo, contrato v1.0 e PostgreSQL"
```

Confira que o `.env` **não** aparece em `git status` — ele está no `.gitignore`.

## Roadmap

| # | Etapa | Status |
|---|---|---|
| 1 | Monorepo, contrato JSON, Docker Compose com PostgreSQL | ✅ |
| 2 | Núcleo Java: entidade `Vaga`, Flyway, filtro júnior com testes, endpoint de ingestão | |
| 3 | Fonte GitHub (Java) | |
| 4 | Fonte Gupy (Java) | |
| 5 | Fontes Adzuna e Careerjet (Java) | |
| 6 | Deduplicação entre fontes + notificação no Telegram | |
| 7 | Scraper do LinkedIn (Python) → ingestão | |
| 8 | Agendamento: `@Scheduled` (Java) + Agendador de Tarefas do Windows (Python) | |
