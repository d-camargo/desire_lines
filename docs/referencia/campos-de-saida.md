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

## 3. Malha baixada do GisBR (Aba 4 — malha_gisbr_<uf>)

Gerada ao executar o comando **Baixar malha** (*Download network*) na aba Rede do painel de rodovias. A malha une as bases oficiais selecionadas (como DNIT e DERs estaduais), aplicando remoção de duplicidades, corte de sobreposições e costura topológica.

A partir da versão 0.10.0 (Decisões D2 e D3), a camada é gravada com um **esquema padronizado de 21 colunas** no vocabulário técnico do HCM, idêntico para qualquer Unidade da Federação.

* **Nome padrão da camada / tabela:** `malha_gisbr_<uf>` (ex.: `malha_gisbr_sp`, `malha_gisbr_mg`), gravada no GeoPackage compartilhado de saída.
* **Tipo de Geometria:** Linha (`LineString`).
* **Módulos responsáveis:** `traffic/malha_gisbr.py` e `traffic/oficiais.py`.

### Especificação das 21 Colunas Padronizadas

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `fonte` | Texto (`String`) | - | Identificador da fonte oficial de origem no GisBR (ex.: `dnit_snv`, `der_sp_rodovias`). |
| `ajuste` | Texto (`String`) | - | Tratamento geométrico recebido na união: vazio (original intacto), `aparada` (corte de sobreposição), `costurada` (nó conectado) ou `aparada+costurada`. |
| `rodovia` | Texto (`String`) | - | Código ou sigla da rodovia (ex.: `BR-116`, `SP 095`). |
| `codigo_trecho` | Texto (`String`) | - | Identificador único do trecho ou subtrecho no cadastro do órgão de origem. |
| `km_ini` | Decimal (`Real`) | km | Quilometragem de início do trecho rodoviário na fonte oficial. |
| `km_fim` | Decimal (`Real`) | km | Quilometragem de término do trecho rodoviário na fonte oficial. |
| `administracao` | Texto (`String`) | - | Órgão ou regime de administração da rodovia (ex.: estadual, federal, concessionária). |
| `tipo_segmento` | Texto (`String`) | - | Tipologia HCM: `pista_dupla`, `2_faixas`, etc. |
| `lanes` | Inteiro (`Integer`) | faixas | Número de faixas de rolamento por sentido. |
| `pavimentado` | Inteiro (`Integer`) | 0/1 | Indicador de pavimento: `1` para pavimentado, `0` para não pavimentado. |
| `urbano` | Inteiro (`Integer`) | 0/1 | Indicador de travessia urbana: `1` para urbano, `0` para rural/interurbano. |
| `largura_faixa` | Decimal (`Real`) | m | Largura média da faixa de rolamento em metros. |
| `largura_acostamento` | Decimal (`Real`) | m | Largura média do acostamento em metros. |
| `terreno` | Texto (`String`) | - | Classificação do relevo (`plano`, `ondulado`, `montanhoso`). |
| `pct_veic_pesados` | Decimal (`Real`) | % | Percentual de veículos pesados (caminhões e ônibus). |
| `vel_livre` | Decimal (`Real`) | km/h | Velocidade de fluxo livre (*Free-Flow Speed* - FFS). |
| `phf` | Decimal (`Real`) | - | Fator de Hora de Pico (*Peak Hour Factor*). |
| `pct_no_passing` | Decimal (`Real`) | % | Percentual de extensão com ultrapassagem proibida. |
| `access_density` | Decimal (`Real`) | acessos/km | Densidade de acessos por quilômetro. |
| `directional_split` | Decimal (`Real`) | % | Distribuição direcional do fluxo. |
| `mao_unica` | Inteiro (`Integer`) | 0/1 | Sentido de circulação: `1` para mão única no sentido da geometria, `0` para mão dupla. |

### Tabela de Mapeamento da Identificação Oficial (D2c)

