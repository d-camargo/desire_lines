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

O plugin abre um diálogo com **três abas**:

| Aba | objectName | O que faz |
|-----|-----------|-----------|
| **Origin/Destination Matrix** | `tab` | Importa a matriz OD (CSV) e a camada de zonas; gera centroides; define o GeoPackage de saída. |
| **Desire Lines** | `tab_2` | Gera as linhas de desejo (uma reta por par OD) ligando centroides, com espessura proporcional ao fluxo. |
| **AoN (Delaunay)** | `tab_3` | Aloca a demanda OD sobre uma rede Delaunay dos centroides via All-or-Nothing (menor caminho). |

### Arquivo de saída único (Output GeoPackage)

Todas as etapas escrevem **tabelas dentro do mesmo arquivo `.gpkg`** definido em
**Output GeoPackage** (aba 1). É o destino único de tudo que o plugin produz:

| Tabela | Gerada por |
|--------|-----------|
| `output` | Leitura da matriz CSV (botão *Read CSV*) |
| `centroids` | Botão *Add Centroids to Traffic Zones* |
| `Desire_Lines` | Botão *Desire Lines* (aba 2) |
| `aon_flows` | Botão *Allocate (AoN)* (aba 3) |

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

## 5. Arquitetura do código

```
desire_lines/
├── desirelines.py            # Classe do plugin: initGui(), run(), unload().
│                             #   run() cria o dialog 1× e configura filtros dos combos.
├── desirelines_dialog.py     # Toda a lógica de UI/execução das 3 abas.
│                             #   matrix(), fvector(), centroids(), desirelines(), run_aon().
├── aon.py                    # Núcleo AoN puro (sem GUI), testável no Console QGIS.
│                             #   pick_metric_crs, build_delaunay_edges, allocate_aon, ...
├── desirelines_dialog_base.ui# Interface Qt Designer (3 abas).
└── test/test_aon.py          # Testes do núcleo AoN (rodar no harness QGIS).
```

**Princípio de design**: `aon.py` é **livre de GUI** — só `qgis.core`,
`qgis.analysis` e Processing nativo, **zero dependências externas** (sem
NetworkX). Isso o torna testável isoladamente. A wiring de UI fica em
`desirelines_dialog.py` (`run_aon`).

### Separação de responsabilidades

- `desirelines.py` → ciclo de vida do plugin e **configuração dos filtros** dos
  combos (PointLayer/NoGeometry/Int/Double) em `run()`.
- `desirelines_dialog.py` → leitura de widgets, validação, chamadas a Processing
  e escrita no GeoPackage.
- `aon.py` → matemática/grafo puros.

---

## 6. Testes

`test/test_aon.py` cobre o núcleo (exige aplicação QGIS — rodar no harness):

- **`PickMetricCrsTest`**: passthrough métrico (EPSG:32723), zona única →
  UTM automático, multi-zona → Albers.
- **`AllocateAonTest`**:
  - `test_flow_follows_shortest_path` — fluxo segue o menor caminho A-B-C;
  - `test_directions_are_kept_separate` — sentidos opostos somam separados
    (comparação independente de orientação: `min`/`max` de `ab`/`ba`);
  - `test_unreachable_is_counted` — grafo desconexo conta `unreachable`.

---

## 7. Notas e limitações

- O plugin **não roda fora do QGIS** (imports PyQGIS exigem o ambiente QGIS).
- O AoN é uma **abstração topológica** da demanda sobre a vizinhança das zonas,
  **não** carregamento em rede viária real.
- Sem PSL (Path-Size Logit) nem UE (User Equilibrium) — exigiriam
  k-shortest-paths e iterações BPR+MSA.
- A conversão wide→long da matriz depende de **`pandas`** no Python do QGIS.
- Encoding fixo da matriz: `windows-1252`, delimitador `;`.
- Para recarregar após mudanças no código/UI, use o **Plugin Reloader** no QGIS.
