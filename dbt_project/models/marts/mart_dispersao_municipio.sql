-- Gold: dispersão de preços por município (coeficiente de variação),
-- útil para identificar municípios com maior heterogeneidade de preços
-- entre postos.

select
    codigo_ibge,
    nome_municipio_ibge,
    uf_sigla,
    produto,
    data_inicial,
    preco_medio_revenda,
    desvio_padrao_revenda,
    case
        when preco_medio_revenda > 0
        then round(desvio_padrao_revenda / preco_medio_revenda, 4)
        else null
    end as coeficiente_variacao
from {{ ref('int_anp_geo_resolvido') }}
where not municipio_nao_resolvido
