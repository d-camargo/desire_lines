# Parâmetros HCM e Regra de Proveniência

Esta página apresenta a referência técnica completa de todos os parâmetros operacionais e geométricos utilizados no cálculo de capacidade viária pelo **HCM 6ª Edição** (Highway Capacity Manual) e na alocação de tráfego do plugin **Desire Lines**.

---

## 1. Regra de Proveniência dos Parâmetros (Decisão D7)

Para garantir transparência e auditabilidade técnica em estudos de planejamento de transportes, o plugin adota estritamente a **Regra D7 — "Nada é assumido em silêncio"**.

Nenhum parâmetro de capacidade é aplicado a uma rodovia sem que sua origem seja explicitamente declarada. Para cada parâmetro `X` utilizado, a camada de saída registra um campo correspondente `src_X` com o valor de proveniência indicando uma de quatro origens possíveis:

1. **`usuario`**: O valor foi informado ou sobrescrito manualmente pelo usuário na interface do plugin (parâmetro fixado com a opção *Fixar* ou valor informado em *Valor onde não há dado*).
2. **`oficial`**: O valor foi lido diretamente de um atributo existente na camada de rodovias (ex.: dados oficiais do SNV/DNIT ou DER obtidos via GISBR, ou campo mapeado na UI).
3. **`complementar`**: O valor foi obtido a partir de uma feição correspondente em uma **camada complementar** espacialmente associada por proximidade (Decisões D4 e D6).
4. **`padrao`**: O parâmetro não constava na tabela de atributos da camada nem no complemento e não foi informado na interface; o plugin aplicou o valor padrão documentado (padrão por classe ou padrão de fábrica).

### Hierarquia de Resolução

O módulo [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py) resolve o valor e a proveniência de cada parâmetro para cada segmento viário através da função `resolve()`, respeitando a seguinte ordem de precedência rigorosa em cascata (Decisões D4 e D7):

```
[ Parâmetro Fixado (Fixar) ]       ---> Se fixado pelo usuário na UI     ---> valor = UI,          src = 'usuario'
            | (se não fixado)
[ Campo Mapeado na UI ]            ---> Se campo selecionado na feição   ---> valor = Campo,       src = 'oficial'
            | (se ausente/nulo)
[ Tradução Oficial (D2) ]          ---> Se atributo oficial reconhecido  ---> valor = Traduzido,   src = 'oficial'
            | (se ausente/nulo)
[ Atributo Candidato ]             ---> Se campo candidato na feição    ---> valor = Feição,      src = 'oficial'
            | (se ausente/nulo)
[ Camada Complementar ]            ---> Se feição a até max_dist_m       ---> valor = Complemento, src = 'complementar'
            | (se ausente/nulo)
[ Valor onde não há dado ]         ---> Se digitado pelo usuário na UI   ---> valor = UI,          src = 'usuario'
            | (se padrão do catálogo)
[ Padrão por Classe ]              ---> Pista dupla / simples / não pav. ---> valor = Classe,      src = 'padrao'
            | (se ausente/nulo)
[ Padrão do Catálogo ]             ---> Fallback residual de fábrica     ---> valor = Catálogo,    src = 'padrao'
```

---

## 2. Tabela Completa de Parâmetros Operacionais e HCM

