# Campos de saída

Esta página apresenta a especificação técnica completa dos campos de atributos gerados em cada uma das camadas vetoriais de saída do plugin **Desire Lines**.

---

## 1. Camada de Linhas de Desejo (Aba 2)

A camada de **Linhas de Desejo** (*Desire Lines*) é gerada a partir da união (*JOIN*) entre a matriz OD e os centroides das zonas de tráfego. Cada feição representa um vetor reto (linha) conectando o centroide da zona de origem ao centroide da zona de destino para todos os pares OD com fluxo maior que zero (autopares onde origem é igual ao destino são descartados).

* **Nome padrão da camada / tabela:** `Desire_Lines` (salva no GeoPackage de saída ou como camada vetorial em memória).
* **Tipo de Geometria:** Linha (`LineString`).

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `<campo_origem>` | Texto ou Inteiro | - | Identificador da zona de origem do par OD (herdado do campo selecionado no CSV da matriz). |
| `<campo_destino>` | Texto ou Inteiro | - | Identificador da zona de destino do par OD (herdado do campo selecionado no CSV da matriz). |
| `<campo_fluxo>` | Decimal (`Double`) | Demanda (passageiros, veíc, etc.) | Volume de demanda/viagens associado ao par OD. |
| `geometry` | Linha (`LineString`) | - | Geometria da reta conectando a origem ao destino. |

!!! note "Nomes das colunas da camada"
    Os nomes reais das colunas `<campo_origem>`, `<campo_destino>` e `<campo_fluxo>` correspondem aos nomes dos campos selecionados nos *comboboxes* da interface na Aba 2 (ex.: `Origem`, `Destino`, `Passageiros`).

---

## 2. Camada de Alocação Sintética AoN Delaunay (Aba 3)

A camada de **Alocação Sintética AoN sobre rede Delaunay** contém os segmentos de reta resultantes da triangulação de Delaunay entre os centroides, acumulando o fluxo de viagens alocado pelos caminhos mínimos (Dijkstra) entre todos os pares OD.

* **Nome padrão da camada:** `aon_flows`
* **Tipo de Geometria:** Linha (`LineString`)
* **Módulo responsável:** `aon.py` (`edge_flows_to_layer`)

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `flow` | Decimal (`Double`) | Demanda (veíc/h ou unidades de fluxo) | Volume total de tráfego alocado no segmento da rede Delaunay. Corresponde à soma dos fluxos em ambas as direções do segmento (`flow = flow_ab + flow_ba`). |
| `flow_ab` | Decimal (`Double`) | Demanda | Volume alocado no sentido de orientação A -> B (do primeiro ao segundo vértice da feição). Gerado quando a opção **Split by direction** está ativada. |
| `flow_ba` | Decimal (`Double`) | Demanda | Volume alocado no sentido de orientação B -> A (do segundo ao primeiro vértice da feição). Gerado quando a opção **Split by direction** está ativada. |

---

## 3. Camada de Capacidade HCM (Aba 4 — Pré-alocação)

Gerada ao executar o comando **Calcular capacidade** (*Compute capacity*) na quarta aba do plugin. Contém a malha viária processada e simplificada com as capacidades calculadas segundo os procedimentos do HCM 6ª Edição (Capítulos 12 e 15), antes de receber qualquer alocação de demanda.

* **Nome padrão da camada:** `capacidade_hcm`
* **Tipo de Geometria:** Linha (`LineString`)
* **Módulo responsável:** `traffic/outputs.py` (`flows_to_layer`)

Possui exatamente os mesmos campos descritos na seção abaixo (Alocação em Rodovias Reais), mas com os seguintes valores padrão de pré-alocação:

* `volume = 0.0`
* `vc = 0.0`
* `los = 'A'`
* `tempo_h = tempo em fluxo livre (t0)`
* `atraso_h = 0.0`
* `metodo = 'capacidade'`

---

