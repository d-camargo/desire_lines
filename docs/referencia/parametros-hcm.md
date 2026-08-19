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

O módulo [`traffic/params.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/params.py) resolve o valor e a proveniência de cada parâmetro para cada segmento viário através da função `resolve()`, respeitando a seguinte ordem de precedência:

```
[ Sobrescrita do Usuário ]  ---> Se definido na UI  ---> valor = UI,       src = 'usuario'
           | (se ausente)
[ Atributo da Camada ]     ---> Se existe na feição ---> valor = Feição,   src = 'oficial'
           | (se ausente)
[ Valor Padrão (Default) ] ---> Fallback do catálogo ---> valor = Default,  src = 'padrao'
```

---

## 2. Tabela Completa de Parâmetros HCM

A tabela abaixo lista os 15 parâmetros gerenciados pelo plugin (definidos em [`traffic/params.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/params.py)), suas unidades, tipos, valores padrão e os campos oficiais buscados automaticamente nas camadas de entrada.

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
| `bpr_alpha` | Alfa da função BPR | - | Decimal (`float`) | `0.15` | `bpr_alpha`, `alpha_bpr` | Coeficiente `alfa` da equação de tempo de viagem `t = t0 * [1 + alfa * (v/c) ^ beta]`. |
| `bpr_beta` | Beta da função BPR | - | Decimal (`float`) | `4.0` | `bpr_beta`, `beta_bpr` | Expoente `beta` da equação de congestionamento BPR. |

---

## 3. Procedimento de Sobrescrita e Mapeamento

### 3.1 Leitura Automática de Campos da Camada (`oficial`)

Ao carregar uma camada viária (seja importada do plugin GISBR ou um arquivo GeoPackage/Shapefile próprio), o Desire Lines inspeciona o esquema de atributos de cada feição.

A busca por campos oficiais é feita de forma flexível:

* **Insensível a maiúsculas/minúsculas**: O campo `LARGURA_FAIXA` ou `Largura_Faixa` é reconhecido do mesmo modo que `largura_faixa`.
* **Busca na lista de candidatos**: O plugin percorre a lista `campos_candidatos` registrada para o parâmetro em [`traffic/params.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/params.py). O primeiro campo encontrado na feição que contenha um valor válido (não nulo / não vazio) é adotado com a proveniência `oficial`.

### 3.2 Sobrescrita Global na Interface (`usuario`)

Na **Aba 4 — Alocação em Rodovias**, o usuário tem a opção de definir valores globais na interface gráfica para qualquer um dos parâmetros HCM.

* Quando um valor é especificado no painel da interface, ele possui a maior prioridade e substitui tanto os valores padrão quanto os atributos existentes na camada vetorial.
* A proveniência gravada no campo `src_*` da camada resultante será marcada como **`usuario`**.
* Isso permite realizar **análises de sensibilidade** e simulações de cenários hipotéticos (ex.: avaliar o impacto de reduzir a velocidade de fluxo livre de toda a malha para 60 km/h ou alterar o percentual de pesados para 35%).

### 3.3 Valores Padrão Assumidos (`padrao`)

Se um parâmetro não estiver presente na tabela de atributos da camada e o usuário não tiver preenchido uma sobrescrita global na interface, o plugin aplica o valor padrão (*default*) recomendado pelas diretrizes do HCM e do DNIT para rodovias rurais brasileiras.

* A proveniência correspondente será marcada como **`padrao`**.
* O resumo das proveniências adotadas ao longo de toda a malha é exibido no log ao final da execução dos comandos **Calcular capacidade** (*Compute capacity*) e **Alocar** (*Assign*).
