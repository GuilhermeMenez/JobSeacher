# scraper-python

Coletor de sites **sem API** (começando pelo LinkedIn), em **Python**. Entra na **etapa 7**.

Não tem banco nem regras de negócio. É um **publicador**:

1. Pergunta ao núcleo quais IDs já existem (`GET /api/vagas/ids`). Se o núcleo estiver fora, segue sem a lista.
2. Raspa só as vagas novas.
3. Valida cada vaga contra `../contrato/mensagem-vaga.schema.json` (via pydantic).
4. Publica **uma mensagem por vaga** na exchange `vagas.coletadas` do RabbitMQ, com routing key `vaga.<fonte>`.

Regras de publicação (detalhes em `../contrato/README.md`):

- **Publisher confirms** ligado e mensagens **persistentes** (`delivery_mode=2`).
- `mandatory=true`: se a fila não existir (núcleo nunca subiu), falha com mensagem clara em vez de perder a vaga.
- Exchange conferida de forma **passiva**: quem cria a topologia é o núcleo.
- Se o RabbitMQ estiver fora: tenta reconectar algumas vezes e então encerra com erro (as vagas são coletadas de novo na próxima execução).

Stack: Python 3.12 · uv · httpx · tenacity · selectolax · pydantic · **pika** (RabbitMQ) · pytest · respx.