Para cada fonte oficial mapeada, o módulo `traffic/oficiais.py` traduz os campos cadastrais específicos daquele órgão para as colunas padronizadas de identificação:

| Campo padronizado | Tipo | DNIT (`dnit_snv`) | DER-SP (`der_sp_rodovias`) |
|---|---|---|---|
| `rodovia` | String | `Codigo_BR` | `Rodovia` |
| `codigo_trecho` | String | `Codigo_SNV` | `Subtrecho` |
| `km_ini` | Real | `Quilometragem_Inicio` | `KmInicial` |
| `km_fim` | Real | `Quilometragem_Fim` | `KmFinal` |
| `administracao` | String | `Administracao` | `Administra` |

Fontes estaduais sem mapeamento cadastral cadastrado mantêm as colunas de identificação como nulas (`NULL`), aplicando normalmente as regras de tradução dos atributos de capacidade.

!!! warning "Atributos brutos não são incluídos na malha padronizada"
    Os atributos brutos específicos de cada fonte (que acumulavam dezenas de colunas esparsas e não padronizadas) **não vêm mais** na camada baixada. A rastreabilidade e a localização exata de qualquer segmento na base oficial do órgão são asseguradas pela combinação: **`fonte` + `codigo_trecho` + `km_ini` / `km_fim`**.

---

## 4. Camada de Capacidade HCM (Aba 4 — Pré-alocação)

Gerada ao executar o comando **Calcular capacidade** (*Compute capacity*) na aba Capacidade do painel de rodovias. Contém a malha viária processada e simplificada com as capacidades calculadas segundo os procedimentos do HCM 6ª Edição (Capítulos 12 e 15), antes de receber qualquer alocação de demanda.

* **Nome padrão da camada:** `capacidade_hcm`
* **Tipo de Geometria:** Linha (`LineString`)
* **Módulo responsável:** `traffic/outputs.py` (`flows_to_layer`)

Possui exatamente os mesmos campos descritos na seção abaixo (Alocação em Rodovias Reais), mas com os seguintes valores padrão de pré-alocação:

* `volume = 0.0`
* `vc = 0.0`
* `los = 'A'`
* `tempo_h = t0 / 60` (tempo em fluxo livre; `t0` está em minutos, `tempo_h` em horas)
* `atraso_h = 0.0`
* `metodo = 'capacidade'`

---

## 5. Camada de Alocação em Rodovias Reais (Aba 4 — AoN / MSA / FW)

Gerada após executar a alocação de demanda da matriz OD sobre a malha rodoviária real (SNV/DER) através do comando **Alocar** (*Assign*).

* **Nome padrão da camada:** `alocacao_aon` (para All-or-Nothing), `alocacao_msa` (para Equilíbrio MSA) ou `alocacao_fw` (para Equilíbrio Frank-Wolfe).
* **Tipo de Geometria:** Linha (`LineString`)
* **Módulo responsável:** `traffic/outputs.py` (`flows_to_layer`)

