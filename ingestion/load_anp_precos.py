"""
Ingestão bronze — Série histórica de preços de combustíveis (ANP)

Trata duas particularidades reais dos arquivos da ANP:
  1. As planilhas trazem um bloco de metadados institucionais (título,
     período, notas) antes da linha real de cabeçalho. A posição desse
     bloco pode variar entre arquivos/anos, então detectamos a linha de
     cabeçalho dinamicamente em vez de fixar um número de linha.
  2. Os nomes de coluna trazem acentos e espaços, o que é frágil para SQL.
     Padronizamos (slugify) os nomes de coluna para snake_case ASCII — isso
     é tratado como normalização técnica, não transformação de negócio, e
     os VALORES continuam intocados (só os nomes das colunas mudam).

Uso:
    python ingestion/load_anp_precos.py --input data/raw/anp_2026.xlsx \
        --fonte semanal_revenda --ano-mes 2026
"""

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BRONZE_DIR = Path("../data/bronze/anp_precos")
METADATA_LOG = Path("../data/bronze/_ingestion_log.jsonl")

HEADER_KEYWORDS = {"DATA INICIAL", "MUNICÍPIO", "MUNICIPIO", "PRODUTO", "ESTADO"}


def slugify(text: str) -> str:
    """Normaliza um nome de coluna para snake_case ASCII."""
    text = str(text).strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def find_header_row(raw: pd.DataFrame, max_scan: int = 50) -> int:
    """Localiza a linha real de cabeçalho, ignorando o bloco de metadados
    institucionais que a ANP costuma colocar no topo do arquivo."""
    for i in range(min(max_scan, len(raw))):
        row_values = {
            str(v).strip().upper() for v in raw.iloc[i].tolist() if pd.notna(v)
        }
        if len(row_values & HEADER_KEYWORDS) >= 3:
            return i
    raise ValueError(
        "Não foi possível localizar a linha de cabeçalho nas primeiras "
        f"{max_scan} linhas do arquivo. Ajuste HEADER_KEYWORDS ou max_scan."
    )


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def already_ingested(hash_: str, fonte: str) -> bool:
    if not METADATA_LOG.exists():
        return False
    with open(METADATA_LOG, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["file_hash"] == hash_ and rec["fonte"] == fonte:
                return True
    return False

def read_raw(path: Path) -> tuple[pd.DataFrame, int]:
    """Lê o arquivo bruto, detecta o cabeçalho real e normaliza só os
    NOMES das colunas (slugify). Os valores permanecem exatamente como
    vieram da ANP — nenhuma transformação de conteúdo acontece aqui."""
    if path.suffix.lower() in (".xlsx", ".xls"):
        raw = pd.read_excel(path, header=None, dtype=object)
    elif path.suffix.lower() == ".csv":
        raw = pd.read_csv(path, header=None, dtype=object, sep=None, engine="python")
    else:
        raise ValueError(f"Formato não suportado: {path.suffix}")

    header_row_idx = find_header_row(raw)
    header = [str(c).strip() for c in raw.iloc[header_row_idx]]
    df = raw.iloc[header_row_idx + 1 :].reset_index(drop=True)
    df.columns = [slugify(c) for c in header]

    df["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    df["_source_file"] = path.name
    return df, header_row_idx


def write_bronze(df: pd.DataFrame, fonte: str, ano_mes: str) -> Path:
    out_dir = BRONZE_DIR / f"fonte={fonte}" / f"ano_mes={ano_mes}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"part-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.parquet"
    df.to_parquet(out_path, index=False)
    return out_path


def log_ingestion(record: dict) -> None:
    METADATA_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Ingestão bronze ANP")
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--fonte",
        required=True,
        choices=["semanal_revenda", "mensal_revenda", "posto_revendedor"],
    )
    parser.add_argument("--ano-mes", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Arquivo não encontrado: {input_path}", file=sys.stderr)
        sys.exit(1)

    
    h = file_hash(input_path)

    if already_ingested(h, args.fonte):
        print(f"Arquivo já foi ingerido ")
        sys.exit(0)

    print(f"Lendo {input_path} ...")
    df, header_row_idx = read_raw(input_path)
    n_rows, n_cols = df.shape
    schema_detected = list(df.columns)

    out_path = write_bronze(df, args.fonte, args.ano_mes)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "file_hash": file_hash(input_path),
        "fonte": args.fonte,
        "ano_mes": args.ano_mes,
        "header_row_detected": header_row_idx,
        "rows": n_rows,
        "cols": n_cols,
        "schema_detected": schema_detected,
        "output_path": str(out_path),
    }
    log_ingestion(record)

    print(f"OK — cabeçalho detectado na linha {header_row_idx}")
    print(f"OK — {n_rows} linhas, {n_cols} colunas gravadas em {out_path}")
    print(f"Schema detectado: {schema_detected}")


if __name__ == "__main__":
    main()

