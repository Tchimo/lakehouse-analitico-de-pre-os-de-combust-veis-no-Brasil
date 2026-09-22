-- Gold: municípios com preço anômalo em relação à média do produto na
-- semana (z-score), usado para o painel de "top anomalias".

with base as (
    select
        codigo_ibge,
        nome_municipio_ibge,
        uf_sigla,
        produto,
        data_inicial,
        preco_medio_revenda
    from {{ ref('int_anp_geo_resolvido') }}
    where not municipio_nao_resolvido
),

stats_semana as (
    select
        produto,
        data_inicial,
        avg(preco_medio_revenda)    as media_produto_semana,
        stddev(preco_medio_revenda) as desvio_produto_semana
    from base
    group by 1, 2
),

zscored as (
    select
        b.*,
        s.media_produto_semana,
        s.desvio_produto_semana,
        case
            when s.desvio_produto_semana > 0
            then round((b.preco_medio_revenda - s.media_produto_semana) / s.desvio_produto_semana, 3)
            else null
        end as z_score
    from base b
    join stats_semana s
        on b.produto = s.produto and b.data_inicial = s.data_inicial
)

select *
from zscored
where abs(z_score) >= 2   -- threshold configurável de anomalia
order by abs(z_score) desc