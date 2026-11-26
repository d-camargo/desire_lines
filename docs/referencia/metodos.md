# Métodos de Alocação e Escopo Operacional

Esta página detalha os métodos de alocação de tráfego disponíveis no **Desire Lines**, as diferenças conceituais entre as abordagens de rede sintética e rede real, a classificação aproximada de Nível de Serviço (LOS), as limitações de escopo em áreas urbanas, o envelope de desempenho do motor de alocação e o procedimento de calibração da macrossimulação com contagens pelo GEH.

---

## 1. Métodos de Alocação de Tráfego

O plugin disponibiliza três métodos principais de alocação de tráfego sobre redes viárias (definidos no módulo [`traffic/assignment.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/assignment.py)): **All-or-Nothing (AoN)**, **Equilíbrio por Médias Sucessivas (MSA + BPR)** e **Equilíbrio de Frank-Wolfe (FW + BPR)** (método padrão recomendado).

### 1.1 All-or-Nothing (AoN / Tudo-ou-Nada)

O método **All-or-Nothing (AoN)** aloca 100% da demanda de cada par Origem/Destino (OD) sobre o caminho mínimo de tempo em fluxo livre (`t0`), calculado via algoritmo de Dijkstra.

* **Mecanismo**: Passada única (1 iteração). Não considera a degradação de velocidade ou o aumento de tempo decorrentes do congestionamento.
* **Custo Computacional**: **Baixo** (uma única passada de Dijkstra por origem; os métodos de equilíbrio repetem essa passada a cada iteração — 100 no padrão do painel).
* **Interpretação da razão `v/c`**: Como os tempos de viagem não são atualizados no AoN, a capacidade calculada serve apenas para avaliação posterior. Se a razão volume/capacidade resultar maior que 1.0 (`v/c > 1`), **isso representa um diagnóstico direto de sobrecarga/déficit de capacidade física** no segmento viário, e **não** um estado de equilíbrio do sistema.

#### Quando usar o AoN:
* **Diagnóstico rápido de demanda potencial**: Para identificar corredores principais de desejo de viagem antes de aplicar restrições de capacidade.
* **Malhas com pouca concorrência de rotas**: Quando a topologia da rede viária oferece poucas ou nenhuma rota alternativa relevante entre as origens e destinos.
* **Demanda muito abaixo da capacidade**: Em redes rurais com baixo volume de tráfego, onde o congestionamento é insignificante e `v/c` fica bem abaixo de 1.
* **Linha de base (Baseline)**: Como cenário de referência para comparar contra o equilíbrio saturado do FW ou MSA.

---

### 1.2 Equilíbrio MSA + BPR (Method of Successive Averages)

O método de **Equilíbrio MSA** distribui iterativamente o tráfego considerando o efeito do congestionamento sobre os tempos de viagem, utilizando a equação de impedância do *Bureau of Public Roads* (BPR).

* **Mecanismo Iterativo**: A cada iteração `k` (`k` = 1, 2, ..., N):
    1. Os tempos de viagem `t_a` de cada arco `a` são recalculados pela curva BPR:
       `t_a = t0_a * [1 + alfa * (v_a / C_a) ^ beta]`
       em que `t0_a` é o tempo em fluxo livre, `v_a` é o volume corrente, `C_a` é a capacidade por sentido, e `alfa` e `beta` são os parâmetros BPR (por link ou globais, padrão: `alfa = 0,15`, `beta = 4,0`).
    2. Realiza-se um carregamento AoN completo sobre os novos tempos `t_a`, gerando volumes auxiliares `y_a^(k)`.
    3. Atualiza-se o fluxo acumulado combinando o resultado anterior com o auxiliar via média sucessiva com passo rígido $1/k$:
       `v_a^(k) = v_a^(k-1) + (1 / k) * (y_a^(k) - v_a^(k-1))`
* **Convergência**: O progresso da alocação é monitorado pelo **gap relativo de iteração**:
  $$\text{gap} = \frac{|\sum_a t_a v_a - \sum_a t_a y_a|}{\sum_a t_a v_a}$$
* **Custo Computacional**: **Moderado**, mas com convergência assintótica lenta devido ao passo fixo $1/k$, necessitando de centenas a milhares de iterações para gaps inferiores a 0,001.

---

### 1.3 Equilíbrio Frank-Wolfe + BPR (Algoritmo Padrão)

O método de **Frank-Wolfe (FW)** é o algoritmo clássico e consagrado para a resolução do problema de Equilíbrio do Usuário de Wardrop sob a formulação matemática de Beckmann. É o **método padrão** do Desire Lines para alocação com equilíbrio.

* **Mecanismo Iterativo**:
    1. **Inicialização**: Executa carregamento AoN inicial nos tempos de fluxo livre `t0`, definindo a base $v^{(1)}$.
    2. A cada iteração `k` (`k` = 2, ..., N):
        - Recalcula os tempos BPR correntes $t_a(v_a)$.
        - Executa carregamento AoN auxiliar com $t_a$, obtendo a direção de descida $y_a$.
        - Avalia o **gap relativo**. Se $0 \le \text{gap} \le \text{gap\_tol}$, interrompe por convergência antecipada.
        - **Busca linear ótima**: Determina o tamanho de passo $\lambda \in [0, 1]$ que minimiza a função objetivo de Beckmann ao longo da direção $(y - v)$, resolvendo por **bisseção** (30 avaliações) a derivada:
          $$\frac{d}{d\lambda} \sum_a \int_0^{v_a + \lambda(y_a - v_a)} t_a(w)\,dw = \sum_a t_a(v_a + \lambda(y_a - v_a)) \cdot (y_a - v_a) = 0$$
        - Atualiza os volumes pelo passo ótimo:
          $$v_a^{(k)} = v_a^{(k-1)} + \lambda \cdot (y_a - v_a^{(k-1)})$$
* **Parâmetros de Convergência Padrão**:
    - **Iterações máximas**: **100** (configurável até 5000 no painel).
    - **Tolerância do gap relativo**: **0,001** (0.001).
* **Custo Computacional**: **Excelente**. Cada iteração exige a mesma passada Dijkstra do MSA, mas o cálculo de $\lambda$ ótimo acelera a aproximação ao equilíbrio: em Sioux Falls, o mesmo gap relativo é atingido com cerca de 6 a 7× menos iterações (FW 50 it: gap 0,0031; o MSA só chega a esse gap na iteração 297, e o gap do FW 100 it, 0,0014, não é alcançado pelo MSA em 300 iterações; e gap < 0,001 na iteração 132 do FW contra 915 do MSA).

---

### 1.4 Quando usar Frank-Wolfe × MSA

| Critério | Frank-Wolfe + BPR (Recomendado) | MSA + BPR |
|---|---|---|
| **Velocidade de convergência** | **Rápida**: erro médio < 0,5% em 100 iterações; em Sioux Falls, gap < 0,001 a partir da iteração 132 | **Lenta**: com passo $1/k$, em Sioux Falls o gap só fica abaixo de 0,001 na iteração 915 |
| **Passo de atualização** | Ótimo ($\lambda$ via busca linear na função de Beckmann) | Pré-determinado ($1/k$) |
| **Recomendação de uso** | **Primeira escolha** para qualquer estudo de planejamento, modelagem de tráfego e projetos reais | Uso acadêmico/didático, comparações históricas ou baseline de métodos sem busca linear |

---

## 2. Comparativo de Métodos no Desire Lines

| Característica | AoN Sintético (Delaunay — Aba 3) | AoN Rodoviário (Painel Rodovias) | MSA + BPR (Painel Rodovias) | Frank-Wolfe + BPR (Painel Rodovias) |
|---|---|---|---|---|
| **Tipo de Rede** | **Sintética** (Triangulação de Delaunay entre centroides) | **Real** (Malha rodoviária do SNV/DER via GISBR) | **Real** (Malha rodoviária do SNV/DER via GISBR) | **Real** (Malha rodoviária do SNV/DER via GISBR) |
| **Passadas / Iterações** | Passada única (1-shot) | Passada única (1-shot) | Iterativo (passo 1/k, padrão 100 it) | Iterativo (passo ótimo λ, padrão 100 it) |
| **Considera Capacidade?** | Não (rede abstrata sem atributos físicos) | Sim (calcula HCM, mas não realimenta tempo) | Sim (calcula HCM e realimenta tempos via BPR) | Sim (calcula HCM e realimenta tempos via BPR) |
| **Redistribuição de Rotas?** | Não | Não | Sim (redistribui tráfego com passo 1/k) | Sim (redistribui tráfego com passo ótimo) |
| **Interpretação do `v/c > 1`** | N/A | Diagnóstico de sobrecarga local | Tendência ao equilíbrio | Tendência ao equilíbrio rigoroso |
| **Desempenho / Convergência** | Instantâneo | Uma passada (equilíbrio: uma por iteração) | Moderado (convergência assintótica lenta) | Rápido e preciso (convergência acelerada) |

---

## 3. Classificação de Nível de Serviço (LOS) Aproximado

O **Nível de Serviço (LOS — *Level of Service*)** do HCM varia formalmente de **A** (melhor condição operacional) a **F** (colapso/congestionamento severo).

### Aproximação por Faixas de `v/c` (Decisão D3)

No HCM 6ª Edição, a determinação rigorosa do LOS exige densidade de tráfego (veq/km/faixa) ou porcentagem do tempo gasto em fila (*PTSF*), parâmetros que necessitam de contagens contínuas e medições de campo indisponíveis no cadastro nacional do SNV.

Em cumprimento à **Decisão D3**, o Desire Lines reporta o LOS baseado estritamente em **faixas da razão Volume/Capacidade (`v/c`)**, conforme a tabela abaixo:

| Nível de Serviço (LOS) | Intervalo de `v/c` | Condição Operacional Identificada |
|:---:|:---:|---|
| **A** | `v/c <= 0,35` | **Fluxo Livre**: Veículos trafegam sem restrições de velocidade; manobras são completamente livres. |
| **B** | `0,35 < v/c <= 0,55` | **Fluxo Estável**: Pequenas restrições de velocidade e manobrabilidade. |
| **C** | `0,55 < v/c <= 0,75` | **Fluxo Estável Controlado**: Velocidade afetada pelo volume de tráfego; retenções pontuais. |
| **D** | `0,75 < v/c <= 0,90` | **Próximo à Saturação**: Restrições severas de manobra; pequenas flutuações de demanda causam filas. |
| **E** | `0,90 < v/c <= 1,00` | **Capacidade Máxima**: Operação no limite de capacidade da via; fluxo instável. |
| **F** | `v/c > 1,00` | **Sobrecarga / Colapso**: Demanda excede a capacidade; formação de gargalos e filas extensas. |

!!! warning "Nota de aproximação"
    O LOS calculado por faixas de `v/c` é um indicador de diagnóstico visual rápido para destacar gargalos na malha rodoviária. Ele não substitui os procedimentos microscópicos de campo do HCM quando há dados detalhados disponíveis.

---

## 4. Escopo Operacional e Sinalização Urbana

### 4.1 Escopo Exclusivamente Rodoviário (Decisão D2)

O módulo de cálculo de capacidade do Desire Lines foi desenvolvido especificamente para **rodovias rurais e interurbanas**:

* **Pistas Simples / Duas Faixas**: Procedimento completo segundo o **HCM 6ª Edição, Capítulo 15**.
* **Pistas Duplas / Multilane e Freeways**: Procedimento completo segundo o **HCM 6ª Edição, Capítulo 12**.

**Fora de Escopo**: Interseções semaforizadas, cruzamentos urbanos, rotatórias, rampas de acesso e trechos de *weaving* (Capítulos 16 a 19 do HCM). A base oficial do SNV/DNIT não fornece parâmetros operacionais urbanos (como tempos de ciclo de semáforo, faseamento e distâncias entre cruzamentos), inviabilizando a aplicação rigorosa do HCM urbano sem invenção de dados.

### 4.2 Aviso e Marcação de Travessias Urbanas (Decisão D11)

Em trechos de travessia urbana integrados à malha rodoviária, a capacidade real da via é governada por controles semafóricos e cruzamentos, e não pelas características geométricas do segmento. Aplicar a fórmula rodoviária nesses trechos **superestima a capacidade real da via urbana**.

Para tratar essa limitação com total transparência:

1. **Conectividade Mantida**: O plugin **não remove** as travessias urbanas do grafo, garantindo a integridade dos caminhos mínimos de transporte.
2. **Marcação de Escopo**: Cada arco urbano processado é etiquetado com o atributo `escopo = 'urbano'` (enquanto os demais recebem `escopo = 'rodoviario'`).
3. **Alerta no Log**: Ao finalizar o cálculo de capacidade e a alocação, o log do plugin reporta explicitamente a quantidade de trechos urbanos processados com a aproximação rodoviária.
4. **Filtragem pelo Analista**: O analista pode utilizar o campo `escopo` para isolar ou filtrar trechos urbanos em relatórios e pós-processamentos cartográficos.

---

## 5. Envelope de Desempenho (Decisão D4)

Para contornar as limitações de desempenho do motor de redes C++ nativo do QGIS — que não permite atualizar custos de arcos *in-place* sem recriar todo o grafo a cada iteração de equilíbrio —, o Desire Lines utiliza um **motor de grafo próprio em Python puro** ([`traffic/graph.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/graph.py)).