### Atributos Principais de Tráfego e Desempenho

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `arc_id` | Texto (`String`) | - | Identificador único do arco direcionado no grafo (ex.: `('link101', 'fw')` ou `('link101', 'bw')`). |
| `link_id` | Inteiro (`Integer64`) ou Texto (`String`) | - | Identificador do segmento/link original da malha rodoviária de entrada (ex.: código do trecho SNV/DER). É **Inteiro (`Integer64`)** quando o id de origem é numérico (o padrão, FID da feição) e Texto (`String`) quando o *Campo de id do link* tem valores não numéricos. |
| `sentido` | Texto (`String`) | - | Sentido de trafegabilidade do arco: `fw` (*forward* — idêntico à orientação da geometria) ou `bw` (*backward* — inverso à geometria). |
| `faixas` | Inteiro (`Int`) | faixas | Número de faixas de rolamento disponíveis por sentido no trecho. |
| `comp_m` | Decimal (`Double`) | m | Comprimento real do trecho viário em metros. |
| `vel_livre` | Decimal (`Double`) | km/h | Velocidade de fluxo livre (*Free-Flow Speed* - FFS) considerada no cálculo. |
| `capacidade` | Decimal (`Double`) | veíc/h | Capacidade teórica máxima por sentido calculada segundo as normas do HCM 6ª Edição. |
| `volume` | Decimal (`Double`) | veíc/h | Volume total de tráfego alocado sobre o arco após a resolução do modelo de alocação. |
| `vc` | Decimal (`Double`) | adimensional | Razão Volume/Capacidade do arco (`v/c = volume / capacidade`). |
| `los` | Texto (`String`) | - | Nível de Serviço (*Level of Service*) operacional do trecho, de `A` a `F`, derivado do indicador `v/c`. |
| `tempo_h` | Decimal (`Double`) | h | Tempo total de viagem no trecho sob o fluxo alocado, determinado pela função de desempenho BPR (`t = t0 * [1 + alfa * (v/c) ^ beta]`), calculada em minutos e gravada em horas (`tempo_h = t / 60`). |
| `atraso_h` | Decimal (`Double`) | h | Atraso por trecho provocado pelo congestionamento em relação ao tempo em fluxo livre (`tempo_h - t0 / 60`), nunca negativo (`max(0, …)`). |
| `metodo` | Texto (`String`) | - | Algoritmo de alocação empregado: `aon` (*All-or-Nothing*), `msa` (*Successive Averages Equilibrium*) ou `fw` (*Frank-Wolfe Equilibrium*). |
| `escopo` | Texto (`String`) | - | Classificação do escopo territorial: `rodoviario` (rodovia rural/interurbana com capacidade HCM) ou `urbano` (travessia urbana mantida na rede sem recálculo de capacidade). |

---

### Campos de Proveniência dos Parâmetros HCM (`src_*`)

Para atender ao princípio de transparência total dos dados (**Regra D7 — "Nada é assumido em silêncio"**), a camada de saída inclui 18 campos adicionais indicando a proveniência exata de cada parâmetro operacional e de capacidade utilizado no cálculo.

Os campos `src_*` podem assumir um dos quatro valores possíveis:

* **`oficial`**: O parâmetro foi lido diretamente de um atributo existente na camada de rodovias de entrada (via mapeamento de campo na UI, busca em candidatos padrão ou atributos oficiais traduzidos).
* **`complementar`**: O parâmetro foi obtido a partir de uma feição correspondente em uma **camada complementar** espacialmente casada por proximidade (Decisões D4 e D6).
* **`usuario`**: O parâmetro foi informado ou sobrescrito manualmente pelo usuário na interface do plugin (parâmetro fixado via *Fixar* ou valor digitado em *Valor onde não há dado*).
* **`padrao`**: O parâmetro não constava na camada de entrada nem no complemento, e o plugin aplicou o valor padrão por classe de rodovia ou do catálogo residual DNIT/HCM.

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
| `src_capacidade` | `capacidade` | Proveniência da capacidade por sentido informada (`oficial`, `complementar`, `usuario` ou `padrao`). |
| `src_tempo_livre` | `tempo_livre` | Proveniência do tempo de fluxo livre informado (`oficial`, `complementar`, `usuario` ou `padrao`). |
| `src_mao_unica` | `mao_unica` | Proveniência da indicação de sentido único / mão única (`oficial`, `complementar`, `usuario` ou `padrao`). |

---

## 6. Simbologia e Estilo Graduado por v/c

As camadas de saída de alocação em rodovias (`alocacao_aon`, `alocacao_msa` e `alocacao_fw`) são configuradas automaticamente com um renderizador de simbologia graduada nativo do QGIS (`QgsGraduatedSymbolRenderer`) aplicado sobre o campo **`vc`**.

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

---

## 7. Camada de Calibração com Contagens GEH (Aba 4 — calibracao_geh)

