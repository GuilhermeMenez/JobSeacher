# core-java

Núcleo do sistema, em **Java + Spring Boot**. Entra na **etapa 2**.

Responsável por:

- Integrações via API: GitHub, Gupy, Adzuna, Careerjet, Greenhouse/Lever (chamam o `IngestaoService` direto)
- **Consumer do RabbitMQ**: lê a fila `nucleo.ingestao-vagas` (vagas do scraper Python) e chama o mesmo `IngestaoService`
- Declarar a topologia do RabbitMQ (exchanges, fila, DLQ) — ver `../contrato/README.md`
- `GET /api/vagas/ids` para o scraper saber o que já foi coletado
- Filtro júnior, score, deduplicação, MongoDB e notificação

Stack: Java 21/25 · Spring Boot 4 · Maven · Spring Data MongoDB · Spring AMQP · RestClient · Resilience4j · JUnit 5 · AssertJ · WireMock · Testcontainers (MongoDB e RabbitMQ).

## Modelo no MongoDB

Banco `vagas`. Uma vaga aparece em várias fontes (LinkedIn e Gupy, por exemplo), então o documento guarda a vaga "canônica" e a lista de onde ela foi vista:

```json
{
  "_id": "…",
  "chaveDedup": "empresa-exemplo|desenvolvedor java junior",
  "titulo": "Desenvolvedor Java Júnior",
  "empresa": "Empresa Exemplo",
  "modalidade": "hibrido",
  "score": 4,
  "status": "nova",
  "notificadaEm": null,
  "ocorrencias": [
    { "fonte": "linkedin", "idExterno": "4012345678", "url": "…", "coletadaEm": "…" },
    { "fonte": "gupy", "idExterno": "9876543", "url": "…", "coletadaEm": "…" }
  ],
  "original": { "…": "mensagem como chegou, para reprocessar se o filtro mudar" }
}
```

| Índice | Para quê |
|---|---|
| único em `ocorrencias.fonte` + `ocorrencias.idExterno` | idempotência: a mesma vaga da mesma fonte nunca entra duas vezes |
| único em `chaveDedup` | junta a mesma vaga vinda de fontes diferentes |
| `score` + `coletadaEm` | listar as melhores vagas recentes |

Sem Flyway: os índices são criados pelo núcleo ao subir (código, não `auto-index-creation`). Mudanças de formato dos documentos ficam documentadas aqui e, se um dia precisar migrar dados, usamos um script versionado (ex.: Mongock).

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
| `MONGODB_URI` | Banco. No `application.yml`: `spring.mongodb.uri: ${MONGODB_URI}` (nome da propriedade no Spring Boot 4) |
| `SPRING_RABBITMQ_HOST` / `_PORT` / `_USERNAME` / `_PASSWORD` | Fila (só no modo servidor) |
| `GITHUB_TOKEN` | Fonte GitHub |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Fonte Adzuna |
| `CAREERJET_API_KEY` | Fonte Careerjet |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Notificação |
