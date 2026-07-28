# Desire Lines — Documentação

Plugin QGIS para gerar **linhas de desejo (desire lines)** a partir de uma matriz
Origem/Destino (OD) e camadas de zonas/centroides, com uma aba adicional de
**alocação All-or-Nothing (AoN) sobre uma rede Delaunay**.

- Versão: `0.2.0` (ver `metadata.txt`)
- QGIS mínimo: `3.0`
- Autor: Diego Camargo (@d-camargo)
- Repositório: https://github.com/d-camargo/desire_lines

> Este documento é a referência funcional/técnica do plugin. Para o plano de
> projeto e convenções de desenvolvimento, ver `../CLAUDE.md`. Para a
> especificação original da feature AoN, ver `../AoN_delaunay_desire_lines.md`.

---

## 1. Visão geral

O plugin abre um diálogo com **quatro abas**:

| Aba | objectName | O que faz |
|-----|-----------|-----------|
| **Origin/Destination Matrix** | `tab` | Importa a matriz OD (CSV) e a camada de zonas; gera centroides; define o GeoPackage de saída. |
| **Desire Lines** | `tab_2` | Gera as linhas de desejo (uma reta por par OD) ligando centroides, com espessura proporcional ao fluxo. |
| **AoN (Delaunay)** | `tab_3` | Aloca a demanda OD sobre uma rede Delaunay dos centroides via All-or-Nothing (menor caminho). |
| **Alocação em rodovias** | `tab_4` | Aloca a demanda OD sobre a malha rodoviária real (SNV/GisBR), com capacidade HCM (pista simples/dupla) e métodos AoN ou MSA/BPR. |

### Arquivo de saída único (Output GeoPackage)

Todas as etapas escrevem **tabelas dentro do mesmo arquivo `.gpkg`** definido em
**Output GeoPackage** (aba 1). É o destino único de tudo que o plugin produz:

| Tabela | Gerada por |
|--------|-----------|
| `output` | Leitura da matriz CSV (botão *Read CSV*) |
| `centroids` | Botão *Add Centroids to Traffic Zones* |
| `Desire_Lines` | Botão *Desire Lines* (aba 2) |
| `aon_flows` | Botão *Allocate (AoN)* (aba 3) |
| `capacidade_hcm` | Botão *Calcular capacidade* (aba 4) |
| `alocacao_aon` / `alocacao_msa` | Botão *Alocar* (aba 4) — o nome segue o método escolhido |

Lógica de caminho (`_output_path`, `desirelines_dialog.py`):

1. Se o usuário escolheu um caminho → usa esse (acrescenta `.gpkg` se faltar).
2. Se ficou vazio → *fallback*: pasta do CSV da matriz → pasta do vetor →
   `~/output.gpkg` (home do usuário).

Após escrever cada tabela, ela é adicionada ao projeto via
`output.gpkg|layername=<tabela>`.

---

## 2. Aba 1 — Origin/Destination Matrix

### 2.1 Matriz OD (CSV)

- Widget `matrixInsert` (filtro `CSV(*csv)`), botão **Read CSV** (`readCSV` → `matrix()`).
- Encoding de leitura: **`windows-1252`**; delimitador **`;`**; sem geometria
  (`geomType=none`).
- Checkbox **"Travel Demand Matrix format"** (`checkBox`): quando marcado, a
  matriz vem em **formato largo (wide)** — uma coluna `OD` + uma coluna por
  destino — e é convertida para **formato longo (long)** com `pandas.melt`:
  - `id_vars='OD'`, gerando colunas `Origem`, `Destino`, `Passageiros`;
  - grava `matrix_long.csv` ao lado do arquivo original e usa esse.
  - **Requer `pandas`** no ambiente Python do QGIS; se ausente, exibe erro.
- A matriz é gravada como tabela **`output`** no GeoPackage.

> Formato "longo" esperado nas etapas seguintes: colunas de **origem**,
> **destino** e **valor/fluxo** (uma linha por par OD).

### 2.2 Zonas de tráfego e centroides

Duas formas de fornecer as zonas (decoplado de nomes fixos):

1. **Importar arquivo** — widget `vectorInsert` (SHP/GPKG), botão **Read Vector**
   (`readV` → `fvector()`). A camada é carregada como `traffic_zones` e
   **selecionada automaticamente** no combo `zonesCombo`.
2. **Atribuir camada existente do projeto** — combo `zonesCombo`
   (`QgsMapLayerComboBox`, filtro polígono, *allow empty*). Permite usar uma
   camada de zonas que já está no projeto, sem importar arquivo.

Botão **Add Centroids to Traffic Zones** (`addCentroids` → `centroids()`),
posicionado **abaixo** do combo de seleção:

- Usa a camada do `zonesCombo`; se vazio, cai no *fallback* `traffic_zones`.
- Roda `native:centroids` com `ALL_PARTS=True`.
- Grava a tabela **`centroids`** no GeoPackage e adiciona ao projeto.

---

## 3. Aba 2 — Desire Lines