## 4. Camada de Alocação em Rodovias Reais (Aba 4 — AoN / MSA)

Gerada após executar a alocação de demanda da matriz OD sobre a malha rodoviária real (SNV/DER) através do comando **Alocar** (*Assign*).

* **Nome padrão da camada:** `alocacao_aon` (para método All-or-Nothing) ou `alocacao_msa` (para método de Equilíbrio MSA).
* **Tipo de Geometria:** Linha (`LineString`)
* **Módulo responsável:** `traffic/outputs.py` (`flows_to_layer`)

### Atributos Principais de Tráfego e Desempenho

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `arc_id` | Texto (`String`) | - | Identificador único do arco direcionado no grafo (ex.: `('link101', 'fw')` ou `('link101', 'bw')`). |
| `link_id` | Texto (`String`) | - | Identificador do segmento/link original da malha rodoviária de entrada (ex.: código do trecho SNV/DER). |
| `sentido` | Texto (`String`) | - | Sentido de trafegabilidade do arco: `fw` (*forward* — idêntico à orientação da geometria) ou `bw` (*backward* — inverso à geometria). |
| `faixas` | Inteiro (`Int`) | faixas | Número de faixas de rolamento disponíveis por sentido no trecho. |
| `comp_m` | Decimal (`Double`) | m | Comprimento real do trecho viário em metros. |
| `vel_livre` | Decimal (`Double`) | km/h | Velocidade de fluxo livre (*Free-Flow Speed* - FFS) considerada no cálculo. |
| `capacidade` | Decimal (`Double`) | veíc/h | Capacidade teórica máxima por sentido calculada segundo as normas do HCM 6ª Edição. |
| `volume` | Decimal (`Double`) | veíc/h | Volume total de tráfego alocado sobre o arco após a resolução do modelo de alocação. |
| `vc` | Decimal (`Double`) | adimensional | Razão Volume/Capacidade do arco (`v/c = volume / capacidade`). |
| `los` | Texto (`String`) | - | Nível de Serviço (*Level of Service*) operacional do trecho, de `A` a `F`, derivado do indicador `v/c`. |
| `tempo_h` | Decimal (`Double`) | h | Tempo total de viagem no trecho sob o fluxo alocado, determinado pela função de desempenho BPR (`t = t0 * [1 + alfa * (v/c) ^ beta]`). |
| `atraso_h` | Decimal (`Double`) | h | Atraso por trecho provocado pelo congestionamento em relação ao tempo em fluxo livre (`tempo_h - t0`). |
| `metodo` | Texto (`String`) | - | Algoritmo de alocação empregado: `aon` (*All-or-Nothing*) ou `msa` (*Successive Averages Equilibrium*). |
| `escopo` | Texto (`String`) | - | Classificação do escopo territorial: `rodoviario` (rodovia rural/interurbana com capacidade HCM) ou `urbano` (travessia urbana mantida na rede sem recálculo de capacidade). |

---

### Campos de Proveniência dos Parâmetros HCM (`src_*`)

Para atender ao princípio de transparência total dos dados (**Regra D7 — "Nada é assumido em silêncio"**), a camada de saída inclui 15 campos adicionais indicando a proveniência exata de cada parâmetro utilizado no cálculo da capacidade.

Os campos `src_*` podem assumir um dos três valores possíveis:

* **`oficial`**: O parâmetro foi lido diretamente de um atributo existente na camada de rodovias de entrada.
* **`usuario`**: O parâmetro foi informado ou sobrescrito manualmente pelo usuário na interface do plugin.
* **`padrao`**: O parâmetro não constava na camada de entrada e o plugin aplicou o valor padrão alinhado às diretrizes do DNIT/HCM.

