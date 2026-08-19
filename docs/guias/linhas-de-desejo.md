# Linhas de desejo

A aba **Linhas de Desejo** ("Desire Lines") gera **uma reta por par OD**,
ligando o centroide da zona de origem ao centroide da zona de destino, com a
**espessura proporcional ao valor** do fluxo. É a leitura visual mais direta da
matriz: para onde a demanda quer ir, sem passar por rede nenhuma.

!!! note "Antes de começar"
    Esta aba consome as duas camadas produzidas na aba anterior — a matriz
    (tabela `output`) e os `centroids`. Veja [Matriz OD](matriz-od.md).

## Entradas

| Campo | O que escolher |
|---|---|
| *Matriz* ("Matrix") | A camada da matriz OD — o combo só lista camadas **sem geometria** |
| *Centroides* ("Centroids") | A camada de centroides — o combo só lista camadas de **ponto** |
| *Origem* ("Origin") | Coluna de id da zona de origem na matriz (campo **inteiro**) |
| *Destino* ("Destination") | Coluna de id da zona de destino na matriz (campo **inteiro**) |
| *Valor para Linhas de Desejo* ("Value to Desire Lines") | Coluna **numérica** de fluxo (viagens, passageiros, toneladas…) — é ela que vira a espessura |
| *ID de Tráfego* ("Traffic ID") | Campo da camada de **centroides** com o mesmo id usado em Origem/Destino (campo **inteiro**) |

O botão *Gerar Linhas de Desejo* ("Desire Lines") só habilita quando as duas
camadas e os quatro campos estão preenchidos — se ele continua cinza, falta
preencher algum combo.

!!! warning "Os ids precisam usar o mesmo esquema"
    *Origem*, *Destino* e *ID de Tráfego* são casados por igualdade. Se a
    matriz numera zonas de um jeito e os centroides de outro, o resultado sai
    vazio. Ver [Solução de problemas](../solucao-de-problemas.md).

## O que o botão gera

O plugin monta as retas por consulta SQL espacial sobre as duas camadas:
para cada linha da matriz, procura o centroide cujo *ID de Tráfego* é igual à
*Origem*, o centroide cujo id é igual ao *Destino*, e desenha o segmento entre
os dois. Pares em que origem e destino são a mesma zona (viagens
intrazonais) são **descartados** — não existe reta de uma zona para ela mesma.

O resultado é gravado como a tabela **`Desire_Lines`** no mesmo GeoPackage de
saída definido na aba da matriz, adicionado ao projeto e estilizado
automaticamente. A camada carrega três atributos — os campos de **origem**,
**destino** e **valor** com os nomes que eles têm na matriz — mais a
geometria de linha, no CRS dos centroides.

## Como ler o resultado

- **Cada feição é um par OD**, não um caminho: a reta é o vetor
  origem→destino, ignora a malha viária e não representa rota nem distância
  percorrida.
- A matriz é normalmente **assimétrica**: se ela traz A→B e B→A como linhas
  separadas, saem **duas retas sobrepostas** com valores diferentes. Para ver
  fluxo total por par, some as duas direções na matriz antes de gerar.
- Onde há muitas zonas, o mapa vira um novelo. Filtrar a camada por um valor
  mínimo (`"<campo de valor>" > x`) ou por uma origem de interesse costuma ser
  mais informativo que exibir a matriz inteira.
- Para uma estimativa de **carregamento em rede**, e não de demanda por par,
  siga para [AoN (Delaunay)](aon-delaunay.md) ou para
  [Alocação em rodovias](alocacao-rodovias.md).

## O estilo aplicado — e como reinterpretá-lo

A camada nasce com um **renderizador graduado por classes** sobre o campo de
valor, variando a **espessura do traço** (mais grosso = maior fluxo):

- **5 classes**, método **Quebras Naturais (Jenks)** — agrupa valores parecidos
  e corta nas lacunas naturais da distribuição, um bom padrão para mapas de
  fluxo;
- espessura de **0,2 mm a 3,0 mm**, cor única azul semitransparente.

Esse estilo é um ponto de partida editável, não uma amarra: abra
*Propriedades da camada → Simbologia* e mude o que precisar — número e limites
das classes, o método de classificação (intervalo igual, quantis, desvio
padrão), as espessuras mínima e máxima, ou a cor. Uma rampa azul
claro→escuro já vem carregada na camada, então trocar o **Método** de
*Tamanho* para *Cor* passa a graduar por cor sem mais configuração.

!!! tip "Por que classes, e não largura definida por dados"
    Versões anteriores calculavam a largura por uma expressão definida por
    dados, que o painel de simbologia **não deixava editar** — a expressão
    sempre vencia o valor digitado à mão. Com o renderizador graduado, tudo o
    que aparece no painel é editável.

**Próximo passo:** [AoN (Delaunay)](aon-delaunay.md).