Gerada após executar o comando **Calibrar** (*Calibrate*) na aba Calibração do painel de rodovias, confrontando os fluxos alocados na malha rodoviária contra os dados de uma camada de postos de contagem observada (ex.: PNCT/DNIT).

* **Nome padrão da camada / tabela:** `calibracao_geh` (gravada no GeoPackage compartilhado de saída).
* **Tipo de Geometria:** Ponto (`Point`).
* **Módulos responsáveis:** `traffic/outputs.py` (`calibration_to_layer`), `traffic/counts.py` (`casar_postos`), `traffic/calibration.py` (`geh`, `faixa_geh`, `resumo`).

### Especificação dos Atributos da Camada

| Campo | Tipo | Unidade | Descrição |
|---|---|---|---|
| `posto` | Texto (`String`) | - | Identificador do posto de contagem (herdado do campo mapeado na interface ou FID da feição). |
| `contagem` | Decimal (`Double`) | veíc | Volume de tráfego contado em campo (ex.: VMDa). |
| `modelado` | Decimal (`Double`) | veíc | Volume modelado consolidado no trecho mais próximo (soma dos dois sentidos, se houver) multiplicado pelo fator de escala (`volume × fator`). |
| `fator` | Decimal (`Double`) | adimensional | Multiplicador de escala aplicado para equalizar as unidades do modelo e das contagens (ex.: 10,0 para converter pico em VMDa com $K = 0,10$). |
| `dif` | Decimal (`Double`) | veíc | Diferença absoluta com sinal entre o volume modelado e o contado ($M - C$). |
| `dif_pct` | Decimal (`Double`) | % | Diferença percentual em relação à contagem ($100 \times (M - C) / C$). Nulo quando a contagem é zero. |
| `geh` | Decimal (`Double`) | adimensional | Estatística GEH calculada para o posto ($GEH = \sqrt{2(M - C)^2 / (M + C)}$). Nulo caso o posto fique sem trecho viário associado. |
| `faixa` | Texto (`String`) | - | Faixa normativa de calibração do posto: `A` ($GEH < 5$), `B` ($5 \le GEH < 10$), `C` ($10 \le GEH < 12$), `D` ($GEH \ge 12$) ou `sem_link` (posto situado além da distância máxima de casamento). |
| `link_id` | Texto (`String`) | - | Identificador do trecho rodoviário mais próximo com o qual o posto foi casado. Nulo quando `faixa = 'sem_link'`. |
| `dist_m` | Decimal (`Double`) | m | Distância euclidiana em metros entre o posto de contagem e o trecho viário casado. Nulo quando `faixa = 'sem_link'`. |

---

### Simbologia e Estilo Categorizado por Faixa de GEH

A camada de pontos `calibracao_geh` é configurada automaticamente com um renderizador categorizado nativo do QGIS (`QgsCategorizedSymbolRenderer`) aplicado sobre o campo **`faixa`**, permitindo identificação visual imediata dos pontos aderentes e dos pontos com divergência severa:

| Categoria | Faixa GEH | Cor Hexadecimal | Símbolo | Significado |
|:---:|:---:|:---:|:---:|---|
| **A** | `GEH < 5` | `#2ca02c` | Círculo verde (3,0 mm) | **Excelente calibração**: aderência ótima entre modelo e contagem. |
| **B** | `5 <= GEH < 10` | `#ffff33` | Círculo amarelo (3,0 mm) | **Aderência aceitável**: dentro da tolerância para macrossimulação. |
| **C** | `10 <= GEH < 12` | `#ff7f00` | Círculo laranja (3,0 mm) | **Divergência moderada**: alerta para checagem de parâmetros locais. |
| **D** | `GEH >= 12` | `#d7191c` | Círculo vermelho (3,0 mm) | **Divergência acentuada**: ponto prioritário para calibração. |
| **sem_link** | Sem link | `#808080` | Círculo cinza (3,0 mm) | **Sem trecho associado**: posto além da distância máxima configurada. |
