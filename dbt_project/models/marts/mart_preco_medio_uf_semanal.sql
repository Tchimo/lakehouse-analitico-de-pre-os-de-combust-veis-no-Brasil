-- Gold: preço médio por UF e produto, granularidade semanal.

select
    data_inicial,
    data_final,
    uf_sigla,
    produto,
    avg(preco_medio_revenda)       as preco_medio_uf,
    min(preco_minimo_revenda)      as preco_minimo_uf,
    max(preco_maximo_revenda)      as preco_maximo_uf,
    stddev(preco_medio_revenda)    as desvio_padrao_uf,
    count(*)                       as n_municipios
from {{ ref('int_anp_geo_resolvido') }}
where not municipio_nao_resolvido
group by 1, 2, 3, 4
