-- Resolve o código IBGE para cada registro da ANP.
--
-- Estratégia em cascata (a fragilidade do projeto está toda aqui):
--   1. Join direto por nome normalizado + UF (cobre a maioria dos casos)
--   2. Fallback via dicionário de exceções curado manualmente (seed
--      `municipio_exceptions.csv`) para nomes que não batem por grafia,
--      abreviação ou mudança de nome do município ao longo do tempo
--   3. O que sobrar sem match cai em `municipio_nao_resolvido = true` e
--      deve ser investigado — não é aceitável esse volume subir silenciosamente
--      para gold (ver teste `test_geo_match_rate` em schema.yml).

with precos as (
    select * from {{ ref('stg_anp_precos_semanal') }}
),

municipios as (
    select * from {{ ref('stg_ibge_municipios') }}
),

exceptions as (
    select * from {{ ref('municipio_exceptions') }}
),

-- tentativa 1: join direto
match_direto as (
    select
        p.*,
        m.codigo_ibge,
        m.nome_municipio as nome_municipio_ibge,
        m.regiao          as regiao_ibge,
        'direto'          as metodo_match
    from precos p
    left join municipios m
        on p.nome_municipio_normalizado = m.nome_municipio_normalizado
        and p.uf_sigla = m.uf_sigla
),

-- tentativa 2: fallback via dicionário de exceções para quem não resolveu
match_fallback as (
    select
        d.*,
        e.codigo_ibge  as codigo_ibge_exc,
        e.nome_ibge_correto as nome_municipio_exc
    from match_direto d
    left join exceptions e
        on d.codigo_ibge is null
        and d.nome_municipio_normalizado = e.nome_anp_normalizado
        and d.uf_sigla = e.uf_sigla
),

final as (
    select
        * exclude (codigo_ibge, nome_municipio_ibge, codigo_ibge_exc, nome_municipio_exc),
        coalesce(codigo_ibge, codigo_ibge_exc)          as codigo_ibge,
        coalesce(nome_municipio_ibge, nome_municipio_exc) as nome_municipio_ibge,
        case
            when codigo_ibge is not null then 'direto'
            when codigo_ibge_exc is not null then 'exception_dict'
            else 'nao_resolvido'
        end as metodo_match,
        (coalesce(codigo_ibge, codigo_ibge_exc) is null) as municipio_nao_resolvido
    from match_fallback
)

select * from final
