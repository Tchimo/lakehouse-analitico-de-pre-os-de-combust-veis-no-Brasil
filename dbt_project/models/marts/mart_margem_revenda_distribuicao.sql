{#
  Gold: diferença entre preço de revenda e preço de distribuição.

  TODO (não implementado neste esqueleto): este mart depende de uma fonte
  bronze adicional — "preco_distribuicao" — que a ANP publica separadamente
  do levantamento de revenda. Passos para habilitar:
    1. Adicionar ingestion/load_anp_precos.py --fonte preco_distribuicao
    2. Criar source em _sources.yml -> anp_precos_distribuicao
    3. Criar stg_anp_precos_distribuicao.sql análogo ao stg_anp_precos_semanal.sql
    4. Fazer join por produto + uf + periodo com int_anp_geo_resolvido

  Estrutura alvo do mart, uma vez implementado:

  select
      r.data_inicial,
      r.uf_nome,
      r.produto,
      r.preco_medio_revenda,
      d.preco_medio_distribuicao,
      r.preco_medio_revenda - d.preco_medio_distribuicao as margem_absoluta,
      round((r.preco_medio_revenda - d.preco_medio_distribuicao)
             / nullif(d.preco_medio_distribuicao, 0), 4) as margem_percentual
  from {{ ref('mart_preco_medio_uf_semanal') }} r
  join {{ ref('stg_anp_precos_distribuicao') }} d
    on r.uf_nome = d.uf_nome and r.produto = d.produto and r.data_inicial = d.data_inicial
#}

select
    cast(null as date)    as data_inicial,
    cast(null as varchar) as uf_nome,
    cast(null as varchar) as produto,
    cast(null as decimal(10,3)) as preco_medio_revenda,
    cast(null as decimal(10,3)) as preco_medio_distribuicao,
    cast(null as decimal(10,3)) as margem_absoluta
where false  -- mart vazio até a fonte de distribuição ser ingerida
