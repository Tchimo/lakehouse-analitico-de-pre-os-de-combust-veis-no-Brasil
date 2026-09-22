"""
Flow Prefect — orquestra ingestão bronze -> dbt run -> dbt test -> relatório
de qualidade.

Uso local (fora de Docker):
    prefect server start   # em outro terminal
    python flows/pipeline_flow.py

Uso agendado: registre este flow como deployment com cron semanal, alinhado
à publicação da ANP (geralmente às segundas-feiras).
"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from prefect import flow, get_run_logger, task

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt_project"
QUALITY_REPORT_PATH = Path(__file__).parent.parent / "docs" / "data_quality_report.md"


def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    return result.returncode, output


@task(retries=1, retry_delay_seconds=30)
def ingest_ibge_municipios():
    logger = get_run_logger()
    code, out = run_cmd(["python", "ingestion/load_ibge_municipios.py"])
    logger.info(out)
    if code != 0:
        raise RuntimeError("Falha na ingestão de municípios IBGE")


@task
def dbt_seed():
    logger = get_run_logger()
    code, out = run_cmd(
        ["dbt", "seed", "--profiles-dir", "."], cwd=DBT_PROJECT_DIR
    )
    logger.info(out)
    if code != 0:
        raise RuntimeError("Falha no dbt seed")


@task
def dbt_run():
    logger = get_run_logger()
    code, out = run_cmd(
        ["dbt", "run", "--profiles-dir", "."], cwd=DBT_PROJECT_DIR
    )
    logger.info(out)
    if code != 0:
        raise RuntimeError("Falha no dbt run")
    return out


@task
def dbt_test():
    logger = get_run_logger()
    code, out = run_cmd(
        ["dbt", "test", "--profiles-dir", ".", "--store-failures"],
        cwd=DBT_PROJECT_DIR,
    )
    logger.info(out)
    # Não damos raise aqui de propósito: queremos capturar o resultado no
    # relatório de qualidade mesmo se algum teste falhar (severidade warn
    # já é tratada pelo próprio dbt). Falhas de severidade error devem
    # travar o deployment na fase de CI, não aqui.
    return code, out


@task
def generate_quality_report(test_exit_code: int, test_output: str):
    logger = get_run_logger()
    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    status = "✅ PASSOU" if test_exit_code == 0 else "⚠️ COM FALHAS"
    report = f"""# Data Quality Report

Gerado em: {datetime.now(timezone.utc).isoformat()}
Status geral: {status}

## Saída do dbt test

```
{test_output}
```
"""
    QUALITY_REPORT_PATH.write_text(report, encoding="utf-8")
    logger.info(f"Relatório gravado em {QUALITY_REPORT_PATH}")


@flow(name="fuel-lakehouse-pipeline")
def pipeline():
    ingest_ibge_municipios()
    dbt_seed()
    dbt_run()
    exit_code, output = dbt_test()
    generate_quality_report(exit_code, output)


if __name__ == "__main__":
    pipeline()