Gera **uma reta por par OD** ligando o centroide de origem ao de destino, com
largura proporcional ao valor.

### 3.1 Entradas (combos)

| Widget | Papel | Filtro |
|--------|-------|--------|
| `mMapLayerComboBox` | Camada da **matriz** (tabela `output`) | NoGeometry |
| `mMapLayerComboBox_2` | Camada de **centroides** (pontos) | PointLayer |
| `mFieldComboBox` | Campo **Origin** | Int |
| `mFieldComboBox_2` | Campo **Destination** | Int |
| `mFieldComboBox_3` | Campo **Value to Desire Lines** | Double |
| `mFieldComboBox_4` | Campo **Traffic ID** (id da zona nos centroides) | Int |

O botão **Desire Lines** (`makeDL`) só habilita quando matriz, centroides e os
quatro campos estão preenchidos (`_update_make_dl_state`).

### 3.2 Como funciona (`desirelines()`)

Monta as linhas via **virtual layer** com `qgis:executesql` (SpatiaLite):

```sql
SELECT "<origin>", "<dest>", "<value>",
       SetSRID(make_line(a.geometry, b.geometry), <srid>) AS geometry
FROM "<matrix>"
JOIN "<centroids>" a ON "<matrix>"."<origin>" = a."<traffic_id>"
JOIN "<centroids>" b ON "<matrix>"."<dest>"   = b."<traffic_id>"
WHERE a."<traffic_id>" != b."<traffic_id>"
```

Detalhes importantes:

- **Sanitização de identificadores**: nomes de camada/campo vêm dos combos, mas
  são validados por `_SAFE_IDENT_RE = ^\w[\w .\-]{0,127}$` (Unicode-aware: aceita
  acentos; rejeita aspas, ponto e vírgula, parênteses) e **aspados** com `q()`
  (duplica `"`). Defesa contra injeção de SQL.
- **`SetSRID(make_line(...), srid)`**: o `make_line()` do SpatiaLite **perde o
  SRID** em virtual layers; o `SetSRID()` reinjeta o CRS dos centroides
  (`postgisSrid()`) para a geometria sair com CRS válido no GPKG.
- `WHERE a != b` descarta auto-pares (origem = destino).
- `INPUT_GEOMETRY_TYPE: 3` = LineString.
- Saída na tabela **`Desire_Lines`**, adicionada ao projeto e **estilizada**.

### 3.3 Estilo (`_apply_desire_lines_style`)

**Renderer graduado por classes** (`QgsGraduatedSymbolRenderer`) sobre o campo de
valor, variando a **espessura do traço** (mais grosso = maior fluxo):

- **5 classes**, método **Natural Breaks (Jenks)** — agrupa valores parecidos e
  quebra nas lacunas naturais; bom padrão para mapas de fluxo.
- `setGraduatedMethod(GraduatedSize)` + `setSymbolSizes(0.2, 3.0)`: a espessura
  varia por classe; cor única (azul `0,90,180,160`). Uma rampa azul claro→escuro
  é passada ao `createRenderer` apenas porque é exigida — fica disponível caso o
  usuário troque depois para graduação **por cor** no painel.

> **Por que classes (e não *data-defined width*)?** A versão anterior usava uma
> sobreposição definida por dados (`scale_linear`) na largura, que o painel de
> simbologia **não deixava editar** (o override "vencia" o valor manual). Com o
> renderer graduado, o usuário edita classes, faixas, larguras e cores
> diretamente no painel.

A mesma função estiliza o `aon_flows` pelo campo `flow`.

---

## 4. Aba 3 — AoN (Delaunay) ⭐

Esta é a funcionalidade nova e mais técnica. Faz **alocação All-or-Nothing** da
demanda OD sobre uma **rede simplificada de Delaunay** construída sobre os
centroides das zonas.

### 4.1 Conceito

- **Rede Delaunay**: triangulação dos centroides → arestas únicas. É uma
  **abstração topológica de vizinhança** entre zonas, **não** uma malha viária
  real. Cada zona fica conectada às suas vizinhas geográficas.
- **All-or-Nothing (AoN)**: para cada par OD, **todo o fluxo** `f_od` segue o
  **único caminho de menor custo** entre origem e destino. Para cada aresta `a`
  nesse caminho: `x_a += f_od`. Não há equilíbrio, congestionamento, nem rotas
  alternativas (PSL/UE estão fora de escopo — exigiriam k-shortest-paths e
  laços BPR+MSA).
- **Custo da aresta**: **distância/comprimento** (`QgsNetworkDistanceStrategy`).
  Não há opção de tempo/velocidade.
- **Bidirecional**: o grafo é `DirectionBoth` — A→B e B→A existem ambos.

### 4.2 Entradas (combos)

| Widget | Papel | Filtro |
|--------|-------|--------|
| `aonMatrixCombo` | Camada da **matriz** OD | NoGeometry |
| `aonCentroidsCombo` | Camada de **centroides** (pontos) | PointLayer |
| `aonOriginField` | Campo **Origin** | Int |
| `aonDestField` | Campo **Destination** | Int |
| `aonValueField` | Campo **Value (flow)** | Double |
| `aonZoneIdField` | Campo **Traffic ID** dos centroides | Int |
| `aonDirectional` | Checkbox **"Split by direction (flow_ab / flow_ba)"** | — |

