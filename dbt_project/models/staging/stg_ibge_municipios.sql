-- Silver: tabela de referência de municípios, normalizada.
-- Gera a chave `nome_municipio_normalizado` usada no join com a ANP.

with source as (
    select * from {{ source('bronze', 'ibge_municipios') }}
),

renamed as (
    select
        cast(codigo_ibge as bigint)        as codigo_ibge,
        nome_municipio,
        {{ normalize_text('nome_municipio') }} as nome_municipio_normalizado,
        uf_sigla,
        uf_nome,
        regiao
    from source
)

select * from renamed
