# JobSeacher — contexto para o Claude Code

Agregador de vagas de **desenvolvedor Java júnior**: coleta de várias fontes, filtra as que são júnior de verdade, remove duplicadas e avisa as novas no Telegram.

Este arquivo resume as decisões tomadas até agora (conversa de planejamento de 22–23/11/2026). Leia antes de propor mudanças de arquitetura.

## Sobre o usuário

- Usa **Windows + PowerShell** e **Docker Desktop**. Comandos e instruções devem funcionar no PowerShell.
- Quer **aprender a stack** (Spring Boot, RabbitMQ, MongoDB). Explique as decisões, não só entregue código.
- Prefere **validar antes do commit**: mostre os arquivos/diff e espere o ok antes de commitar ou fazer push.
- Conversa em **português**. Nomes de classes, pacotes e campos também em português (ex.: `IngestaoService`, `idExterno`).

## Arquitetura

```
Sites com API (GitHub, Gupy, Adzuna, Careerjet) ─► coletores Java ─┐
                                                                   ▼
Sites sem API (LinkedIn...) ─► scraper Python ─► RabbitMQ ─► consumer Java ─► IngestaoService ─► MongoDB ─► Telegram
                                                    └─► DLQ
```

| Peça | Responsabilidade |
|---|---|
| `core-java/` (Spring Boot 4) | **Dono de todas as regras**: coletores via API, consumer da fila, filtro júnior, deduplicação, score, MongoDB, notificação. **Declara a topologia do RabbitMQ.** |
| `scraper-python/` | **Só publica** na fila. Sem banco, sem regras. Confere a exchange de forma passiva, nunca cria fila |
| `contrato/` | JSON Schema das mensagens + topologia do RabbitMQ. Fonte da verdade entre Java e Python |
| `docker-compose.yml` | MongoDB 8 + RabbitMQ 4 (management) locais |
| `.github/workflows/ci.yml` | Valida contrato e compose, sobe a infra, build/testes de Java e Python quando existirem |
| `.github/workflows/coleta.yml` | Coleta diária 07:47 (Brasília): núcleo em execução única, só fontes via API, Mongo temporário com estado em cache (`mongodump`/`mongorestore`) |

## Decisões já tomadas (não reabrir sem o usuário pedir)

- **Java para integrações de API e regras; Python só para scraping.**
- **Fila RabbitMQ entre Python e Java.** A fila é do Java (ele declara exchange, fila e DLQ); o Python só envia. Uma mensagem = uma vaga (`contrato/mensagem-vaga.schema.json`).
- **Coletores Java não passam pela fila**: chamam o `IngestaoService` direto. Por isso a coleta no GitHub Actions não precisa de RabbitMQ.
- `GET /api/vagas/ids?fonte=` continua **HTTP** (o scraper precisa da resposta na hora).
- **MongoDB** em vez de PostgreSQL (escolha do usuário, para aprender). Documento = vaga canônica + lista `ocorrencias` por fonte. Índices únicos em `ocorrencias.fonte`+`ocorrencias.idExterno` e em `chaveDedup`. Sem Flyway; índices criados em código. Propriedade no Spring Boot 4: `spring.mongodb.uri` (via env `MONGODB_URI`).
- **Idempotência**: entrega at-least-once; reprocessar a mesma vaga não duplica.
- **Consumer não notifica** por mensagem: grava com status `nova`; um passo separado manda **resumo**. Vagas reprovadas no filtro são gravadas com status `descartada`.
- **Coleta diária num lugar só** (GitHub Actions). LinkedIn fica fora do Actions (bloqueia IPs de nuvem); decidir onde ele roda na etapa 7.
- Rodar tudo **só com Docker** deve continuar possível (Dockerfiles do núcleo e do scraper entram nas etapas 2 e 7).
- Contrato na versão `1.0` (o formato de lote foi substituído antes de ter consumidores).

## Estado atual

- `main`: etapa 1 original (commit `499d32d`).
- `feature/fila-e-mongodb`: CI, coleta diária, fila RabbitMQ e troca para MongoDB. **Ainda sem PR** (o CI só roda em push na `main` ou em PR).
- Nada de código Java/Python ainda: `core-java/` e `scraper-python/` só têm README com os requisitos.

## Pendências

1. **Corrigir a documentação do consumer** (`contrato/README.md` e `core-java/README.md`):
   - trocar "ack manual" por **ack automático do Spring** (`AcknowledgeMode.AUTO`: confirma quando o listener retorna sem erro, depois de gravar no banco);
   - "3 tentativas com espera 2s, 4s, 8s" → `max-attempts: 3` dá **duas** esperas (2s e 4s);
   - erros de validação devem ser marcados como **não repetíveis** no retry.
2. Opcional: redesenhar o diagrama com o RabbitMQ dentro da área do núcleo Java (deixar claro que a fila é dele).
3. Abrir PR `feature/fila-e-mongodb` → `main` e acompanhar o primeiro CI (MongoDB/RabbitMQ nunca foram testados de verdade: o ambiente de planejamento não tinha Docker).
4. **Etapa 2** — núcleo Spring Boot em `core-java/`: documento `Vaga` + índices, filtro júnior com testes (Java sem pegar JavaScript, descartar >2 anos de experiência), `IngestaoService`, topologia + consumer do RabbitMQ, modo de execução única, Dockerfile. Critérios padrão sugeridos: estágio incluído, até 2 anos, bônus para Spring/SQL/Git/Docker/JUnit, qualquer modalidade — confirmar com o usuário.

## Roadmap

| # | Etapa |
|---|---|
| 1 | Monorepo, contrato, Docker Compose ✅ |
| 2 | Núcleo Java (ver pendência 4) |
| 3 | Fonte GitHub Issues (backend-br/vagas etc.) |
| 4 | Fonte Gupy (`portal.api.gupy.io/api/v1/jobs`) |
| 5 | Fontes Adzuna e Careerjet (APIs oficiais, chaves no `.env`/secrets) |
| 6 | Deduplicação entre fontes + resumo no Telegram |
| 7 | Scraper do LinkedIn (Python) publicando no RabbitMQ |
| 8 | Agendamento (Actions pronto; scraper local a definir) |

## Como validar

```powershell
# Contrato (só Docker)
docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q 'jsonschema[format-nongpl]' && python scripts/validar_contrato.py"

# Infra local
Copy-Item .env.example .env   # e troque as senhas
docker compose up -d
docker compose ps             # mongo e rabbitmq "healthy"
```

Workflows: valide com `actionlint` antes de commitar.

## Convenções

- Commits em português, descritivos. Nunca commitar `.env` (o CI falha se acontecer).
- Mudanças de formato de mensagem passam por `contrato/` (schema + exemplos válidos e inválidos) antes do código.