Botão **Allocate (AoN)** (`runAoN` → `run_aon()`); só habilita com todas as
entradas preenchidas (`_update_aon_state`).

### 4.3 Fluxo de execução (`run_aon`, `desirelines_dialog.py`)

1. **Ler centroides**: para cada feição, `zone_key(traffic_id) -> índice`, e
   coleta os `QgsPointXY` no CRS da camada; calcula o *extent*. Exige **≥ 3
   centroides válidos** (mínimo para triangular).
   - `_zone_key()` normaliza o id (int → `int(float(...))` → string), para a
     matriz e os centroides casarem mesmo com tipos diferentes (`12` vs `12.0`).
2. **Escolher CRS métrico** via `aon.pick_metric_crs` (ver §4.4). Se `None`,
   avisa o usuário e aborta.
3. **Reprojetar** os centroides para o CRS métrico (`QgsCoordinateTransform`),
   se diferente do de origem.
4. **Ler a demanda OD** da matriz: mapeia origem/destino para índices de
   centroide; converte o valor para `float`. Linhas com id desconhecido ou
   valor inválido entram em `missing`.
5. **Construir a rede e alocar** (`aon.py`):
   `points_to_layer` → `build_delaunay_edges` → `allocate_aon` →
   `edge_flows_to_layer(directional=...)`.
6. **Gravar** `aon_flows` no GeoPackage (`_write_layer_to_gpkg`) e estilizar por
   `flow`.
7. **Relatar** no message bar: CRS escolhido, pares alocados, e perdas
   (`unreachable`, ids desconhecidos, `skipped`).

### 4.4 Seleção de CRS métrico (`aon.pick_metric_crs`)

Dijkstra/comprimento exigem unidades **métricas** — distâncias em graus
distorceriam o menor caminho. Regra (decidida com o usuário):

| Situação | CRS escolhido |
|----------|---------------|
| `src_crs` já é **projetado/métrico** | usa **como está** (passthrough) |
| **Geográfico**, cabe em **uma** zona UTM (e mesmo hemisfério) | **WGS84 UTM** automático: `EPSG 326xx` (N) / `327xx` (S) |
| **Geográfico**, abrange **>1 zona UTM** ou cruza o equador | **SIRGAS 2000 / Brazil Albers — `EPSG:10857`** (equivalente, em metros, padrão IBGE) |
| Nada válido | retorna `(None, nota)` → pede ao usuário reprojetar para UTM |

- Zona UTM: `zone = int((lon + 180)/6) + 1`, limitada a 1..60 (`_utm_zone`).
- **Fallback do Albers**: se o PROJ local não conhecer `EPSG:10857`, constrói a
  partir de um **proj4** (`+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22
  +x_0=5000000 +y_0=10000000 +ellps=GRS80 ... +units=m`), via `createFromProj`
  (QGIS ≥ 3.10) ou `createFromProj4` (≥ 3.0).

### 4.5 Construção da rede Delaunay (`build_delaunay_edges`)

Encadeia algoritmos nativos de Processing sobre a camada de pontos métrica:

```text
native:delaunaytriangulation   → polígonos (triângulos)
  → native:polygonstolines     → contornos como linhas
  → native:explodelines        → um segmento por aresta
  → native:deleteduplicategeometries → remove arestas internas duplicadas
```

Arestas internas são compartilhadas por dois triângulos (aparecem 2×); a
deduplicação (igualdade GEOS, **independente de direção**) colapsa A→B e B→A em
uma só. `_memory_layer()` cria a camada e aplica `setCrs()` explicitamente
(robusto a CRS sem authid, como o Albers via proj4).

### 4.6 Alocação (`allocate_aon`)

```text
director = QgsVectorLayerDirector(edges, ..., DirectionBoth)
director.addStrategy(QgsNetworkDistanceStrategy())   # custo = comprimento
builder  = QgsGraphBuilder(metric_crs)
tied     = director.makeGraph(builder, centroid_points)
graph    = builder.graph()
```

- **Uma execução de Dijkstra por origem distinta** (não por par): os pares OD
  são agrupados por origem (`by_origin`), e `QgsGraphAnalyzer.dijkstra` roda uma
  vez por origem, retornando a **árvore de menor caminho**.
- Para cada destino, **caminha a árvore do destino de volta à origem**, somando
  o fluxo a cada aresta percorrida (o "tudo ou nada").
- **Acúmulo por par não-ordenado** `{lo, hi}` (menor/maior id de vértice) para
  nunca contar em dobro as duas arestas direcionadas do par. Cada par guarda
  **as duas direções**: `[ab, ba]`, onde `ab` é o fluxo no sentido `lo→hi` (a
  orientação desenhada da geometria, p1→p2) e `ba` o inverso.

