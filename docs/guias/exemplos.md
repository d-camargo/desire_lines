# Exemplos

O repositório traz dois conjuntos de dados prontos em `examples/`, um pequeno e
um grande, para percorrer as quatro abas de ponta a ponta sem precisar montar
dados próprios.

!!! note "Os exemplos não vêm dentro do plugin"
    `examples/` está marcado como `export-ignore` no `.gitattributes` — ou seja,
    fica **fora do zip instalado no QGIS** e só existe no repositório. Baixe os
    arquivos pelos links abaixo (ou clone o repo).

| Conjunto | Matriz OD (CSV) | Zonas de tráfego (GPKG) | Zonas | Formato da matriz |
|---|---|---|---|---|
| **Microrregiões de MG** | [`OD-MG_EXPORT.csv`](https://github.com/d-camargo/desire_lines/raw/main/examples/Microrregioes_MG/OD-MG_EXPORT.csv) | [`MICRO-MG.gpkg`](https://github.com/d-camargo/desire_lines/raw/main/examples/Microrregioes_MG/MICRO-MG.gpkg) | 66 | longo (uma linha por par) |
| **RMSP** | [`Tab24_OD2017.csv`](https://github.com/d-camargo/desire_lines/raw/main/examples/RMSP/Tab24_OD2017.csv) | [`zonas_2017_region_reproj_geometrias_corrigidas.gpkg`](https://github.com/d-camargo/desire_lines/raw/main/examples/RMSP/zonas_2017_region_reproj_geometrias_corrigidas.gpkg) | 517 | largo (*wide*) |

Comece pelo de **MG**: são 66 zonas, a matriz já está em formato longo e tudo
roda em segundos. O da **RMSP** é o caso realista — matriz larga, 517 zonas e
267 mil pares depois da conversão.

## Exemplo 1 — Microrregiões de MG

Matriz de **carga geral** entre as 66 microrregiões de Minas Gerais, com
cenários otimista/médio/pessimista para 2015, 2020, 2025, 2030 e 2035.

### Aba 1 — Matriz OD

1. *Ler CSV* ("Read CSV") em `OD-MG_EXPORT.csv`, com a caixa de **formato**
   **desmarcada** — o arquivo já está em formato longo, uma linha por par
   (4.356 = 66 × 66). O arquivo está em **windows-1252**, exatamente o
   encoding que o plugin assume, então os acentos dos nomes ("AIMORÉS") saem
   corretos.
2. *Ler Vetor* ("Read Vector") em `MICRO-MG.gpkg` (camada `traffic_zones`, 66
   polígonos, **EPSG:4674 / SIRGAS 2000** geográfico).
3. Defina o **GeoPackage de saída** e clique em *Adicionar Centroides*.

As colunas da matriz são:

| Coluna | Papel |
|---|---|
| `Origem` | id da zona de origem (inteiro, 154 a 219) |
| `Origem_Descr` | nome da microrregião de origem (só descritivo) |
| `Destino` / `Destino_Descr` | idem, para o destino |
| `Carga_Geral_<ano>_<cenário>` | 15 colunas de valor — escolha **uma** como campo de valor (ex.: `Carga_Geral_2015_Medio`) |

O campo de id nas zonas é **`Origem`** — mesmo nome e mesma numeração da
coluna de origem da matriz, então é ele que vai nos combos *ID de Tráfego*.

### Abas 2 e 3 — linhas de desejo e AoN

Preencha os dois combos de camada com `matrix` e `centroids` e os campos assim:

| Combo | Valor |
|---|---|
| *Origem* | `Origem` (da matriz) |
| *Destino* | `Destino` |
| *Valor* | `Carga_Geral_2015_Medio` (ou outro cenário) |
| *ID de Tráfego* | `Origem` (dos centroides) |

**O que esperar:**

- **Linhas de desejo:** **4.290 feições** — os 4.356 pares menos os 66
  intrazonais (`Origem = Destino`), que o plugin descarta e que nessa matriz
  são justamente os de valor zero.
- **AoN (Delaunay):** os centroides são geográficos e MG se estende da zona
  UTM 22 à 24, então o plugin cai na regra do **SIRGAS 2000 / Brazil Albers
  (EPSG:10857)** e diz isso na mensagem final. A camada `aon_flows` sai nesse
  CRS — não no EPSG:4674 da entrada.

### Aba 4 — alocação em rodovias

É o exemplo adequado para a aba 4: demanda **interurbana** sobre malha rural,
que é o escopo do procedimento HCM implementado. Use *Baixar via GisBR* com
**UF = `MG`** e *Recortar para a extensão dos centroides* marcada (com o
plugin [GisBR](https://github.com/d-camargo/gisbr) instalado), ou aponte uma
camada de rodovias própria.

!!! warning "A unidade da coluna de carga não é veíc/h"
    As colunas `Carga_Geral_*` são **carga**, não veículos por hora — e a
    capacidade do HCM é em **veículos por hora por sentido**. Alocar a coluna
    crua produz um v/c sem significado físico. Converta antes (carga → veículos
    equivalentes → hora de projeto) ou leia o resultado apenas como
    **distribuição relativa** de fluxo pela malha, não como v/c. Ver
    [Alocação em rodovias](alocacao-rodovias.md).

## Exemplo 2 — RMSP (matriz larga)

Matriz de viagens entre as 517 zonas OD da Região Metropolitana de São Paulo
(Pesquisa OD 2017), no formato de **tabela quadrada**: a primeira coluna se
chama `OD` e há uma coluna por zona de destino, de `1` a `517`.

### Aba 1 — Matriz OD

1. *Ler CSV* em `Tab24_OD2017.csv` com a caixa de **formato marcada** — é o
   caso *wide*. O plugin roda o `pandas.melt` e grava um `matrix_long.csv` ao
   lado do original, com as colunas **`Origem`**, **`Destino`** e
   **`Passageiros`** e **267.289 linhas** (517 × 517). Sem `pandas` no Python
   do QGIS a conversão não acontece — ver [Matriz OD](matriz-od.md).
2. *Ler Vetor* em `zonas_2017_region_reproj_geometrias_corrigidas.gpkg`: 517
   polígonos em **EPSG:31983 (SIRGAS 2000 / UTM 23S)**, já métrico.

Campos das zonas: `NumeroZona`, `NomeZona`, `NumeroMuni`, `NomeMunici`,
`NumDistrit`, `NomeDistri`, `Area_ha_2` e **`IDTRAF`**. Use **`IDTRAF`** como
*ID de Tráfego* — ele é idêntico a `NumeroZona` em todas as 517 zonas e casa
com a numeração 1–517 da matriz.

!!! danger "O ponto neste CSV é separador de milhar"
    3.152 células trazem valores como `1.016`, `1.489`, `2.919` — sempre com
    três dígitos depois do ponto. São **1.016 viagens**, não 1,016. Lido como
    número, `1.016` vira **1,016**, e justamente os maiores fluxos da matriz
    encolhem para menos de 3 viagens. **Antes de importar**, remova esses
    pontos no arquivo (localizar-e-substituir `.` por nada, num editor de
    texto). Se as linhas de desejo mais grossas do mapa parecerem os pares
    errados, é isso.

### Abas 2 e 3

| Combo | Valor |
|---|---|
| *Origem* | `Origem` |
| *Destino* | `Destino` |
| *Valor* | `Passageiros` |
| *ID de Tráfego* | `IDTRAF` |

**O que esperar:**

- **Linhas de desejo:** **266.772 feições** — todos os pares menos os 517
  intrazonais. A maioria tem valor zero: só **26.386** pares não-intrazonais
  têm viagens. Vale filtrar a camada (`"Passageiros" > 0`, ou um limiar bem
  mais alto) antes de tentar ler o mapa; a matriz inteira desenhada vira um
  bloco preto.
- **AoN (Delaunay):** os centroides já estão em CRS métrico, então o plugin
  **usa o EPSG:31983 como está** — sem reprojeção, ao contrário do exemplo de
  MG. São 517 centroides, bem acima do mínimo de 3.

### Aba 4 — por que não com este conjunto

A RMSP é **área urbana**, e a aba de rodovias foi feita para rodovias
rurais/interurbanas: os trechos de travessia urbana saem marcados com
`escopo='urbano'`, contados no aviso final e **não** recalculados por
procedimento urbano. Além disso a coluna `Passageiros` é de viagens diárias de
pessoas, não veículos por hora. Use este conjunto nas abas 1 a 3, e o de MG na
aba 4.

## Se algo não bater

- Nenhum par casou → *Origem*, *Destino* e *ID de Tráfego* estão em esquemas
  de id diferentes (`Origem` em MG, `IDTRAF` na RMSP).
- Fluxos grandes aparecendo pequenos na RMSP → o separador de milhar, acima.
- Mais detalhes em [Solução de problemas](../solucao-de-problemas.md),
  [Formatos de entrada](../referencia/formatos-de-entrada.md) e
  [Campos de saída](../referencia/campos-de-saida.md).
