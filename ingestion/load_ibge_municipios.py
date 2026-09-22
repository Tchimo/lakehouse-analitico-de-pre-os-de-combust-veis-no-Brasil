"""
Ingestão bronze — Tabela de municípios do IBGE

Carrega a tabela oficial de municípios (código IBGE, nome, UF, região) usada
como referência geográfica para o join com os dados da ANP na camada silver.

Fonte sugerida: API de localidades do IBGE
  https://servicodados.ibge.gov.br/api/v1/localidades/municipios

Uso:
    python ingestion/load_ibge_municipios.py --output data/bronze/ibge_municipios

Se a API estiver indisponível, aceita também um CSV local via --input.
"""

import argparse
#import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
BRONZE_DIR = Path("data/bronze/ibge_municipios")


def fetch_from_api() -> pd.DataFrame:
    resp = requests.get(IBGE_API_URL, timeout=60)
    resp.raise_for_status()
    raw = resp.json()

    rows = []
    for m in raw:
        try:
            uf_sigla = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            uf_nome = m["microrregiao"]["mesorregiao"]["UF"]["nome"]
            regiao = m["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"]
        except (KeyError, TypeError):
            # Alguns municípios (raros) têm estrutura de regiao-imediata em vez
            # de microrregiao — trate exceções, não deixe a carga inteira cair.
            uf_sigla = m.get("regiao-imediata", {}).get("regiao-intermediaria", {}).get("UF", {}).get("sigla")
            uf_nome = None
            regiao = None

        rows.append(
            {
                "codigo_ibge": m["id"],
                "nome_municipio": m["nome"],
                "uf_sigla": uf_sigla,
                "uf_nome": uf_nome,
                "regiao": regiao,
            }
        )
    return pd.DataFrame(rows)


def fetch_from_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def main():
    parser = argparse.ArgumentParser(description="Ingestão bronze IBGE municípios")
    parser.add_argument("--input", help="CSV local (alternativa à API)")
    args = parser.parse_args()

    if args.input:
        df = fetch_from_csv(Path(args.input))
    else:
        print("Buscando municípios na API do IBGE...")
        df = fetch_from_api()

    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BRONZE_DIR / f"municipios-{datetime.now(timezone.utc):%Y%m%d}.parquet"
    df.to_parquet(out_path, index=False)

    print(f"OK — {len(df)} municípios gravados em {out_path}")


if __name__ == "__main__":
    main()