```python
v = end; f = float(flow)
while v != start:
    edge = graph.edge(tree[v])
    a, b = edge.fromVertex(), edge.toVertex()   # viagem real a -> b
    if a <= b: key, forward = (a, b), True       # lo -> hi
    else:      key, forward = (b, a), False       # hi -> lo
    pair = flow_by_pair.setdefault(key, [0.0, 0.0])
    pair[0 if forward else 1] += f
    v = a
```

**Estatísticas** (`stats`):
- `allocated` — pares alocados com sucesso;
- `unreachable` — destino sem caminho (grafo desconexo);
- `skipped` — auto-par (o == d) ou origem inexistente no grafo.

### 4.7 Saída (`edge_flows_to_layer`) e campos

Camada de linhas em memória, depois gravada como `aon_flows`:

| Campo | Sempre? | Significado |
|-------|---------|-------------|
| `flow` | **sim** | Total por segmento = `flow_ab + flow_ba`. Usado pelo estilo. |
| `flow_ab` | só se `directional` | Volume na orientação desenhada do segmento **A→B** (p1→p2). |
| `flow_ba` | só se `directional` | Volume no sentido inverso **B→A** (p2→p1). |

> **Por que AB/BA e não OD/DO?** `flow_ab`/`flow_ba` são as direções do
> **segmento desenhado** (ancoradas aos vértices p1/p2 da linha), **não** a
> origem/destino da matriz. A nomenclatura AB/BA é a convenção de direção de
> link (TransCAD/Cube/Emme) e evita a leitura errada como O/D. `flow` (total) é
> sempre escrito para o estilo funcionar nos dois modos.

---

## 5. Aba 4 — Alocação em rodovias (Highway Assignment) ⭐

Esta aba realiza a alocação da demanda de tráfego sobre a **malha rodoviária real** (obtida via plugin **GISBR**), calculando a capacidade operacional de cada segmento rodoviário conforme os procedimentos do **HCM (Highway Capacity Manual)** e alocando os fluxos da matriz OD via **All-or-Nothing (AoN)** ou **MSA (Method of Successive Averages com curva BPR)**.

### 5.1 Requisito e dependência do GISBR (D6)

- A funcionalidade exige que o plugin **GISBR** esteja instalado no QGIS (`plugin_dependencies=GisBR`).
- O GISBR fornece o acesso à malha do Sistema Nacional de Viação (SNV / INDE).
- Se o GISBR não estiver presente no ambiente, a aba **Alocação em rodovias** é automaticamente desabilitada e exibe um aviso orientando a instalação do GISBR.

### 5.2 Fluxo passo a passo de uso

1. **Obter a Malha Rodoviária**:
   - Escolha uma camada de vias já carregada no QGIS ou utilize o botão de integração com o GISBR para baixar a malha rodoviária da área de estudo (por estado/UF ou caixa delimitadora *Bounding Box*).
2. **Selecionar a Matriz OD e Centroides**:
   - Selecione a camada da **Matriz OD** (em formato longo, gravada na tabela `output`) e os campos de **Origem**, **Destino** e **Fluxo**.
   - Selecione a camada de **Centroides** e o campo **Traffic ID** (identificador das zonas).
3. **Configurar os Parâmetros HCM e Sobrescritas (D7)**:
   - **Terreno**: escolha o tipo de relevo dominante (*Plano*, *Ondulado* [padrão] ou *Montanhoso*).
   - **% Veículos Pesados**: proporção de caminhões/ônibus no tráfego (padrão 20%).
   - **Sobrescritas por campo**: caso a camada de rodovias possua campos específicos para número de faixas, tipo de rodovia, largura de faixa ou velocidade de fluxo livre (FFS), você pode mapeá-los nos comboboxes. Se o campo não for mapeado, o plugin aplica automaticamente os valores padrão documentados (ex.: FFS de 80 km/h para pista simples e 110 km/h para pista dupla; PHF 0,92).
   - A proveniência de cada valor é registrada nos campos `src_*` da camada resultante.
4. **Passo 1 — Calcular Capacidade (D9)**:
   - Clique no botão **Calcular capacidade**.
   - O plugin processa as características geométricas/operacionais da malha e calcula a capacidade por sentido (veq/h) segundo as regras do HCM para pistas simples (cap. 15) e pistas duplas/multilane/freeway (cap. 12).
   - O resultado é salvo na tabela `capacidade_hcm` no GeoPackage de saída e carregado no mapa. Você pode inspecionar e editar as capacidades diretamente na tabela de atributos antes de prosseguir.
5. **Passo 2 — Alocar (D10)**:
   - Escolha o método de alocação: **AoN (All-or-Nothing)** ou **MSA (Method of Successive Averages)**.
   - Configure o número máximo de iterações (para MSA, padrão 10) e a tolerância de erro/gap.
   - Clique em **Alocar**. O plugin conecta os centroides à malha (raio máximo de conectores), calcula os caminhos mínimos e acumula os fluxos nos arcos.

---

### 5.3 Parâmetros HCM e Regra de Proveniência (D7)

