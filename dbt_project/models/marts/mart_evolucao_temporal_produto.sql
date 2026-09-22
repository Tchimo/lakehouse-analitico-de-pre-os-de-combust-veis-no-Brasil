-- Gold: série temporal nacional por produto — insumo direto para o
-- gráfico de "série temporal por combustível".

select
    data_inicial,
    produto,
    avg(preco_medio_revenda) as preco_medio_brasil,
    min(preco_minimo_revenda) as preco_minimo_brasil,
    max(preco_maximo_revenda) as preco_maximo_brasil
from {{ ref('int_anp_geo_resolvido') }}
where not municipio_nao_resolvido
group by 1, 2
order by 1, 2