| Campo de Proveniência | Parâmetro Associado | Descrição |
|---|---|---|
| `src_tipo_segmento` | `tipo_segmento` | Proveniência da tipologia do trecho (`2_faixas`, `multipista`, `freeway`). |
| `src_lanes` | `lanes` | Proveniência do número de faixas por sentido. |
| `src_pavimentado` | `pavimentado` | Proveniência do indicador de pavimentação. |
| `src_urbano` | `urbano` | Proveniência da indicação de travessia urbana. |
| `src_largura_faixa` | `largura_faixa` | Proveniência da largura da faixa de rolamento (m). |
| `src_largura_acostamento` | `largura_acostamento` | Proveniência da largura do acostamento (m). |
| `src_terreno` | `terreno` | Proveniência do tipo de terreno (plano, ondulado, montanhoso). |
| `src_pct_veic_pesados` | `pct_veic_pesados` | Proveniência do percentual de veículos pesados (caminhões e ônibus). |
| `src_vel_livre` | `vel_livre` | Proveniência da velocidade de fluxo livre (km/h). |
| `src_phf` | `phf` | Proveniência do Fator de Hora de Pico (*Peak Hour Factor*). |
| `src_pct_no_passing` | `pct_no_passing` | Proveniência do percentual de trecho com proibição de ultrapassagem. |
| `src_access_density` | `access_density` | Proveniência da densidade de acessos por quilômetro (acessos/km). |
| `src_directional_split` | `directional_split` | Proveniência da distribuição direcional do tráfego (ex.: 50/50, 60/40). |
| `src_bpr_alpha` | `bpr_alpha` | Proveniência do parâmetro `alfa` da equação de impedância BPR. |
| `src_bpr_beta` | `bpr_beta` | Proveniência do parâmetro `beta` da equação de impedância BPR. |

---

## 5. Simbologia e Estilo Graduado por v/c

As camadas de saída de alocação em rodovias (`alocacao_aon` e `alocacao_msa`) são configuradas automaticamente com um renderizador de simbologia graduada nativo do QGIS (`QgsGraduatedSymbolRenderer`) aplicado sobre o campo **`vc`**.

O estilo utiliza uma escala de cores intuitiva de 6 classes (de verde escuro a roxo) acompanhada pelo aumento na espessura das linhas:

| Nível de Serviço | Intervalo de `v/c` | Cor Hexadecimal | Espessura (mm) | Condição Operacional |
|:---:|:---:|:---:|:---:|---|
| **LOS A** | `v/c <= 0.35` | `#1a9641` | 0.6 mm | **Fluxo Livre:** Condição excelente, sem restrição de manobra. |
| **LOS B** | `0.35 < v/c <= 0.55` | `#a6d96a` | 0.8 mm | **Fluxo Estável:** Pequeno aumento de densidade, velocidades mantidas. |
| **LOS C** | `0.55 < v/c <= 0.75` | `#ffffbf` | 1.0 mm | **Fluxo Restrito:** Liberdade de manobra reduzida, velocidade influenciada pelo tráfego. |
| **LOS D** | `0.75 < v/c <= 0.90` | `#fdae61` | 1.2 mm | **Fluxo Próximo da Instabilidade:** Alta densidade, pequenas perturbações causam retenção. |
| **LOS E** | `0.90 < v/c <= 1.00` | `#d7191c` | 1.5 mm | **Capacidade Máxima:** Operação no limite operacional, fluxo altamente instável. |
| **LOS F** | `v/c > 1.00` | `#7b3294` | 2.0 mm | **Sobre-saturação:** Demanda excede a capacidade teórica; formação de filas e congestionamento. |

!!! warning "LOS como aproximação operacional"
    A atribuição do Nível de Serviço no campo `los` e na simbologia automática é uma **aproximação derivada do indicador `v/c`**. O procedimento oficial do HCM 6ª Edição define o LOS através de parâmetros de desempenho específicos: *Percent Time-Spent-Following (PTSF)* e *Average Travel Speed (ATS)* para rodovias de pista simples (Capítulo 15), ou densidade de veículos por quilômetro e por faixa para rodovias multifaixas e freeways (Capítulo 12).