Para garantir auditabilidade total, a leitura de parâmetros segue a regra:
1. **Campo oficial da camada**: lido se o usuário mapear um campo correspondente.
2. **Padrão assumido**: aplicado caso o campo não seja fornecido.
3. **Sobrescrita do usuário**: valor global definido na interface da aba.

| Parâmetro | Padrão se ausente | Fonte / Justificativa |
|---|---|---|
| Tipo de segmento | 2 faixas (pista simples) | SNV / Padrão rural |
| Nº de faixas por sentido | 1 (simples) / 2 (duplicada) | Derivado do tipo de pista |
| Terreno | Ondulado | Escolha global na aba |
| % Veículos pesados | 20 % | Média rodoviária rural federal |
| Largura de faixa / acostamento | 3,50 m / 2,50 m | Normas de projeto DNIT |
| Velocidade de fluxo livre (FFS) | 80 km/h (simples) / 110 km/h (duplicada) | Limites de velocidade rodoviários rurais |
| PHF (Fator de Hora de Pico) | 0,92 | Padrão HCM para tráfego rural |
| % Ultrapassagem proibida | 50 % | Estimativa para pista simples |
| Parâmetros BPR ($\alpha, \beta$) | 0,15 / 4,0 | Curva BPR padrão |

A origem exata de cada dado é gravada nos campos `src_*` (ex.: `src_capacidade`, `src_ffs`) na camada de saída, com os valores `'oficial'`, `'padrao'` ou `'usuario'`.

---

### 5.4 Critério de Escolha: AoN vs. MSA (D10)

O plugin expõe dois métodos de alocação para atender a finalidades distintas:

| Método | O que faz | Custo Computacional | Quando Usar |
|---|---|---|---|
| **AoN (All-or-Nothing)** | Aloca 100% do fluxo de cada par OD pelo menor caminho em tempo de fluxo livre ($t_0$). Não realimenta o tempo por congestionamento. | **Baixo** (~10× mais rápido) | • Diagnóstico rápido de demanda potencial em redes grandes.<br>• Malhas rodoviárias com pouca concorrência de rotas.<br>• Cenários onde a demanda está bem abaixo da capacidade.<br>• Como **linha de base (baseline)** para comparar contra o MSA. |
| **MSA (Equilíbrio MSA + BPR)** | Iterativo (padrão 10 iterações). Atualiza os tempos de viagem a cada iteração via fórmula BPR ($t = t_0 [1 + \alpha (v/c)^\beta]$), distribuindo o tráfego entre rotas concorrentes conforme a saturação. | **Moderado** (proporcional ao nº de iterações) | • Malhas rodoviárias com rotas alternativas concorrentes.<br>• Trechos onde a demanda atinge ou supera a capacidade.<br>• Simulação do efeito de gargalos e desvio de tráfego. |

> **Interpretação da razão $v/c$ em AoN**: Na alocação AoN, se o campo $v/c$ resultar maior que 1.0 ($v/c > 1$), isso representa um **diagnóstico direto de sobrecarga/déficit de capacidade** no trecho, e não um estado de equilíbrio real.

---

### 5.5 Diferença entre AoN (Delaunay) e AoN (Rodovias)

- **AoN (Delaunay) — Aba 3**: Carrega a demanda sobre uma rede **sintética de abstração topológica** (triangulação de Delaunay conectando centroides). Não utiliza estradas reais, não possui capacidade nem limites físicos.
- **AoN (Rodovias) — Aba 4**: Carrega a demanda sobre a **malha rodoviária real** (geometria do SNV/DER), calculando a capacidade HCM dos trechos e permitindo auditar o uso da infraestrutura viária física.

---

### 5.6 Escopo Rodoviário e Aviso de Área Urbana (D11)

O módulo de tráfego foi desenhado exclusivamente para **rodovias rurais e interurbanas**:

1. **Sem interseções semaforizadas (D2)**: O cálculo do HCM abrange segmentos de pista simples e pista dupla/freeway. Interseções semaforizadas, rotatórias e rampas urbanas estão fora de escopo por falta de dados na base oficial.
2. **Ressalva de Área Urbana / Travessias Urbanas (D11)**: Em trechos urbanos, a capacidade real é governada por semáforos, ciclos e cruzamentos, e não pela geometria do segmento. Aplicar a fórmula rodoviária nesses trechos **superestima a capacidade**.
   - O plugin **não remove** as travessias urbanas da malha, mas identifica e marca estes arcos com `escopo = 'urbano'` (contra `'rodoviario'`).
   - Um aviso é exibido no log e na barra de mensagens informando a quantidade de trechos urbanos processados com a fórmula aproximada, cabendo ao analista filtrar ou ajustar a análise.
3. **LOS aproximado por $v/c$ (D3)**: O Nível de Serviço (LOS) é classificado por faixas da razão $v/c$ ($A \le 0,35$; $B \le 0,55$; $C \le 0,75$; $D \le 0,90$; $E \le 1,00$; $F > 1,00$), funcionando como um indicador visual rápido de gargalos.

---

### 5.7 Leitura dos Resultados e Envelope de Desempenho (D4)

