# scraper-python

Coletor de sites **sem API** (começando pelo LinkedIn), em **Python**. Entra na **etapa 7**.

Não tem banco nem regras de negócio:

1. Pergunta ao núcleo quais IDs já existem (`GET /api/vagas/ids`)
2. Raspa só as vagas novas
3. Envia em lotes para `POST /api/ingestao/vagas`, no formato de `../contrato/`

Stack: Python 3.12 · uv · httpx · tenacity · selectolax · pydantic · pytest · respx.
