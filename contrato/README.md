# Contrato entre coletores e núcleo — v1.0

Formato que **todas** as vagas seguem até chegar ao núcleo Java.

```
scraper-python ──publica──► [exchange vagas.coletadas] ──► [fila nucleo.ingestao-vagas] ──consome──► core-java
                                                                     │ falhou 3x / inválida
                                                                     ▼
                                                     [vagas.dlx] ──► [nucleo.ingestao-vagas.dlq]

coletores Java (API) ──chamada direta (mesmo processo)──► IngestaoService ◄── consumer da fila
```

- **Coletores externos** (hoje: o scraper Python) publicam **uma mensagem por vaga** no RabbitMQ.
- **Coletores Java** (GitHub, Gupy, Adzuna, Careerjet) rodam dentro do núcleo e chamam o mesmo serviço de ingestão direto, sem passar pela fila. Assim a coleta diária no GitHub Actions não precisa de RabbitMQ.
- O consumer da fila e os coletores Java usam **o mesmo `IngestaoService`**: as regras existem num lugar só.

## Quem faz o quê

| | Coletores (scraper Python, coletores Java) | Núcleo Java |
|---|---|---|
| Buscar vagas na fonte | ✅ | |
| Normalizar para este contrato (descrição em **texto puro**) | ✅ | |
| Validar contra o schema antes de publicar | ✅ | ✅ (de novo, ao consumir) |
| Filtro júnior, score, deduplicação, notificação | ❌ | ✅ |
| Declarar exchanges, filas e DLQ | ❌ | ✅ (o consumidor é dono da fila) |

> Regra de ouro: **coletor não decide se a vaga serve.** Ele só entrega.

## Schemas

| Schema | Uso |
|---|---|
| `vaga.schema.json` | Uma vaga |
| `mensagem-vaga.schema.json` | Corpo de cada mensagem na fila (envelope + vaga) |
| `ids-conhecidos.schema.json` | Resposta do `GET /api/vagas/ids` (HTTP) |

## Topologia no RabbitMQ

Declarada **pelo núcleo Java** ao subir (beans do Spring AMQP). Declarar de novo com os mesmos argumentos não muda nada, então reiniciar o núcleo é seguro.

| Recurso | Nome | Tipo / argumentos |
|---|---|---|
| Exchange principal | `vagas.coletadas` | `topic`, durável |
| Routing key | `vaga.<fonte>` | ex.: `vaga.linkedin`, `vaga.catho` |
| Fila | `nucleo.ingestao-vagas` | `quorum`, durável, binding `vaga.*`, `x-dead-letter-exchange=vagas.dlx` |
| Exchange de erro | `vagas.dlx` | `fanout`, durável |
| Fila de erro (DLQ) | `nucleo.ingestao-vagas.dlq` | `quorum`, durável |

## Como publicar (coletores externos)

| Propriedade AMQP | Valor |
|---|---|
| `exchange` | `vagas.coletadas` |
| `routing_key` | `vaga.<fonte>` (a mesma `fonte` da vaga) |
| `content_type` | `application/json` |
| `content_encoding` | `utf-8` |
| `delivery_mode` | `2` (persistente: sobrevive a reinício do RabbitMQ) |
| `message_id` | o mesmo `idMensagem` do corpo |
| `type` | `vaga.coletada` |
| `app_id` | quem publicou, ex.: `scraper-python` |
| `mandatory` | `true` |

Obrigatório no publicador:

1. **Publisher confirms** ligado: só considera a vaga enviada quando o RabbitMQ confirmar.
2. **`mandatory=true`**: se a fila ainda não existir (núcleo nunca subiu), a mensagem volta para o publicador em vez de sumir. O scraper deve **falhar com uma mensagem clara**: "suba o core-java uma vez para criar as filas".
3. Exchange declarada só de forma **passiva** (confere que existe; quem cria é o núcleo).

## Como consumir (núcleo Java)

- **Ack manual** só **depois** de gravar no banco (`at-least-once`).
- **Idempotência**: a chave é `fonte` + `idExterno`. Receber a mesma vaga duas vezes (reentrega, ou scraper que rodou duas vezes) não duplica nada.
- **Mensagem inválida** (JSON quebrado, falha no schema, versão incompatível): vai **direto para a DLQ**, sem nova tentativa.
- **Erro temporário** (ex.: banco fora): **3 tentativas** com espera crescente (2s, 4s, 8s); depois vai para a DLQ.
- Mensagens na DLQ podem ser inspecionadas e reenviadas pelo painel do RabbitMQ: <http://localhost:15672>.

## Consulta HTTP: `GET /api/vagas/ids`

Fila serve para **enviar**. Para **perguntar** ("quais vagas do LinkedIn você já tem?") continua sendo HTTP, porque o scraper precisa da resposta na hora.

| Parâmetros | Resposta |
|---|---|
| `fonte` (obrigatório), `desde` (opcional, `AAAA-MM-DD`) | `200` + `ids-conhecidos` |

Se o núcleo não estiver rodando, o scraper segue sem essa lista (baixa o detalhe de tudo, respeitando o limite de páginas). As vagas repetidas são descartadas pelo núcleo depois, pela idempotência.

## Campos da vaga

| Campo | Obrigatório | Pode ser `null` | Observação |
|---|---|---|---|
| `fonte` | sim | não | Um dos valores do enum. Fonte nova = nova versão MINOR do contrato |
| `idExterno` | sim | não | ID na fonte, sem espaços. `fonte` + `idExterno` é a chave única |
| `titulo` | sim | não | |
| `empresa` | sim | sim | `null` se confidencial ou não informada |
| `local` | sim | sim | Texto como veio |
| `modalidade` | sim | não | `remoto`, `hibrido`, `presencial` ou `desconhecida` |
| `url` | sim | não | `http(s)://...` |
| `publicadaEm` | sim | sim | `AAAA-MM-DD` |
| `descricao` | sim | sim | Texto puro. `null` se ainda não coletada |
| `coletadaEm` | sim | não | ISO 8601 com fuso, ex.: `2026-11-22T21:00:00-03:00` |
| `nivelInformado` | não | sim | Rótulo da fonte, só informativo |
| `contratacaoInformada` | não | sim | Ex.: `CLT`, `PJ`, `Estágio` |
| `salarioInformado` | não | sim | Texto como veio |
| `tags` | não | — | Lista de strings únicas |

Campos fora desta lista são **recusados** (`additionalProperties: false`): isso pega erro de digitação cedo.

## Versionamento

- `versaoContrato` no formato `MAJOR.MINOR` (hoje `1.0`).
- **MINOR** (1.0 → 1.1): só adiciona campos **opcionais** ou valores novos de enum. Publicadores antigos continuam funcionando.
- **MAJOR** (1.x → 2.0): remove/renomeia campo ou muda tipo. O núcleo manda para a DLQ mensagens com MAJOR maior que o dele.

## Validar

Na raiz do repositório, só com Docker:

```powershell
docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q 'jsonschema[format-nongpl]' && python scripts/validar_contrato.py"
```

Exemplos em `exemplos/validos/` precisam passar e os de `exemplos/invalidos/` precisam falhar. O prefixo do nome do arquivo indica o schema (`mensagem-vaga.linkedin.json` → `mensagem-vaga.schema.json`).
