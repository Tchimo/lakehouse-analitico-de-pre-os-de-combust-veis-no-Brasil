-- Teste singular: valida faixa de preço plausível, diferenciando GLP
-- (vendido por botijão de 13kg, preço naturalmente mais alto) dos demais
-- combustíveis (vendidos por litro). O teste genérico accepted_range com
-- faixa fixa 0-20 gerava falsos positivos em massa para GLP.

select *
from {{ ref('stg_anp_precos_semanal') }}
where
    (produto = 'GLP' and (preco_medio_revenda < 40 or preco_medio_revenda > 200))
    or
    (produto != 'GLP' and (preco_medio_revenda < 0 or preco_medio_revenda > 20))