#### Campos da camada de saída (`alocacao_aon` / `alocacao_msa`)
- `volume`: volume total de tráfego alocado no arco (veículos/dia ou veq/h).
- `capacidade`: capacidade calculada por sentido (veq/h).
- `vc`: razão volume/capacidade.
- `los`: Nível de Serviço aproximado (A a F), por faixas de v/c (D3) — não por densidade.
- `metodo`: método de alocação utilizado (`aon` ou `msa`).
- `escopo`: classificação do trecho (`rodoviario` ou `urbano`).
- `src_*`: rastreabilidade da origem dos parâmetros de entrada.

#### Envelope de Desempenho
- O motor de grafo desenvolvido em Python suporta confortavelmente malhas de até **~50.000 arcos** com **10 iterações** de MSA.
- A alocação AoN por realizar uma única passada de Dijkstra é aproximadamente **10× mais rápida**, permitindo processar malhas ainda maiores em tempo reduzido.

---

## 6. Arquitetura do código

```
desire_lines/
├── desirelines.py            # Classe do plugin: initGui(), run(), unload().
│                             #   run() cria o dialog 1× e configura filtros dos combos.
├── desirelines_dialog.py     # Lógica de UI/execução das abas (inclui run_assignment/run_aon).
├── aon.py                    # Núcleo AoN sintético (Delaunay) puro (sem GUI).
├── traffic/                  # Módulo de tráfego em rodovias (HCM, grafo, alocação, GISBR).
│   ├── __init__.py
│   ├── assignment.py         # Motores assign_aon, assign_msa, assign
│   ├── gisbr_bridge.py       # Integração e checagem do plugin GISBR
│   ├── graph.py              # Grafo direcionado em Python puro
│   ├── hcm.py                # Procedimentos de capacidade HCM (caps. 12 e 15)
│   ├── network.py            # Construtor de rede viária e conectores de centroides
│   ├── outputs.py            # Camada de saída (capacidade_hcm / alocacao_*) e estilo v/c
│   └── params.py             # Tratamento de parâmetros e proveniência (D7)
├── desirelines_dialog_base.ui# Interface Qt Designer (4 abas).
└── test/                     # Suíte de testes unitários do plugin.
```

**Princípio de design**: Os módulos em `traffic/` são **livres de GUI** e em Python puro, testáveis sem QGIS. A wiring de UI fica em `desirelines_dialog.py`.

---

## 7. Testes

`test/` cobre o núcleo do plugin:

- `test_aon.py`: testes da triangulação e alocação Delaunay.
- `test_hcm.py`: validação dos procedimentos HCM de capacidade.
- `test_graph.py` / `test_network.py`: construção do grafo viário e conectores.
- `test_assignment.py`: motores AoN e MSA sobre rede rodoviária.
- `test_gisbr_bridge.py`: checagem e mensagens da integração com GISBR.

---

## 8. Notas e limitações

- O plugin **não roda fora do QGIS** (imports PyQGIS exigem o ambiente QGIS).
- O AoN em Delaunay (Aba 3) é uma **abstração topológica** da demanda sobre a vizinhança das zonas, **não** carregamento em rede viária real.
- Sem PSL (Path-Size Logit) nem UE (User Equilibrium) — exigiriam k-shortest-paths e iterações complexas.
- A conversão wide→long da matriz depende de **`pandas`** no Python do QGIS.
- Encoding fixo da matriz: `windows-1252`, delimitador `;`.
- Para recarregar após mudanças no código/UI, use o **Plugin Reloader** no QGIS.

---

## 9. Módulo de alocação de tráfego em rodovias — Decisões de Arquitetura

> **Status:** implementado (`desire_lines/traffic/` e 4ª aba). Esta seção registra as **decisões de arquitetura (D1–D11)** que orientaram a implementação.

Módulo que aloca a demanda OD sobre a **malha rodoviária oficial**
(federal/estadual, obtida via GISBR), com **capacidade calculada por
procedimento HCM** e **dois métodos de alocação**. Difere da aba *AoN
(Delaunay)* (§4), que usa uma rede **sintética** de vizinhança entre centroides.

### 9.1 Decisões de arquitetura