A tabela abaixo lista os 18 parâmetros gerenciados pelo plugin (definidos em [`traffic/params.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/params.py)), suas unidades, tipos, valores padrão e os campos oficiais buscados automaticamente nas camadas de entrada.

| Identificador (`id`) | Rótulo / Parâmetro | Unidade | Tipo | Valor Padrão | Campos Candidatos na Camada (Fonte Oficial) | Descrição / Valores Aceitos |
|---|---|---|---|---|---|---|
| `tipo_segmento` | Tipo de segmento | - | Texto (`str`) | `'2_faixas'` | `tipo_pista`, `pista`, `tipo_seg`, `tp_pista`, `ds_pista`, `tipo_segmento` | Classificação funcional do trecho: `2_faixas` (pista simples - Cap. 15), `multipista` (pista dupla/multilane - Cap. 12) ou `freeway` (autoestrada com acesso controlado - Cap. 12). |
| `lanes` | Número de faixas por sentido | faixas | Inteiro (`int`) | `1` | `faixas`, `num_faixas`, `faixas_sentido`, `nr_faixas`, `n_faixas`, `lanes` | Quantidade de faixas de rolamento disponíveis no sentido de tráfego analisado. |
| `pavimentado` | Pavimentado | - | Booleano (`bool`) | `True` | `pavimentado`, `superficie`, `tp_superficie`, `ds_superficie`, `st_pavimentado` | Indicador de pavimento. Define a classe da via para o padrão de velocidade livre (60 km/h para não pavimentada vs. 80 km/h pavimentada). O procedimento do HCM não aplica penalização direta sobre a capacidade. |
| `urbano` | Trecho urbano | - | Booleano (`bool`) | `False` | `urbano`, `trecho_urbano`, `travessia_urbana`, `tp_trecho`, `is_urbano` | Sinaliza se o segmento é uma travessia urbana (`True`) ou rodovia rural/interurbana (`False`). |
| `largura_faixa` | Largura de faixa | m | Decimal (`float`) | `3.5` | `largura_faixa`, `larg_faixa`, `lane_width` | Largura média das faixas de rolamento. Padrão norma DNIT: 3,50 m. |
| `largura_acostamento` | Largura de acostamento | m | Decimal (`float`) | `2.5` | `largura_acostamento`, `acostamento`, `shoulder_width` | Largura útil do acostamento lateral. Padrão norma DNIT: 2,50 m. |
| `terreno` | Tipo de terreno | - | Texto (`str`) | `'ondulado'` | `terreno`, `tp_terreno`, `ds_terreno`, `terrain` | Topografia do trecho: `plano` (flat), `ondulado` (rolling) ou `montanhoso` (mountainous). Impacta a equivalência de veículos pesados (`E_T`). |
| `pct_veic_pesados` | Percentual de veículos pesados | % | Decimal (`float`) | `20.0` | `pct_veic_pesados`, `pct_pesados`, `veic_pesados`, `pct_hv`, `heavy_vehicles` | Porcentagem da composição do tráfego formada por caminhões e ônibus em relação ao volume total. |
| `vel_livre` | Velocidade de fluxo livre (FFS) | km/h | Decimal (`float`) | `80.0` | `vel_livre`, `ffs`, `v_livre`, `vl_maxima`, `speed_limit` | Velocidade média observada sob baixo volume de tráfego (*Free-Flow Speed*). |
| `phf` | Fator de Hora de Pico (PHF) | - | Decimal (`float`) | `0.92` | `phf`, `fator_pico`, `peak_hour_factor` | Relação entre o volume total na hora pico e a taxa máxima no subintervalo de 15 min (*Peak Hour Factor*). |
| `pct_no_passing` | Zonas de ultrapassagem proibida | % | Decimal (`float`) | `50.0` | `pct_no_passing`, `ultrapassagem_proibida`, `pct_proib_ultrapassagem` | Porcentagem da extensão do trecho de pista simples com marcação contínua de proibição de ultrapassagem. |
| `access_density` | Densidade de acessos | acessos/km | Decimal (`float`) | `10.0` | `access_density`, `densidade_acessos`, `n_acessos_km` | Número de intersecções, acessos comerciais e entradas por quilômetro (usado no cálculo de FFS para multipistas). |
| `directional_split` | Divisão direcional | % | Decimal (`float`) | `50.0` | `directional_split`, `divisao_direcional`, `split_dir` | Proporção de fluxo no sentido principal (ex.: 50 para 50/50, 60 para 60/40). |
| `bpr_alpha` | Alfa da função BPR | - | Decimal (`float`) | `0.15` | `bpr_alpha`, `alpha_bpr` | Coeficiente `alfa` da equação de tempo de viagem `t = t0 * [1 + alfa * (v/c) ^ beta]`. Aplicado por arco quando presente. |
| `bpr_beta` | Beta da função BPR | - | Decimal (`float`) | `4.0` | `bpr_beta`, `beta_bpr` | Expoente `beta` da equação de congestionamento BPR. Aplicado por arco quando presente. |
| `capacidade` | Capacidade por sentido (0 = HCM) | veíc/h | Decimal (`float`) | `0.0` | `capacidade`, `capacity`, `cap`, `capacidade_vph` | Capacidade informada por sentido. A **sentinela 0.0** indica cálculo automático pelo HCM (Cap. 12 ou 15). Se `> 0`, tem precedência sobre o HCM (mantendo o `escopo`). |
| `tempo_livre` | Tempo de fluxo livre (0 = comprimento ÷ FFS) | min | Decimal (`float`) | `0.0` | `tempo_livre`, `free_flow_time`, `fft`, `t0` | Tempo de viagem em fluxo livre no arco. A **sentinela 0.0** indica cálculo geométrico (`comprimento ÷ vel_livre`). Se `> 0`, tem precedência sobre o cálculo. |
| `mao_unica` | Mão única (sentido da geometria) | - | Booleano (`bool`) | `False` | `mao_unica`, `oneway`, `one_way`, `sentido_unico` | Se `True`, o trecho gera apenas o arco no sentido de digitalização da geometria (`fw`), omitindo o arco reverso (`bw`). Se `False`, opera em mão dupla gerando `fw` e `bw`. |

---

### 2.1 A Sentinela `0.0` e Parâmetros Informados

Os parâmetros `capacidade` e `tempo_livre` adotam o valor **`0.0` como sentinela explícita** para "calcular automaticamente":

* **Por que `0.0` e não `None`?** A interface do plugin gera dinamicamente controles numéricos (`QDoubleSpinBox`) a partir das especificações de `PARAMS`. O valor `None` não é representável diretamente em um *spinbox* numérico Qt, e um valor positivo arbitrário como padrão sobrescreveria toda a malha caso o usuário não informasse um campo.
* **Precedência na construção da rede**:
    * Se `capacidade > 0.0`: a capacidade do arco recebe esse valor exato (com proveniência `oficial` se veio da camada, ou `usuario` se veio da UI), preservando a classificação de `escopo` (`rodoviario` ou `urbano`). Se `capacidade <= 0.0`, aciona o procedimento analítico do HCM 6ª Edição (`segment_capacity`).
    * Se `tempo_livre > 0.0`: o tempo `t0` recebe o valor informado em minutos. Se `tempo_livre <= 0.0`, calcula `t0 = (comprimento_km / vel_livre_kmh) * 60.0`.
* **Mão única (`mao_unica`)**:
    * Quando `mao_unica` resolve para `True` (reconhecendo valores textuais ou numéricos como `True`, `1`, `'sim'`, `'yes'`, `'oneway'`), a rede viária constrói **apenas o arco no sentido direto (`fw`)** e define `arc_bw = None`. Isso garante que malhas já orientadas (como a de Sioux Falls ou bases municipais direcionadas) não tenham sua capacidade artificialmente duplicada por arcos reversos fictícios.

---

---

## 3. Como a capacidade é estimada (Decisão D9)

A estimativa de capacidade de cada segmento viário segue um processo estruturado em três níveis:
1. **O que já existe nos dados oficiais** (geometria básica, tipo de pista, pavimento e identificação);
2. **Informações complementares** espacialmente associadas (redes OSM, postos de contagem, perímetros urbanos);
3. **Valores padrão** por classe de rodovia e catálogo residual do HCM.

A resolução dos 18 parâmetros operacionais e geométricos ocorre pela função `params.resolve()`, que implementa uma **cascata rigorosa de 8 etapas** (Decisão D4). A primeira etapa que fornecer um valor válido define o parâmetro; valores nulos, vazios ou que não convertem para o tipo esperado fazem a resolução avançar para a etapa seguinte.

A resolução é executada em **duas passadas**:
1. **Primeira passada**: resolve `tipo_segmento` e `pavimentado`, que classificam a via para os padrões de velocidade e faixas.
2. **Segunda passada**: resolve os demais 16 parâmetros operacionais.

### As 8 etapas da cascata de resolução (Decisão D4)

1. **Parâmetros fixados pelo usuário (`overrides`)** &rarr; proveniência **`usuario`**: Linhas da tabela de parâmetros com a opção **Fixar** (*Fix*) marcada na interface e sem campo de camada mapeado. Força o valor especificado sobre toda a malha, sobrepondo dados oficiais.
2. **Campo mapeado na camada (`field_map`)** &rarr; proveniência **`oficial`**: Coluna da camada viária explicitamente selecionada no combo *Campo da camada* (*Layer field*).
3. **Tradução automática de atributos da feição (`oficiais.traduz`)** &rarr; proveniência **`oficial`**: Reconhecimento automático dos campos brutos das fontes oficiais (DNIT, DER-SP) e colaborativas (OSM). Permite ler bases brutas ou GeoPackages legados sem necessidade de mapeamento manual.
4. **Campos candidatos na feição (`campos_candidatos`)** &rarr; proveniência **`oficial`**: Busca automática pelos nomes padrão do catálogo (ver Seção 2). Como a lista de candidatos inclui o próprio identificador do parâmetro, a malha padronizada baixada via GisBR (Decisão D3) é lida diretamente nesta etapa.
5. **Camada complementar por proximidade (`complemento`)** &rarr; proveniência **`complementar`**: Atributos da feição mais próxima a até a distância máxima configurada (padrão 30 m), processados primeiro por `oficiais.traduz()` e em seguida por `campos_candidatos`.
6. **Valor onde não há dado (`defaults`)** &rarr; proveniência **`usuario`**: Valores digitados na coluna *Valor onde não há dado* na interface sem a opção *Fixar* ativada, utilizados como preenchimento apenas onde a rede e o complemento não trouxeram informação.
7. **Padrão por classe de rodovia (`PADRAO_POR_CLASSE`)** &rarr; proveniência **`padrao`**: Se `lanes` ou `vel_livre` não foram obtidos nas etapas anteriores, adota valores típicos conforme a classe definida na primeira passada:
    - **Pista dupla**: 2 faixas por sentido, velocidade livre de 100 km/h;
    - **Pista simples pavimentada**: 1 faixa por sentido, velocidade livre de 80 km/h;
    - **Não pavimentada**: 1 faixa por sentido, velocidade livre de 60 km/h.
8. **Padrão de fábrica do catálogo (`PARAMS`)** &rarr; proveniência **`padrao`**: Valor padrão residual definido nas especificações de cada parâmetro no catálogo do plugin.

### Regras de tradução das fontes oficiais e OSM (Decisão D2a)

O módulo `traffic/oficiais.py` traduz atributos de bases oficiais para os parâmetros HCM sem diferenciar maiúsculas/minúsculas e normalizando acentos e espaços:

| Campo (fonte) | Valores reconhecidos | Parâmetros HCM resultantes |
|---|---|---|
| `TipoPista` (DER-SP), `Superficie_Federal` (SNV/DNIT) | `DUP` | `tipo_segmento = 'pista_dupla'`, `pavimentado = True` |
| idem | `PAV`, `EOD` | `tipo_segmento = '2_faixas'`, `pavimentado = True` |
| idem | `IMP`, `EOP`, `LEN` | `tipo_segmento = '2_faixas'`, `pavimentado = False` |
| `PerimetroU` (DER-SP) | Começa com `S` (`Sim`, `S`) | `urbano = True` |
| idem | Começa com `N` (`Não`, `Nã`, `N`) | `urbano = False` |
| `lanes` + `oneway` (OSM) | Se `oneway` em {`yes`, `true`, `1`} | `lanes = int(lanes)` |
| idem | Se `oneway` em {`no`, `false`, `0`} ou ausente | `lanes = max(1, int(lanes) // 2)` |
| `oneway` (OSM) | `yes`, `true`, `1` &rarr; `mao_unica = True`; `no`, `false`, `0` &rarr; `False` | `mao_unica = True` ou `False` (`-1` não traduz) |
| `maxspeed` (OSM) | Valor numérico em km/h | Se limite &ge; 80 km/h: `vel_livre = limite + 8`<br>Se limite < 80 km/h: `vel_livre = limite + 11` (HCM 6ª ed. cap. 12: FFS = limite + 5 mi/h ou + 7 mi/h abaixo de 50 mi/h) |

!!! note "Velocidade calculada no GisBR não entra nas regras"
    O atributo `velocidade_kmh` gerado pelo plugin GisBR na extração do OSM **não** é traduzido automaticamente. Quando uma via OSM não possui a etiqueta `maxspeed`, o GisBR estima a velocidade média com base na classificação `highway`. Marcá-la como `complementar` violaria a regra de que *nada é assumido em silêncio*; caso o usuário deseje utilizá-la, deve mapear o campo explicitamente.

### O que as bases oficiais (DNIT e DER-SP) trazem e o que falta

Ao baixar a malha oficial do estado de São Paulo via GisBR (composta pela malha federal DNIT/SNV e pela malha estadual DER-SP), os dados oficiais cobrem diretamente apenas a geometria básica e poucos atributos operacionais:

| Parâmetro HCM | DNIT (SNV) | DER-SP | Observação técnica |
|---|:---:|:---:|---|
| `tipo_segmento` | :white_check_mark: (`Superficie_Federal`) | :white_check_mark: (`TipoPista`) | Traduz `DUP` para pista dupla e `PAV`/`IMP` para 2 faixas. |
| `pavimentado` | :white_check_mark: (`Superficie_Federal`) | :white_check_mark: (`TipoPista`) | Identifica revestimento asfáltico ou leito natural. |
| `urbano` | :x: | :white_check_mark: (`PerimetroU`) | DNIT não possui indicação de perímetro urbano; DER-SP indica com `Sim`/`Nã`. |
| `lanes` | :x: | :x: | Nenhuma das bases oficiais informa a contagem exata de faixas. |
| `vel_livre` | :x: | :x: | Não trazem velocidade regulamentada ou de fluxo livre. |
| `pct_veic_pesados` | :x: | :x: | Não informam composição veicular por trecho físico. |
| `terreno` | :x: | :x: | Relevo (plano, ondulado, montanhoso) não consta nas tabelas. |
| `largura_faixa` | :x: | :x: | Não informado; utiliza padrão normativo (3,5 m). |
| `largura_acostamento` | :x: | :x: | Não informado; utiliza padrão normativo (2,5 m). |
| `access_density` | :x: | :x: | Não mapeado nas bases rodoviárias oficiais. |
| `pct_no_passing` | :x: | :x: | Não mapeado nas bases rodoviárias oficiais. |
| `phf` | :x: | :x: | Não informado; utiliza padrão de planejamento (0,92). |
| `directional_split` | :x: | :x: | Não informado; adota divisão simétrica 50/50. |
| `mao_unica` | :x: | :x: | Deduzido pela geometria/duplicação ou via camada complementar OSM. |

Como demonstrado pela tabela, os dados oficiais sozinhos deixam lacunas em parâmetros fundamentais como número de faixas, velocidade livre e composição do tráfego.

### Receita de enriquecimento para São Paulo (Etapa 2 — Camada complementar)

Para obter estimativas de capacidade de alta fidelidade no estado de São Paulo, recomenda-se combinar a malha oficial com camadas complementares (associadas na aba Capacidade pelo grupo *Dados complementares*):

1. **Faixas e velocidades via OpenStreetMap (QuickOSM)**:
   - Baixar pelo plugin QuickOSM os eixos rodoviários com a chave `highway` igual a `motorway`, `trunk` ou `primary` contendo as tags `lanes`, `oneway` e `maxspeed`.
   - Como a camada complementar é casada espacialmente com a malha oficial a até 30 m, os atributos de `lanes`, `vel_livre` e `mao_unica` são imediatamente absorvidos com proveniência `complementar`.
2. **Rede OSM pré-processada do GisBR Base (`osm_links_rm<id>`)**:
   - Em Regiões Metropolitanas atendidas pelo repositório [`gisbr_base`](https://github.com/d-camargo/gisbr_base), a camada de links viários fornece a geometria tratada com `maxspeed` e `oneway`, complementando a velocidade e o sentido de tráfego.
3. **Percentual de pesados a partir de postos de contagem**:
   - Uma camada de pontos com os postos de monitoramento (DER-SP ou DNIT) contendo a coluna `pct_veic_pesados` ou `pct_pesados` transfere a composição de tráfego medida em campo para as rodovias adjacentes.
4. **Perímetro urbano para o SNV via polígonos do IBGE**:
   - Como o DNIT não traz o atributo urbano, vincular como camada complementar o mapeamento de **Áreas Urbanizadas do IBGE** com um campo `urbano = 1` marca automaticamente as travessias urbanas das rodovias federais (`escopo = 'urbano'`).

---

## 4. Procedimento de Sobrescrita e Mapeamento

### 4.1 Mapeamento Direto por Campo na Interface (Decisão D7)

No painel **Alocação em rodovias**, na aba **Capacidade**, a tabela de parâmetros dispõe de uma coluna *Campo da camada* (*Layer field*) que permite selecionar diretamente qualquer coluna da camada viária.

* **Precedência do mapeamento (D4/D7)**: Quando o usuário seleciona uma coluna no combo de um parâmetro, esse nome de campo é enviado no dicionário `field_map = {param_id: nome_do_campo}` para o método `params.resolve()`.
* **Identificação oficial**: Qualquer valor lido com sucesso a partir da coluna mapeada é registrado com proveniência **`oficial`**, mesmo que o nome do campo na sua base seja completamente diferente dos candidatos pré-cadastrados (por exemplo, uma coluna chamada `cap_veic_hora` ou `t_zero`).
* **Fallback gracioso**: Se o campo mapeado contiver valor nulo, vazio ou inválido em determinada feição, a cascata segue para as etapas seguintes (tradução oficial, candidatos, complemento e padrões).

### 4.2 Leitura Automática por Candidatos (`oficial`)

Se nenhum campo for selecionado no combo da interface, o plugin inspeciona automaticamente o esquema da camada em busca dos nomes listados em `campos_candidatos` (tabela da Seção 2). A busca é insensível a maiúsculas/minúsculas (`CAPACITY`, `Capacity` e `capacity` são tratados identicamente). O primeiro candidato com dado válido define o parâmetro como `oficial`.

### 4.3 Fixação e Valores Globais na Interface (`usuario`)

A tabela de parâmetros oferece duas formas de intervenção do usuário:

* **Coluna Fixar (*Fix*)**: Marcada a caixa de seleção de um parâmetro (e sem campo mapeado), o valor digitado torna-se um *override* (etapa 1 da cascata). Ele prevalece sobre atributos da camada e complementos, forçando o valor em todos os trechos com proveniência **`usuario`**.
* **Coluna Valor onde não há dado (*Value where there is no data*)**: Sem a caixa *Fixar* marcada, o valor digitado é utilizado apenas como preenchimento residual (etapa 6 da cascata) caso a camada viária e os complementos não forneçam informação. Se for modificado em relação ao padrão de fábrica, é registrado como **`usuario`**.

Para os parâmetros com sentinela (`capacidade` e `tempo_livre`), o valor `0.0` sinaliza que o cálculo analítico do HCM ou a estimativa geométrica devem ser preservados.

### 4.4 Valores Padrão Assumidos (`padrao`)

Se um parâmetro não possuir fixação, não for encontrado nem por mapeamento, nem por tradução de atributos, nem por candidatos, nem em camada complementar e não tiver valor modificado na interface, o plugin adota o padrão por classe de via ou o valor residual do catálogo `PARAMS`.

* A proveniência correspondente será marcada como **`padrao`**.
* Ao término da execução de **Calcular capacidade** ou **Alocar**, a barra de mensagens exibe o resumo de quantos pares (arco, parâmetro) vieram de cada fonte (`oficial`, `complementar`, `usuario`, `padrao`), assegurando total rastreabilidade (Regra D7).
