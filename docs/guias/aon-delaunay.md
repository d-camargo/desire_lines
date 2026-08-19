# AoN (Delaunay)

A aba **AoN (Delaunay)** faz uma alocação **Tudo-ou-Nada** ("All-or-Nothing")
da matriz OD sobre uma **rede sintética** construída a partir dos próprios
centroides das zonas. É o passo intermediário entre a leitura por par
([Linhas de desejo](linhas-de-desejo.md)) e o carregamento da malha viária de
verdade ([Alocação em rodovias](alocacao-rodovias.md)).

!!! danger "A rede de Delaunay **não** é a malha viária real"
    A rede é a **triangulação de Delaunay** dos centroides: cada zona fica
    ligada às suas vizinhas geográficas por segmentos retos. Isso é uma
    **abstração topológica de vizinhança**, não uma representação de rodovias
    — não existem estradas, sentidos, capacidade nem velocidade ali. Os
    volumes por aresta dizem *por onde a demanda atravessa o território*, não
    quantos veículos passam numa rodovia. Para volume em rodovia, use a aba
    [Alocação em rodovias](alocacao-rodovias.md).

## O que "Tudo-ou-Nada" significa aqui

Para cada par OD, **todo** o fluxo segue o **único caminho de menor custo**
entre origem e destino, e é somado a cada aresta desse caminho. O custo é o
**comprimento** do segmento — não há tempo, velocidade nem congestionamento.
Como não há realimentação de capacidade no custo, também não há rotas
alternativas nem equilíbrio: uma aresta muito carregada não empurra viagens
para outro caminho. A rede é **bidirecional** — A→B e B→A existem ambas.

## Entradas

| Campo | O que escolher |
|---|---|
| *Matriz* ("Matrix") | A camada da matriz OD — o combo só lista camadas **sem geometria** |
| *Centroides* ("Centroids") | A camada de centroides — o combo só lista camadas de **ponto** |
| *Origem* ("Origin") | Coluna de id da zona de origem na matriz (campo **inteiro**) |
| *Destino* ("Destination") | Coluna de id da zona de destino na matriz (campo **inteiro**) |
| *Valor (fluxo)* ("Value (flow)") | Coluna **numérica** de fluxo a ser alocada |
| *ID de Tráfego* ("Traffic ID") | Campo dos **centroides** com o mesmo id usado em Origem/Destino (campo **inteiro**) |

O botão *Alocar (AoN)* ("Allocate (AoN)") só habilita com as duas camadas e os
quatro campos preenchidos. São necessários **pelo menos 3 centroides válidos**
— com menos que isso não há triângulo para triangular, e o plugin avisa e
aborta.

!!! warning "Os ids precisam usar o mesmo esquema"
    Linhas da matriz cujo id de origem ou destino não existe entre os
    centroides são descartadas e contadas no aviso final. Se nenhum par casar,
    a alocação nem roda — ver [Solução de problemas](../solucao-de-problemas.md).

## Dividir por sentido (flow_ab / flow_ba)

A caixa *Dividir por sentido (flow_ab / flow_ba)* ("Split by direction")
controla os campos da camada de saída:

| Campo | Quando aparece | Significado |
|---|---|---|
| `flow` | sempre | Total no segmento = `flow_ab + flow_ba`. É o campo usado pelo estilo. |
| `flow_ab` | só com a caixa marcada | Volume no sentido **desenhado** do segmento, do primeiro para o último vértice |
| `flow_ba` | só com a caixa marcada | Volume no sentido inverso |

!!! note "AB/BA são os sentidos do segmento, não origem/destino"
    `ab`/`ba` se referem à **orientação da geometria** desenhada, ancorada nos
    vértices da linha — não à origem e ao destino da matriz. A convenção
    AB/BA é a usada para direção de link em software de transportes
    (TransCAD, Cube, Emme) justamente para não ser lida como O/D. Deixe a
    caixa desmarcada quando só interessa o carregamento total do segmento.

## A escolha automática do CRS métrico

Menor caminho por comprimento exige unidades **métricas**: distâncias medidas
em graus distorcem o resultado, porque um grau de longitude não vale o mesmo
que um grau de latitude. O plugin resolve isso sozinho, reprojetando os
centroides antes de triangular:

| Situação dos centroides | CRS usado na alocação |
|---|---|
| CRS já é **projetado/métrico** | usado **como está** |
| **Geográfico** e a área cabe numa **única zona UTM** (mesmo hemisfério) | **UTM WGS84** da zona, escolhido automaticamente |
| **Geográfico** e a área abrange **mais de uma zona UTM** ou cruza o equador | **SIRGAS 2000 / Brazil Albers (EPSG:10857)** — equivalente, em metros, padrão IBGE |
| Nada aplicável | o plugin **aborta** e pede que você reprojete os centroides para um sistema métrico |

A mensagem de sucesso ao final informa qual CRS foi escolhido, quantos pares
foram alocados, sobre quantas arestas, e as perdas: pares **inalcançáveis**
(grafo desconexo), linhas da matriz com id desconhecido e pares
**descartados** (origem igual ao destino, ou origem ausente da rede). Vale ler
esse aviso — ele é o único lugar onde as perdas aparecem.

## O resultado

A camada sai como a tabela **`aon_flows`** no mesmo GeoPackage de saída da aba
da matriz, adicionada ao projeto e estilizada por `flow` (mesmo renderizador
graduado por espessura das linhas de desejo, e igualmente editável em
*Propriedades da camada → Simbologia*). A geometria está no CRS métrico
escolhido, que pode não ser o das camadas de entrada.

## Quando este resultado serve

Serve bem para:

- ver **por onde a demanda atravessa o território** e quais ligações entre
  zonas vizinhas concentram fluxo, quando não há malha viária disponível;
- comparar cenários de matriz (antes/depois) sobre uma rede fixa e barata de
  construir;
- checagem rápida de coerência da matriz e dos centroides antes do trabalho
  mais pesado da aba de rodovias.

Não serve para:

- estimar **volume em rodovia**, v/c, nível de serviço ou qualquer coisa que
  dependa de capacidade — a rede é sintética e não tem capacidade;
- estudar rotas ou desvios: não há caminhos alternativos no Tudo-ou-Nada, e as
  arestas não são estradas.

**Próximo passo:** [Alocação em rodovias](alocacao-rodovias.md).
