# Contrato entre coletores e núcleo — v1.0

Este é o formato que **todas** as vagas seguem até chegar ao núcleo Java, venham de uma integração de API (Java) ou do scraper (Python).

## Quem faz o quê

| | Coletores (fontes Java e scraper Python) | Núcleo Java |
|---|---|---|
| Buscar vagas na fonte | ✅ | |
| Normalizar campos para este contrato | ✅ | |
| Descrição em **texto puro** (sem HTML) | ✅ | |
| Validar contra o schema antes de enviar | ✅ | ✅ (de novo, ao receber) |
| Filtro júnior, Java ≠ JavaScript, anos de experiência | ❌ | ✅ |
| Score, deduplicação entre fontes, notificação | ❌ | ✅ |

> Regra de ouro: **coletor não decide se a vaga serve.** Ele só entrega. Assim as regras existem num lugar só.

## Arquivos

| Schema | Uso |
|---|---|
| `vaga.schema.json` | Uma vaga |
| `lote-vagas.schema.json` | Corpo do `POST /api/ingestao/vagas` (1 a 100 vagas, uma fonte por lote) |
| `resposta-ingestao.schema.json` | Resposta do `POST /api/ingestao/vagas` |
| `ids-conhecidos.schema.json` | Resposta do `GET /api/vagas/ids` |

## Endpoints do núcleo (implementados na etapa 2)

| Método | Rota | Corpo / parâmetros | Resposta |
|---|---|---|---|
| `POST` | `/api/ingestao/vagas` | `lote-vagas` | `200` + `resposta-ingestao`. `400` se o lote inteiro for inválido (JSON quebrado, versão incompatível, `fonte` do lote diferente da das vagas) |
| `GET` | `/api/vagas/ids?fonte=linkedin&desde=2026-11-01` | `desde` é opcional | `200` + `ids-conhecidos` |

## Campos da vaga

| Campo | Obrigatório | Pode ser `null` | Observação |
|---|---|---|---|
| `fonte` | sim | não | Um dos valores do enum. Fonte nova = nova versão do contrato |
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
- **MINOR** (1.0 → 1.1): só adiciona campos **opcionais** ou valores novos de enum. Coletores antigos continuam funcionando.
- **MAJOR** (1.x → 2.0): remove/renomeia campo ou muda tipo. O núcleo recusa lotes com MAJOR maior que o dele.

## Validar

Na raiz do repositório:

```powershell
uv run --with "jsonschema[format-nongpl]" python scripts/validar_contrato.py
```

Exemplos em `exemplos/validos/` precisam passar e os de `exemplos/invalidos/` precisam falhar. O prefixo do nome do arquivo indica o schema (`lote-vagas.linkedin.json` → `lote-vagas.schema.json`).
