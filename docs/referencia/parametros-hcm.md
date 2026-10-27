# Parâmetros HCM e Regra de Proveniência

Esta página apresenta a referência técnica completa de todos os parâmetros operacionais e geométricos utilizados no cálculo de capacidade viária pelo **HCM 6ª Edição** (Highway Capacity Manual) e na alocação de tráfego do plugin **Desire Lines**.

---

## 1. Regra de Proveniência dos Parâmetros (Decisão D7)

Para garantir transparência e auditabilidade técnica em estudos de planejamento de transportes, o plugin adota estritamente a **Regra D7 — "Nada é assumido em silêncio"**.

Nenhum parâmetro de capacidade é aplicado a uma rodovia sem que sua origem seja explicitamente declarada. Para cada parâmetro `X` utilizado, a camada de saída registra um campo correspondente `src_X` com o valor de proveniência indicando uma de três origens possíveis:

1. **`usuario`**: O valor foi informado ou sobrescrito manualmente pelo usuário na interface do plugin.
2. **`oficial`**: O valor foi lido diretamente de um atributo existente na camada de rodovias (ex.: dados oficiais do SNV/DNIT ou DER obtidos via GISBR).
3. **`padrao`**: O parâmetro não constava na tabela de atributos da camada e não foi sobrescrito na interface; o plugin aplicou o valor padrão documentado.

### Hierarquia de Resolução

O módulo [`traffic/params.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/params.py) resolve o valor e a proveniência de cada parâmetro para cada segmento viário através da função `resolve()`, respeitando a seguinte ordem de precedência rigorosa (Decisão D2):

```
[ Sobrescrita do Usuário ]    ---> Se definido valor global na UI  ---> valor = UI,           src = 'usuario'
            | (se ausente)
[ Campo Mapeado na UI ]       ---> Se campo selecionado na feição   ---> valor = Campo Mapeado, src = 'oficial'
            | (se ausente/nulo)
[ Atributo Candidato ]        ---> Se existe campo candidato       ---> valor = Feição,        src = 'oficial'
            | (se ausente/nulo)
[ Valor Padrão (Default) ]    ---> Fallback do catálogo            ---> valor = Default,       src = 'padrao'
```

---

## 2. Tabela Completa de Parâmetros Operacionais e HCM

A tabela abaixo lista os 18 parâmetros gerenciados pelo plugin (definidos em [`traffic/params.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/params.py)), suas unidades, tipos, valores padrão e os campos oficiais buscados automaticamente nas camadas de entrada.

| Identificador (`id`) | Rótulo / Parâmetro | Unidade | Tipo | Valor Padrão | Campos Candidatos na Camada (Fonte Oficial) | Descrição / Valores Aceitos |
|---|---|---|---|---|---|---|
| `tipo_segmento` | Tipo de segmento | - | Texto (`str`) | `'2_faixas'` | `tipo_pista`, `pista`, `tipo_seg`, `tp_pista`, `ds_pista`, `tipo_segmento` | Classificação funcional do trecho: `2_faixas` (pista simples - Cap. 15), `multipista` (pista dupla/multilane - Cap. 12) ou `freeway` (autoestrada com acesso controlado - Cap. 12). |
| `lanes` | Número de faixas por sentido | faixas | Inteiro (`int`) | `1` | `faixas`, `num_faixas`, `faixas_sentido`, `nr_faixas`, `n_faixas`, `lanes` | Quantidade de faixas de rolamento disponíveis no sentido de tráfego analisado. |
| `pavimentado` | Pavimentado | - | Booleano (`bool`) | `True` | `pavimentado`, `superficie`, `tp_superficie`, `ds_superficie`, `st_pavimentado` | Indicador de pavimento. Trechos não pavimentados (`False`) recebem penalização na capacidade. |
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

## 3. Procedimento de Sobrescrita e Mapeamento

### 3.1 Mapeamento Direto por Campo na Interface (Decisão D2)

No painel **Alocação em rodovias**, na aba **Parâmetros HCM**, cada parâmetro dispõe de um *combobox* (*field:*) que permite selecionar diretamente qualquer coluna da camada viária.

* **Precedência do mapeamento (D2)**: Quando o usuário seleciona uma coluna no *combobox* de um parâmetro, esse nome de campo é enviado no dicionário `field_map = {param_id: nome_do_campo}` para o método `params.resolve()`.
* **Identificação oficial**: Qualquer valor lido com sucesso a partir da coluna mapeada é registrado com proveniência **`oficial`**, mesmo que o nome do campo na sua base seja completamente diferente dos candidatos pré-cadastrados (por exemplo, uma coluna chamada `cap_veic_hora` ou `t_zero`).
* **Fallback gracioso**: Se o campo mapeado contiver valor nulo, vazio ou inválido em determinada feição, o resolvedor busca a lista de candidatos padrão e, se nada for encontrado, aplica o valor de fábrica (`padrao`).

### 3.2 Leitura Automática por Candidatos (`oficial`)

Se nenhum campo for selecionado no combo *field:* da interface, o plugin inspeciona automaticamente o esquema da camada em busca dos nomes listados em `campos_candidatos` (tabela acima). A busca é insensível a maiúsculas/minúsculas (`CAPACITY`, `Capacity` e `capacity` são tratados identicamente). O primeiro candidato com dado válido define o parâmetro como `oficial`.

### 3.3 Sobrescrita Global na Interface (`usuario`)

O usuário pode digitar ou ajustar um valor global no controle de edição de qualquer parâmetro na interface.

* Valores globais digitados na interface possuem a maior prioridade: eles prevalecem sobre campos mapeados e candidatos existentes na feição.
* A proveniência gravada no campo `src_*` da camada resultante será marcada como **`usuario`**.
* Para os parâmetros com sentinela (`capacidade` e `tempo_livre`), o valor padrão `0.0` sinaliza que não há sobrescrita global ativa, permitindo a leitura da camada ou o cálculo automático.

### 3.4 Valores Padrão Assumidos (`padrao`)

Se um parâmetro não possuir sobrescrita do usuário e não for encontrado nem pelo mapeamento de campo nem pelos nomes candidatos, o plugin adota o valor de fábrica do catálogo `PARAMS`.

* A proveniência correspondente será marcada como **`padrao`**.
* Ao término da execução de **Calcular capacidade** ou **Alocar**, a barra de mensagens exibe o resumo de quantos pares (arco, parâmetro) vieram de cada fonte (`oficial`, `usuario`, `padrao`), assegurando total rastreabilidade (Regra D7).
