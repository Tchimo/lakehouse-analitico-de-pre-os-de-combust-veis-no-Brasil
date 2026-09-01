# Lakehouse Analítico de Preços de Combustíveis (ANP)

Plataforma analítica reprodutível para ingestão, tratamento, validação e
disponibilização de dados públicos da ANP sobre preços de combustíveis no
Brasil, enriquecida com a referência geográfica oficial do IBGE.

## Arquitetura

Medallion architecture (bronze → silver → gold), com camadas imutáveis:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   BRONZE    │ --> │    SILVER    │ --> │    GOLD     │
│  raw/       │     │  normalizado │     │  marts      │
│  imutável   │     │  tipado      │     │  analítico  │
│  versionado │     │  geo-resolvido│    │  consumível │
└─────────────┘     └──────────────┘     └─────────────┘
     Python              dbt (staging)      dbt (marts)
   (ingestion/)         normalize_text()   agregações
```

- **Bronze**: `ingestion/load_anp_precos.py` e `load_ibge_municipios.py` gravam
  Parquet particionado, sem nenhuma transformação de conteúdo. Cada carga é um
  snapshot novo — bronze nunca é sobrescrito.
- **Silver**: modelos dbt em `dbt_project/models/staging/` padronizam tipos,
  nomes de coluna e resolvem a chave geográfica (`int_anp_geo_resolvido.sql`).
- **Gold**: modelos dbt em `dbt_project/models/marts/` geram os agregados
  consumidos pelo dashboard.

## Stack

| Camada          | Ferramenta         |
|-----------------|---------------------|
| Motor analítico | DuckDB               |
| Transformação   | dbt (dbt-duckdb)      |
| Orquestração    | Prefect               |
| Qualidade       | dbt tests + Great Expectations |
| CI/CD           | GitHub Actions        |
| Dashboard       | Metabase               |
| Ambiente        | Docker / docker-compose |

## Ameaças à qualidade de dados (conhecidas)

1. **ANP sem API estável**: ingestão depende de download manual/scriptado de
   planilhas publicadas no portal de dados abertos. Mudanças na URL ou no
   formato do arquivo quebram a ingestão silenciosamente se não monitoradas.
2. **Inconsistência de schema entre arquivos históricos da ANP**: nomes de
   coluna mudam de case e grafia entre períodos. Tratado centralizadamente em
   `stg_anp_precos_semanal.sql` — qualquer mudança nova deve ser ajustada
   *apenas* ali.
3. **Join geográfico impreciso** (ANP município-texto vs IBGE código): tratado
   em `int_anp_geo_resolvido.sql` com estratégia em cascata (match direto →
   dicionário de exceções `municipio_exceptions.csv` → não resolvido). O teste
   `tests/assert_geo_match_rate.sql` falha se a taxa de não-resolução passar
   de 2%.

## Estratégia de atualização

A ANP publica a série semanal geralmente às segundas-feiras. O pipeline é
pensado para rodar semanalmente via GitHub Actions agendado (cron) ou via
deployment do Prefect. Cada execução:

1. Ingestão bronze (novo snapshot, imutável)
2. `dbt seed` (atualiza dicionário de exceções, se alterado)
3. `dbt run` (reconstrói silver e gold)
4. `dbt test` (valida qualidade, gera relatório)

## Custo / portabilidade

Escolha deliberada por DuckDB + arquivos locais: zero infraestrutura paga,
roda inteiramente em um único arquivo `.duckdb` + Parquet no disco, portável
para qualquer máquina ou runner de CI. Trade-off: não é pensado para
concorrência de escrita ou volumes multi-TB — migrar para Postgres/BigQuery
seria o caminho natural para produção em escala.

## Como rodar

```bash
git clone <repo>
cd fuel-lakehouse
cp .env.example .env   # ajuste variáveis se necessário

# Suba os serviços (Prefect + Metabase)
docker-compose up -d

# Baixe manualmente os arquivos brutos da ANP para data/raw/, depois:
python ingestion/load_anp_precos.py --input data/raw/anp_2026_08.xlsx \
    --fonte semanal_revenda --ano-mes 2026-08
python ingestion/load_ibge_municipios.py

# Rode o pipeline dbt
cd dbt_project
dbt deps --profiles-dir .
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .

# Acesse o Metabase em http://localhost:3000 e conecte ao arquivo
# data/warehouse.duckdb
```

## Estrutura do repositório

```
fuel-lakehouse/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── ingestion/              # scripts de ingestão bronze
├── flows/                  # orquestração Prefect
├── dbt_project/
│   ├── models/staging/     # silver
│   ├── models/marts/       # gold
│   ├── seeds/              # dicionário de exceções geográficas
│   └── tests/              # testes singulares
├── data/                   # bronze/silver/gold (não versionado em git)
├── docs/                   # relatório de qualidade gerado
└── .github/workflows/      # CI
```

## Próximos passos

- [ ] Popular `data/raw/` com histórico completo da ANP e validar o schema map
- [ ] Ampliar `municipio_exceptions.csv` conforme o teste de match rate apontar gaps
- [ ] Ingerir a fonte de preço de distribuição para habilitar `mart_margem_revenda_distribuicao`
- [ ] Publicar dashboards no Metabase e capturar prints para `docs/`
- [ ] (Opcional) Expor os marts gold via API FastAPI
