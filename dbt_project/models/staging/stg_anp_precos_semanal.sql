-- Silver: normalização da série semanal de preços de revenda (ANP).
--
-- A ANP inclui um bloco de metadados institucionais antes do cabeçalho
-- real; a detecção e remoção disso acontece na ingestão (bronze), não
-- aqui — este model já recebe colunas slugificadas em snake_case.
--
-- `estado` vem como nome completo da UF (ex: "SAO PAULO", "PARA"), sem
-- sigla — por isso resolvemos a sigla via o seed uf_mapping, normalizando
-- os dois lados (acentos/caixa) para tornar o join robusto.
--
-- `margem_media_revenda` frequentemente vem como o marcador '-' quando a
-- ANP não calcula margem só com dado de revenda — tratamos como nulo.

with source as (
    select * from {{ source('bronze', 'anp_precos_semanal_revenda') }}
),

uf_map as (
    select * from {{ ref('uf_mapping') }}
),

normalized as (
    select
        cast(source.data_inicial as date)   as data_inicial,
        cast(source.data_final as date)     as data_final,
        upper(trim(source.regiao))          as regiao,
        upper(trim(source.estado))          as uf_nome_raw,
        uf_map.uf_sigla,
        upper(trim(source.municipio))       as nome_municipio_raw,
        {{ normalize_text('source.municipio') }} as nome_municipio_normalizado,
        upper(trim(source.produto))         as produto,
        cast(source.numero_de_postos_pesquisados as integer) as numero_postos_pesquisados,
        trim(source.unidade_de_medida)      as unidade_medida,
        cast(source.preco_medio_revenda as decimal(10,3))     as preco_medio_revenda,
        cast(source.desvio_padrao_revenda as decimal(10,3))   as desvio_padrao_revenda,
        cast(source.preco_minimo_revenda as decimal(10,3))    as preco_minimo_revenda,
        cast(source.preco_maximo_revenda as decimal(10,3))    as preco_maximo_revenda,
        try_cast(nullif(trim(cast(source.margem_media_revenda as varchar)), '-') as decimal(10,3)) as margem_media_revenda,
        try_cast(nullif(trim(cast(source.coef_de_variacao_revenda as varchar)), '-') as decimal(10,4)) as coef_variacao_revenda,
        source._source_file,
        cast(source._ingested_at as timestamp) as ingested_at
    from source
    left join uf_map
        on {{ normalize_text('source.estado') }} = {{ normalize_text('uf_map.uf_nome') }}
)

select * from normalized