### Capacidades e Limites de Processamento

* **Tamanho de Malha Recomendado**: Confortável para redes contendo até **~50.000 arcos** direcionados.
* **Iterações de Equilíbrio**: Excelente desempenho com o padrão de **100 iterações** de Frank-Wolfe ou MSA em áreas de estudo estaduais e regionais.
* **Dijkstra por Origem**: A busca de menor caminho é executada **uma vez por origem única** (e não por par OD individual), reduzindo drasticamente o tempo total de processamento.
* **Ganho do AoN**: Como a alocação All-or-Nothing realiza apenas uma passada de Dijkstra, sua execução é proporcionalmente mais rápida que os métodos de equilíbrio, que repetem essa passada a cada iteração (até **100** no padrão), permitindo processar malhas maiores em poucos segundos.

---

## 6. Validação com Sioux Falls

A precisão do motor de alocação de tráfego do Desire Lines foi validada utilizando o clássico benchmark de **Sioux Falls** ([bstabler/TransportationNetworks](https://github.com/bstabler/TransportationNetworks)), composto por 24 zonas, 76 links direcionados, 528 pares OD com demanda positiva (total de 360.600 viagens) e Tempo Total de Viagem no Sistema (TSTT — *Total System Travel Time*) de referência de **7.480.225** (sob função BPR com $\alpha = 0,15$ e $\beta = 4,0$).

O erro é medido por link em relação aos fluxos de equilíbrio de referência (`SiouxFalls_flow.tntp`):
$$\text{erro} = \frac{|v - v_{\text{ref}}|}{v_{\text{ref}}}$$

| Cenário | erro máx. | erro médio | TSTT |
|---|---|---|---|
| Entradas TNTP (cap/fft, 1 sentido), MSA 10 it / gap 0,01 (**padrão anterior do painel**) | 69,6 % | 13,7 % | 9 342 350 |
| idem, MSA 50 it | 16,9 % | 3,0 % | 7 770 932 |
| idem, MSA 500 it (gap 1,8e-3) | 1,7 % | 0,30 % | 7 507 334 |
| idem, MSA 2000 it (gap 4,7e-4) | 0,4 % | 0,07 % | 7 487 138 |
| idem, **Frank-Wolfe** 50 / 100 / 300 it | 5,3 / 2,3 / 0,7 % | 0,96 / 0,46 / 0,14 % | 7 484 340 / 7 476 227 / 7 478 543 |
| Cap/fft TNTP, mas **cada feição vira mão dupla** | 73,6 % | 19,4 % | 3 743 234 |
| **O que o plugin fazia antes** (cap HCM, t0 = geometria ÷ 80 km/h, mão dupla, 10 it) | 177 % | 64,9 % | 714 504 749 |

### Conclusões da Validação

1. **Convergência Superior do Frank-Wolfe**: Com **Frank-Wolfe a 300 iterações**, o motor alcança erro médio de apenas **0,14%** (máximo de 0,7%) e TSTT de 7.478.543, praticamente indistinguível da referência analítica (< 0,03% de desvio). O novo padrão de **100 iterações e gap 0,001** oferece um equilíbrio excelente entre velocidade e precisão (erro médio de 0,46%).
2. **Desempenho do MSA**: O MSA confirma convergência assintótica correta (erro médio de 0,07% em 2000 iterações), mas requer cerca de 6 a 7× mais iterações que o Frank-Wolfe para o mesmo gap relativo (medido em Sioux Falls: FW 50 it ≈ MSA 297 it; gap < 0,001 em 132 it no FW e 915 it no MSA).
3. **Importância dos Parâmetros Informados e Mão Única**: As causas principais de divergência em redes calibradas não estão nos algoritmos de caminho mínimo, mas sim em impor mão dupla onde a via é de mão única (`mao_unica`) ou calcular capacidade/tempo livre por fórmulas genéricas quando os valores reais já são conhecidos (`capacidade` e `tempo_livre`).

---

## 7. Calibração da Macrossimulação pelo GEH

A etapa de **calibração da macrossimulação** consiste em confrontar os volumes de tráfego alocados na rede viária contra contagens empíricas observadas em postos de monitoramento (como as séries históricas e contagens contínuas do PNCT/DNIT).

### 7.1 Estatística GEH

A estatística **GEH** (desenvolvida por Geoffrey E. Havers na década de 1970) é uma métrica de concordância empírica formulada especificamente para engenharia de tráfego. Diferente de erros percentuais simples — que distorcem a avaliação em trechos com baixo volume (pequenas diferenças absolutas geram erros percentuais enormes) e são complacentes em trechos saturados (grandes discrepâncias absolutas geram erros percentuais baixos) —, o GEH equilibra grandezas relativas e absolutas:

$$GEH_i = \sqrt{ \frac{2 (M_i - C_i)^2}{M_i + C_i} }$$

em que:

* $M_i$ é o volume modelado no posto $i$ (após a aplicação do *Fator modelo → contagem*, $M = \text{volume alocado} \times \text{fator}$);
* $C_i$ é o volume contado/observado em campo no posto $i$.

Quando a soma $M_i + C_i = 0$, adota-se formalmente $GEH = 0,0$.

### 7.2 Faixas Normativas de Classificação

O valor do GEH de cada posto casado é classificado em quatro faixas operacionais (com limites fechados à esquerda):

| Faixa GEH | Intervalo | Interpretação Operacional |
|:---:|:---:|---|
| **Faixa A** | $GEH < 5$ | **Excelente aderência**: os volumes modelado e observado são praticamente coincidentes. |
| **Faixa B** | $5 \le GEH < 10$ | **Aderência aceitável**: discrepância tolerável para modelos de macrossimulação e planejamento regional. |
| **Faixa C** | $10 \le GEH < 12$ | **Alerta de divergência moderada**: requer atenção; indica possíveis imprecisões de zoneamento ou capacidade. |
| **Faixa D** | $GEH \ge 12$ | **Divergência severa**: inconsistência significativa; aponta distorções graves na rede, na matriz ou na contagem. |

### 7.3 Critério DNIT ("% mínimo desejado")

As notas técnicas do Plano Nacional de Contagem de Tráfego do DNIT (PNCT 2018, 2021, 2025 e 2026), em consonância com diretrizes internacionais consagradas (como o *Design Manual for Roads and Bridges* — DMRB, Volume 12, do Reino Unido), definem o **critério de calibração aceitável da macrossimulação** com base no percentual mínimo desejado de postos válidos:

* **No mínimo 60%** dos postos de contagem situados na **Faixa A** ($GEH < 5$);
* **No mínimo 95%** dos postos de contagem situados no acumulado das **Faixas A + B** ($GEH < 10$).

O plugin avalia automaticamente o conjunto de postos casados e reporta na barra de mensagens se a modelagem **atende** ou **não atende** ao critério oficial do DNIT.

### 7.4 Percentual do Erro Médio Quadrático (%RMSE)

Além das faixas de GEH, o plugin calcula o **%RMSE** (*Percent Root Mean Square Error*), que expressa o desvio padrão dos erros em relação à média dos volumes contados:

$$\%RMSE = 100 \times \frac{\sqrt{\frac{1}{n} \sum_{i=1}^n (M_i - C_i)^2}}{\frac{1}{n} \sum_{i=1}^n C_i}$$

em que $n$ é o total de postos com trecho viário associado dentro da distância máxima de casamento. Postos isolados (`faixa = 'sem_link'`) não entram no cômputo de $n$.

### 7.5 O que NÃO é feito (Limitações de Escopo)

Para evitar ambiguidades metodológicas, destacam-se duas premissas fundamentais do escopo:

1. **Sem ajuste matemático de matriz (ODME)**: O plugin realiza o diagnóstico e a verificação da aderência da alocação da matriz existente em relação às contagens de campo, mas **não executa estimação/ajuste reverso de matriz OD por contagens** (*Origin-Destination Matrix Estimation* — ODME). A alteração matemática de células da matriz para forçar convergência artificial deve ser realizada em ferramentas especializadas caso desejado pelo analista.
2. **O GEH mede aderência, não é teste estatístico formal**: O GEH é uma métrica heurística e empírica consagrada na engenharia de tráfego. Ele **não constitui um teste estatístico de hipóteses** (como qui-quadrado, ANOVA ou teste $t$ de Student) e não estabelece distribuições amostrais teóricas ou níveis de significância probabilística ($p$-valor).
