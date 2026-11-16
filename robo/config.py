"""Configurações do robô Papai Achou.

Tudo o que você pode ajustar sem mexer no resto do código fica aqui.
"""

# Palavras pesquisadas na Shopee a cada rodada (o nicho do canal) e a categoria da vitrine.
# Categorias da vitrine: Fitness, Casa e cozinha, Escola, Crianças, Moda, Maquiagem e beleza, Tecnologia útil, Presentes.
PALAVRAS_CHAVE = {
    "legging fitness": "Fitness",
    "conjunto fitness": "Fitness",
    "top fitness": "Fitness",
    "short fitness masculino": "Fitness",
    "tenis corrida": "Fitness",
    "garrafa academia": "Fitness",
    "coqueteleira": "Fitness",
    "elastico treino": "Fitness",
    "halteres": "Fitness",
    "tapete yoga": "Fitness",
    "corda de pular": "Fitness",
    "organizador casa": "Casa e cozinha",
    "utensilios cozinha": "Casa e cozinha",
    "potes hermeticos": "Casa e cozinha",
    "kit limpeza casa": "Casa e cozinha",
    "garrafa termica": "Casa e cozinha",
    "material escolar": "Escola",
    "mochila infantil": "Escola",
    "lancheira": "Escola",
    "brinquedo educativo": "Crianças",
    "brinquedo infantil": "Crianças",
    "vestido feminino": "Moda",
    "conjunto feminino": "Moda",
    "bolsa feminina": "Moda",
    "tenis masculino": "Moda",
    "camiseta masculina": "Moda",
    "relogio masculino": "Moda",
    "kit maquiagem": "Maquiagem e beleza",
    "paleta de sombras": "Maquiagem e beleza",
    "base maquiagem": "Maquiagem e beleza",
    "pincel maquiagem": "Maquiagem e beleza",
    "skincare": "Maquiagem e beleza",
    "fone bluetooth": "Tecnologia útil",
    "carregador turbo": "Tecnologia útil",
    "luminaria led": "Tecnologia útil",
    "kit presente": "Presentes",
}

# Vitrine (site): quantas ofertas manter publicadas e por quantos dias.
VITRINE_MAXIMO = 80
VITRINE_DIAS = 14

# Quantos produtos buscar por palavra (máximo da API: 50).
PRODUTOS_POR_PALAVRA = 30

# Filtros do checklist do playbook.
NOTA_MINIMA = 4.5            # estrelas
VENDAS_MINIMAS = 100         # unidades vendidas
DESCONTO_MINIMO = 20         # % de desconto informado pela Shopee
COMISSAO_MINIMA = 0.05       # 5% de comissão
PRECO_MINIMO = 10.0          # R$
PRECO_MAXIMO = 600.0         # R$

# Quantas ofertas mandar para você aprovar a cada rodada.
OFERTAS_POR_RODADA = 5

# Não repetir o mesmo produto antes de X dias.
DIAS_SEM_REPETIR = 7

# Considera "preço de verdade" se estiver até 5% acima do menor preço já visto.
TOLERANCIA_MENOR_PRECO = 1.05

# Endpoint oficial da API de afiliados da Shopee Brasil.
SHOPEE_ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

# Ordenação da busca: 2 = mais vendidos.
SHOPEE_ORDENACAO = 2
