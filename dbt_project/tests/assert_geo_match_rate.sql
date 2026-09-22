-- Teste singular: falha se mais de 2% dos registros não resolveram
-- município (nem por join direto, nem por dicionário de exceções).
-- dbt tests "falham" quando a query retorna linhas — aqui retornamos
-- uma linha somente se a taxa de não-resolução ultrapassar o threshold.

with stats as (
    select
        count(*) as total,
        sum(case when municipio_nao_resolvido then 1 else 0 end) as nao_resolvidos
    from {{ ref('int_anp_geo_resolvido') }}
)

select *
from stats
where total > 0
  and (nao_resolvidos::float / total::float) > 0.02