**D1 — HCM-CALC é referência, não dependência.** O
[HCM-CALC](https://github.com/swash17/HCM-CALC) (Dr. Scott Washburn, UF) não é
uma biblioteca: é um aplicativo desktop Windows, sem licença declarada — não é
importável nem redistribuível dentro de um plugin GPL-3.0. Os procedimentos HCM
necessários são implementados em **Python puro dentro do plugin**; os
*ExampleProblems* do HCM-CALC e os exemplos publicados do HCM entram apenas como
**valores de referência escritos à mão nos testes**. Nenhum arquivo daquele
repositório é copiado para cá.

**D2 — Escopo HCM: rodovias, e só o que a malha brasileira exige.** Cobertos:
**pista simples / duas faixas** (HCM 6ª ed., cap. 15) e **segmento básico de
pista dupla / multilane e freeway** (cap. 12). **Fora de escopo:** interseções
semaforizadas, vias urbanas, rampas e *weaving* — a base oficial não fornece as
entradas, e a exclusão é documentada em vez de chutada (ver D11).

**D3 — LOS por v/c, não por densidade.** O LOS do HCM sai de densidade
(pc/mi/ln) ou *follower density*, que exigem mais entrada do que há por arco. O
módulo reporta LOS por faixas de **v/c** — A ≤ 0,35; B ≤ 0,55; C ≤ 0,75;
D ≤ 0,90; E ≤ 1,00; F > 1,00 — **rotulado como aproximação** na saída e aqui.
Serve para ranquear gargalos, sem fingir precisão que a base não sustenta.

**D4 — Grafo próprio em Python, não `QgsGraph`.** `QgsVectorLayerDirector` cria
uma aresta **por segmento geométrico** e não devolve o vínculo aresta→feição;
numa malha real (links com dezenas de vértices) isso impede acumular fluxo **por
link** (a capacidade é do link) e congela o custo no `makeGraph` (obrigaria a
reconstruir o grafo a cada iteração). Em `traffic/graph.py`: grafo próprio com
`heapq` (stdlib), nó = extremidade de arco arredondada à tolerância de snap,
custo por arco atualizado *in-place*, Dijkstra com predecessor-arco. O mesmo
grafo serve às N iterações do MSA e ao AoN de passada única.
*Custo:* Dijkstra em Python é ~10× mais lento que o C++ do QGIS. Mitigações:
recorte obrigatório pela área de estudo, 1 Dijkstra por origem (não por par OD)
e padrão de 10 iterações. **Envelope declarado:** confortável até ~50 mil arcos
(o AoN, por ser 1 iteração, escala ~10× melhor). Se estourar na prática, a
alternativa registrada é explodir a rede em segmentos de 2 pontos, voltar ao
`QgsGraphAnalyzer` e agregar por `link_id`.

**D5 — Arcos direcionados, um por sentido.** Capacidade e congestionamento são
por sentido: cada link vira **dois arcos** (A→B e B→A, geometria revertida), com
capacidade, fluxo e custo próprios. Isso dispensa o esquema `flow_ab`/`flow_ba`
de `aon.py` no módulo novo — **`aon.py` não é alterado**.

**D6 — GISBR: dependência obrigatória atrás de um adaptador fino.** O GISBR
ainda não expõe algoritmo de malha rodoviária (o SNV está no catálogo do
diagnóstico, via WFS do INDE). Todo acesso fica em `traffic/gisbr_bridge.py`,
nesta ordem: (1) `processing.run('gisbr:<alg>')` se houver algoritmo de
rodovias; (2) fallback importando `gisbr.core.sources` /
`gisbr.core.connectors.wfs`; (3) se o GISBR não estiver instalado, **bloquear o
módulo** com mensagem clara e link para
<https://github.com/d-camargo/gisbr>. O `metadata.txt` declara
`plugin_dependencies=GisBR`, mas quem manda é a checagem em runtime. O GISBR
exige QGIS ≥ 3.16; o `qgisMinimumVersion` do Desire Lines segue 3.0 e a aba nova
se desabilita sozinha.

**D7 — Parâmetros ausentes: assumir com padrão documentado, sempre
sobrescrevível, sempre registrado.** Regra única: (a) tenta ler do campo
oficial; (b) se não houver, usa um padrão explícito e justificado; (c) o usuário
sobrescreve globalmente na aba **ou** mapeando um campo da camada; (d) a origem
efetiva vai para a saída (`src_*`) e para o resumo no log. **Nada é assumido em
silêncio.**

| Parâmetro | Fonte oficial (SNV/DER) | Se ausente (padrão) |
|---|---|---|
| Tipo de segmento (2 faixas / multilane / freeway) | derivado de "Simples/Duplicada" | 2 faixas |
| Nº de faixas por sentido | derivado do tipo de trecho | 1 (simples) / 2 (duplicada) |
| Comprimento | geometria (CRS métrico) | — (sempre existe) |
| Pavimentado | campo de superfície | pavimentado |
| **Trecho urbano / travessia urbana** | campo de tipo de trecho, se existir | **não (rural)** — ver D11 |
| Largura de faixa | não existe | 3,50 m (padrão DNIT) |
| Largura de acostamento | não existe | 2,50 m (rural) |
| Terreno (plano/ondulado/montanhoso) | não existe | ondulado (escolha global na aba) |
| % veículos pesados | não existe | 20 % (rural federal) |
| FFS / velocidade de fluxo livre | não confiável | 80 km/h simples, 110 km/h duplicada |
| PHF | não existe | 0,92 (rural) |
| % de zonas de ultrapassagem proibida | não existe | 50 % |
| Densidade de acessos | não existe | padrão HCM para rodovia rural |
| Divisão direcional | não existe | 50/50 |
| α, β do BPR | n/a | 0,15 / 4,0 |

Derivar terreno de MDE (declividade via SRTM) fica **fora** desta rodada; o
padrão global + mapeamento por campo cobre o caso. O `% de veículos pesados` por
dados do PNCT fica como melhoria futura.

**D8 — Onde o código mora.** Subpacote novo `desire_lines/traffic/`
(`__init__.py`, `params.py`, `hcm.py`, `gisbr_bridge.py`, `network.py`,
`graph.py`, `assignment.py`, `outputs.py`), **sem GUI dentro** — mesmo princípio
de `aon.py` (§5). A UI é uma **4ª aba** ("Alocação em rodovias") no
`desirelines_dialog_base.ui`; **não** se cria um Processing provider
(`hasProcessingProvider=no` continua). `hcm.py`, `params.py`, `graph.py` e
`assignment.py` são Python puro, testáveis sem QGIS.

**D9 — Duas ações separadas na aba.** "Calcular capacidade" (só HCM, devolve a
malha com `capacidade`/`src_*`) é útil sozinho e é pré-requisito de "Alocar".
Separar os botões evita reprocessar a capacidade a cada rodada e permite
revisar/editar as capacidades antes de alocar.

**D10 — AoN é método de primeira classe, não só etapa interna do MSA.** Ver
§8.2.

**D11 — Escopo rodoviário: área urbana não é chutada, é sinalizada.** Ver §8.3.

### 9.2 Os dois métodos de alocação (D10)

Ponto de entrada único
`assignment.assign(graph, arcs, od_pairs, method='msa', ...)`, com
`method ∈ {'aon', 'msa'}`, devolvendo **sempre a mesma tripla**
`(fluxos, historico, stats)`:

| Método | O que faz | Realimenta custo? | `historico` / `gap` |
|---|---|---|---|
| **`'aon'`** — All-or-Nothing | Uma passada sobre os custos de **fluxo livre** (`t0`): todo o fluxo de cada par OD vai pelo menor caminho. | **Não** | uma entrada; `stats['gap'] = None` |
| **`'msa'`** — Equilíbrio MSA + BPR | Itera AoN sobre custos atualizados pela relação fluxo/capacidade (BPR), distribuindo o tráfego entre rotas concorrentes. Padrão: 10 iterações. | **Sim** | uma entrada por iteração; `gap` numérico |

Por que o AoN é exposto e não escondido: custo zero de implementação
(`assign_msa` já roda AoN por iteração — AoN é `max_iter=1` sem realimentação);
serve a casos reais (pouca concorrência de rotas, demanda bem abaixo da
capacidade, diagnóstico rápido em rede grande); e é a **linha de base de
comparação** — rodar os dois sobre a mesma rede mostra em números o efeito da
restrição de capacidade.

A capacidade **continua sendo calculada e reportada no AoN** (`capacidade`,
`v/c`, `LOS`); o que muda é que ela não realimenta o custo. O método usado vai
para o campo `metodo` da saída, e o log diz explicitamente que, em AoN,
**`v/c > 1` é diagnóstico de sobrecarga, não resultado de equilíbrio**.

> **Nomenclatura:** a aba *AoN (Delaunay)* (§4) faz "AoN sobre rede **sintética**
> (Delaunay entre centroides)"; esta aba faz "AoN sobre rede **rodoviária
> real**". São coisas diferentes.

### 9.3 Ressalvas explícitas de escopo

Três limites, declarados aqui e repetidos na interface, nos docstrings e no log:

1. **Sem interseções semaforizadas (D2).** O escopo HCM implementado cobre
   segmentos rodoviários (pista simples/duas faixas e pista dupla/freeway).
   Interseções semaforizadas, rampas e *weaving* estão fora — a base oficial não
   fornece as entradas.
2. **Área urbana usa outro método de capacidade (D11).** Em área urbana o HCM
   trata segmento de via urbana (cap. 16–19), onde a capacidade é governada pelo
   controle semafórico (verde/ciclo, fluxo de saturação, espaçamento de
   interseções) — nada disso existe no SNV nem é inferível dele; aplicar o
   procedimento rodoviário num trecho urbano **superestima grosseiramente** a
   capacidade. O módulo é **explicitamente rodoviário**: travessias urbanas
   dentro da malha **não são removidas nem recalculadas por método urbano** —
   recebem a capacidade rodoviária como **aproximação declarada**, são marcadas
   com `escopo = 'urbano'` (contra `'rodoviario'`) e sua contagem aparece no log
   com aviso. O usuário decide se corta a área urbana da análise. O procedimento
   urbano fica registrado como melhoria futura, não como lacuna esquecida.
3. **LOS por v/c é aproximação (D3).** O LOS reportado sai de faixas de v/c, não
   da densidade/*follower density* do HCM. Serve para ranquear gargalos; não
   equivale ao LOS oficial.

### 9.4 Saída auditável

A camada de arcos gerada traz, por arco: `volume`, `capacidade`, `v/c`, `LOS`,
tempo, `metodo` (`aon`/`msa`), `escopo` (`rodoviario`/`urbano`) e a
**proveniência de cada parâmetro** nos campos `src_*` (dado oficial, padrão
assumido ou definido pelo usuário), conforme D7.
