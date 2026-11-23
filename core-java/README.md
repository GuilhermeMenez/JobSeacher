# core-java

Núcleo do sistema, em **Java + Spring Boot**. Entra na **etapa 2**.

Responsável por:

- Integrações via API: GitHub, Gupy, Adzuna, Careerjet, Greenhouse/Lever (chamam o `IngestaoService` direto)
- **Consumer do RabbitMQ**: lê a fila `nucleo.ingestao-vagas` (vagas do scraper Python) e chama o mesmo `IngestaoService`
- Declarar a topologia do RabbitMQ (exchanges, fila, DLQ) — ver `../contrato/README.md`
- `GET /api/vagas/ids` para o scraper saber o que já foi coletado
- Filtro júnior, score, deduplicação, PostgreSQL (Flyway) e notificação

Stack: Java 21/25 · Spring Boot · Maven · Spring AMQP · RestClient · Resilience4j · Spring Data JPA · Flyway · JUnit 5 · AssertJ · WireMock · Testcontainers (PostgreSQL e RabbitMQ).

## Modos de execução

| Modo | Como | O que roda |
|---|---|---|
| **Servidor** (padrão, no seu Docker) | `java -jar app.jar` | API HTTP + consumer da fila + coletores agendados |
| **Execução única** (GitHub Actions) | `--vagas.execucao=unica --spring.main.web-application-type=none --spring.rabbitmq.listener.simple.auto-startup=false` | Só os coletores via API, uma vez; salva, notifica e **encerra** (saída ≠ 0 se algo falhar). Não conecta no RabbitMQ |

## Requisitos para o consumer da fila

- **Ack manual** só depois de gravar no banco.
- **Idempotência** por `fonte` + `idExterno` (reentrega não duplica).
- Mensagem inválida (JSON, schema, versão) → `AmqpRejectAndDontRequeueException` → DLQ direto.
- Erro temporário → 3 tentativas com espera crescente (2s, 4s, 8s) → DLQ.
- `prefetch` baixo (ex.: 10): o volume é pequeno e evita segurar mensagens se o núcleo cair.

## Requisitos para a coleta diária (`.github/workflows/coleta.yml`)

1. Suportar o modo de **execução única** acima.
2. Ler a configuração das **variáveis de ambiente** abaixo.
3. **Pular, sem falhar, as fontes sem chave** (ex.: sem `ADZUNA_APP_ID` → só registra no log).
4. Gerar **um único JAR executável** em `core-java/target/` (padrão do `spring-boot-maven-plugin`).

| Variável | Uso |
|---|---|
| `SPRING_DATASOURCE_URL` / `_USERNAME` / `_PASSWORD` | Banco |
| `SPRING_RABBITMQ_HOST` / `_PORT` / `_USERNAME` / `_PASSWORD` | Fila (só no modo servidor) |
| `GITHUB_TOKEN` | Fonte GitHub |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Fonte Adzuna |
| `CAREERJET_API_KEY` | Fonte Careerjet |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Notificação |
