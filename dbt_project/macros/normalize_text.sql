{#
  Normaliza texto para permitir join confiável entre nomes de município
  vindos da ANP (inconsistentes) e a tabela oficial do IBGE:
  remove acentos (via strip_accents nativo do DuckDB), baixa para
  minúsculas, remove espaços nas pontas e colapsa espaços duplos.
#}
{% macro normalize_text(column_name) %}
    trim(
        regexp_replace(
            lower(
                strip_accents({{ column_name }})
            ),
            '\s+', ' ', 'g'
        )
    )
{% endmacro %}