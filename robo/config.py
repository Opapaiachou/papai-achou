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
    "whey protein": "Fitness",
    "creatina": "Fitness",
    "pre treino": "Fitness",
    "pasta de amendoim": "Fitness",
    "barra de proteina": "Fitness",
    "luva academia": "Fitness",
    "organizador casa": "Casa e cozinha",
    "utensilios cozinha": "Casa e cozinha",
    "potes hermeticos": "Casa e cozinha",
    "kit limpeza casa": "Casa e cozinha",
    "garrafa termica": "Casa e cozinha",
    "organizador geladeira": "Casa e cozinha",
    "acessorios air fryer": "Casa e cozinha",
    "mop giratorio": "Casa e cozinha",
    "jogo de cama": "Casa e cozinha",
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
    "tenis feminino": "Moda",
    "chinelo": "Moda",
    "moda infantil": "Moda",
    "perfume feminino": "Maquiagem e beleza",
    "perfume masculino": "Maquiagem e beleza",
    "kit maquiagem": "Maquiagem e beleza",
    "paleta de sombras": "Maquiagem e beleza",
    "base maquiagem": "Maquiagem e beleza",
    "pincel maquiagem": "Maquiagem e beleza",
    "skincare": "Maquiagem e beleza",
    "fone bluetooth": "Tecnologia útil",
    "carregador turbo": "Tecnologia útil",
    "luminaria led": "Tecnologia útil",
    "smartwatch": "Tecnologia útil",
    "capinha celular": "Tecnologia útil",
    "caixa de som bluetooth": "Tecnologia útil",
    "kit presente": "Presentes",
    # Reforço Black Friday (19/11)
    "air fryer": "Casa e cozinha",
    "jogo de panelas": "Casa e cozinha",
    "panela eletrica": "Casa e cozinha",
    "jogo de toalhas": "Casa e cozinha",
    "camiseta dry fit": "Fitness",
    "tenis infantil": "Crianças",
    "jogo de tabuleiro": "Crianças",
    "mochila notebook": "Tecnologia útil",
    "kit perfume": "Presentes",
    "kit cuidados masculino": "Presentes",
}

# Vitrine (site): quantas ofertas manter publicadas, quantas entram por rodada e por quantos dias.
VITRINE_MAXIMO = 300
VITRINE_POR_RODADA = 80
VITRINE_DIAS = 14

# Quantos produtos buscar por palavra (máximo da API: 50).
PRODUTOS_POR_PALAVRA = 50

# Filtros do checklist do playbook.
NOTA_MINIMA = 4.5            # estrelas
VENDAS_MINIMAS = 200         # unidades vendidas (foco no que já vende)
DESCONTO_MINIMO = 10         # % de desconto informado pela Shopee
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

# ---------- Magalu (Influenciador Magalu) ----------
# Nome da loja no endereço magazinevoce.com.br/<loja>. O link de afiliado é o produto dentro dessa loja.
MAGALU_LOJA = "magazineopapaiachou"
# Pausa (segundos) entre uma busca e outra, para não sobrecarregar o site.
MAGALU_PAUSA = 1.5
# O Magalu não informa unidades vendidas: no lugar das vendas, exige um mínimo de avaliações.
AVALIACOES_MINIMAS = 20

# Lojas buscadas nas rodadas automáticas. A Shopee entra sozinha quando as chaves da Open API existirem.
LOJAS_AUTOMATICAS = ["Magalu", "Awin", "Shopee"]
