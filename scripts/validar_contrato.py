"""Valida os schemas do contrato e os exemplos.

Regra dos nomes: o prefixo do arquivo de exemplo (antes do primeiro ponto)
diz qual schema usar. Ex.: mensagem-vaga.linkedin.json -> mensagem-vaga.schema.json

- exemplos/validos/   -> TODOS precisam passar
- exemplos/invalidos/ -> TODOS precisam falhar

Uso (na raiz do repositório), só com Docker:
    docker run --rm -v "${PWD}:/app" -w /app python:3.12-slim sh -c "pip install -q 'jsonschema[format-nongpl]' && python scripts/validar_contrato.py"

Ou com uv:
    uv run --with "jsonschema[format-nongpl]" python scripts/validar_contrato.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

RAIZ = Path(__file__).resolve().parent.parent
CONTRATO = RAIZ / "contrato"
EXEMPLOS = CONTRATO / "exemplos"


def carregar(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def montar_validadores() -> dict[str, Draft202012Validator]:
    schemas = {p.name.removesuffix(".schema.json"): carregar(p) for p in CONTRATO.glob("*.schema.json")}

    # Registra cada schema pelo $id e pelo nome do arquivo, para os $ref relativos funcionarem
    recursos = []
    for nome, schema in schemas.items():
        recurso = Resource.from_contents(schema)
        recursos.append((schema["$id"], recurso))
        recursos.append((f"{nome}.schema.json", recurso))
    registro = Registry().with_resources(recursos)

    validadores = {}
    for nome, schema in schemas.items():
        Draft202012Validator.check_schema(schema)  # o próprio schema é válido?
        validadores[nome] = Draft202012Validator(schema, registry=registro, format_checker=FormatChecker())
    return validadores


def main() -> int:
    validadores = montar_validadores()
    print(f"Schemas OK: {', '.join(sorted(validadores))}\n")

    falhas = 0
    for pasta, deve_passar in (("validos", True), ("invalidos", False)):
        for arquivo in sorted((EXEMPLOS / pasta).glob("*.json")):
            prefixo = arquivo.name.split(".")[0]
            validador = validadores.get(prefixo)
            if validador is None:
                print(f"[ERRO] {pasta}/{arquivo.name}: nenhum schema '{prefixo}.schema.json'")
                falhas += 1
                continue

            erros = sorted(validador.iter_errors(carregar(arquivo)), key=lambda e: list(e.path))
            passou = not erros

            if passou == deve_passar:
                msg = erros[0].message if erros else ""
                detalhe = "" if passou else f" -> {msg[:100]}{'...' if len(msg) > 100 else ''}"
                print(f"[ok]   {pasta}/{arquivo.name}{detalhe}")
            else:
                falhas += 1
                esperado = "passar" if deve_passar else "falhar"
                print(f"[FALHA] {pasta}/{arquivo.name}: deveria {esperado}")
                for erro in erros:
                    caminho = "/".join(str(p) for p in erro.path) or "(raiz)"
                    print(f"         {caminho}: {erro.message}")

    print()
    if falhas:
        print(f"{falhas} problema(s) encontrado(s).")
        return 1
    print("Contrato válido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
