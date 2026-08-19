# Métodos de Alocação e Escopo Operacional

Esta página detalha os métodos de alocação de tráfego disponíveis no **Desire Lines**, as diferenças conceituais entre as abordagens de rede sintética e rede real, a classificação aproximada de Nível de Serviço (LOS), as limitações de escopo em áreas urbanas e o envelope de desempenho do motor de alocação.

---

## 1. Métodos de Alocação de Tráfego

O plugin disponibiliza dois métodos principais de alocação de tráfego sobre redes viárias (definidos no módulo [`traffic/assignment.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/assignment.py)): **All-or-Nothing (AoN)** e **Equilíbrio por Médias Sucessivas (MSA + BPR)**.

### 1.1 All-or-Nothing (AoN / Tudo-ou-Nada)

O método **All-or-Nothing (AoN)** aloca 100% da demanda de cada par Origem/Destino (OD) sobre o caminho mínimo de tempo em fluxo livre ($t_0$), calculado via algoritmo de Dijkstra.

* **Mecanismo**: Passada única (1 iteração). Não considera a degradação de velocidade ou o aumento de tempo decorrentes do congestionamento.
* **Custo Computacional**: **Baixo** (~10× mais rápido que uma alocação MSA típica de 10 iterações).
* **Interpretação da razão $v/c$**: Como os tempos de viagem não são atualizados no AoN, a capacidade calculada serve apenas para avaliação posterior. Se a razão volume/capacidade resultar maior que 1.0 ($v/c > 1$), **isso representa um diagnóstico direto de sobrecarga/déficit de capacidade física** no segmento viário, e **não** um estado de equilíbrio do sistema.

#### Quando usar o AoN:
* **Diagnóstico rápido de demanda potencial**: Para identificar corredores principais de desejo de viagem antes de aplicar restrições de capacidade.
* **Malhas com pouca concorrência de rotas**: Quando a topologia da rede viária oferece poucas ou nenhuma rota alternativa relevante entre as origens e destinos.
* **Demanda muito abaixo da capacidade**: Em redes rurais com baixo volume de tráfego, onde o congestionamento é insignificante e $v/c \ll 1$.
* **Linha de base (Baseline)**: Como cenário de referência para comparar contra o equilíbrio saturado do MSA.

---

### 1.2 Equilíbrio MSA + BPR (Method of Successive Averages)

O método de **Equilíbrio MSA** distribui iterativamente o tráfego considerando o efeito do congestionamento sobre os tempos de viagem, utilizando a equação de impedância do *Bureau of Public Roads* (BPR).

* **Mecanismo Iterativo**: A cada iteração $k$ ($k = 1, 2, \dots, N$):
    1. Os tempos de viagem $t_a$ de cada arco $a$ são recalculados pela curva BPR:
       $$t_a = t_{0,a} \left[ 1 + \alpha \left( \frac{v_a}{C_a} \right)^\beta \right]$$
       em que $t_{0,a}$ é o tempo em fluxo livre, $v_a$ é o volume corrente, $C_a$ é a capacidade por sentido, e $\alpha=0,15, \beta=4,0$ são os parâmetros padrão BPR.
    2. Realiza-se um carregamento AoN completo sobre os novos tempos $t_a$, gerando volumes auxiliares $y_a^{(k)}$.
    3. Atualiza-se o fluxo acumulado combinando o resultado anterior com o auxiliar via média sucessiva:
       $$v_a^{(k)} = v_a^{(k-1)} + \frac{1}{k} \left( y_a^{(k)} - v_a^{(k-1)} \right)$$
* **Convergência**: O progresso da alocação é monitorado pelo **gap relativo de iteração**, registrando a estabilização dos fluxos entre passos sucessivos.
* **Custo Computacional**: **Moderado** (proporcional ao número máximo de iterações configurado, padrão: 10 iterações).

#### Quando usar o MSA + BPR:
* **Redes viárias com rotas concorrentes**: Quando existem caminhos alternativos que disputam a mesma demanda OD.
* **Trechos com demanda próxima ou superior à capacidade**: Em cenários onde a sobrecarga de vias principais força o desvio do tráfego para vias secundárias.
* **Simulação de gargalos**: Para mapear a redistribuição real do tráfego decorrente de restrições de capacidade viária.

---

## 2. Comparativo de Métodos no Desire Lines

| Característica | AoN Sintético (Delaunay — Aba 3) | AoN Rodoviário (Aba 4) | MSA + BPR (Aba 4) |
|---|---|---|---|
| **Tipo de Rede** | **Sintética** (Triangulação de Delaunay entre centroides) | **Real** (Malha rodoviária do SNV/DER via GISBR) | **Real** (Malha rodoviária do SNV/DER via GISBR) |
| **Passadas / Iterações** | Passada única (1-shot) | Passada única (1-shot) | Iterativo (padrão: 10 iterações) |
| **Considera Capacidade?** | Não (rede abstrata sem atributos físicos) | Sim (calcula HCM, mas não realimenta tempo) | Sim (calcula HCM e realimenta tempos via BPR) |
| **Redistribuição de Rotas?** | Não | Não | Sim (redistribui tráfego saturado) |
| **Interpretação do $v/c > 1$** | N/A | Diagnóstico de sobrecarga local | Tendência ao equilíbrio (redireciona para rotas livres) |
| **Desempenho relativo** | Instantâneo | ~10× mais rápido que MSA | Moderado |

---

## 3. Classificação de Nível de Serviço (LOS) Aproximado

O **Nível de Serviço (LOS — *Level of Service*)** do HCM varia formalmente de **A** (melhor condição operacional) a **F** (colapso/congestionamento severo).

### Aproximação por Faixas de $v/c$ (Decisão D3)

No HCM 6ª Edição, a determinação rigorosa do LOS exige densidade de tráfego (veq/km/faixa) ou porcentagem do tempo gasto em fila (*PTSF*), parâmetros que necessitam de contagens contínuas e medições de campo indisponíveis no cadastro nacional do SNV.

Em cumprimento à **Decisão D3**, o Desire Lines reporta o LOS baseado estritamente em **faixas da razão Volume/Capacidade ($v/c$)**, conforme a tabela abaixo:

| Nível de Serviço (LOS) | Intervalo de $v/c$ | Condição Operacional Identificada |
|:---:|:---:|---|
| **A** | $v/c \le 0,35$ | **Fluxo Livre**: Veículos trafegam sem restrições de velocidade; manobras são completamente livres. |
| **B** | $0,35 < v/c \le 0,55$ | **Fluxo Estável**: Pequenas restrições de velocidade e manobrabilidade. |
| **C** | $0,55 < v/c \le 0,75$ | **Fluxo Estável Controlado**: Velocidade afetada pelo volume de tráfego; retenções pontuais. |
| **D** | $0,75 < v/c \le 0,90$ | **Próximo à Saturação**: Restrições severas de manobra; pequenas flutuações de demanda causam filas. |
| **E** | $0,90 < v/c \le 1,00$ | **Capacidade Máxima**: Operação no limite de capacidade da via; fluxo instável. |
| **F** | $v/c > 1,00$ | **Sobrecarga / Colapso**: Demanda excede a capacidade; formação de gargalos e filas extensas. |

> [!WARNING]
> **Nota de Aproximação**: O LOS calculado por faixas de $v/c$ é um indicador de diagnóstico visual rápido para destacar gargalos na malha rodoviária. Ele não substitui os procedimentos microscópicos de campo do HCM quando há dados detalhados disponíveis.

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

Para contornar as limitações de desempenho do motor de redes C++ nativo do QGIS — que não permite atualizar custos de arcos *in-place* sem recriar todo o grafo a cada iteração do MSA —, o Desire Lines utiliza um **motor de grafo próprio em Python puro** ([`traffic/graph.py`](file:///home/diego/projects/desire-lines/desire_lines/traffic/graph.py)).

### Capacidades e Limites de Processamento

* **Tamanho de Malha Recomendado**: Confortável para redes contendo até **~50.000 arcos** direcionados.
* **Iterações MSA**: Excelente desempenho com o padrão de **10 iterações** em áreas de estudo estaduais e regionais.
* **Dijkstra por Origem**: A busca de menor caminho é executada **uma vez por origem única** (e não por par OD individual), reduzindo drasticamente o tempo total de processamento.
* **Ganho do AoN**: Como a alocação All-or-Nothing realiza apenas uma passada de Dijkstra, sua execução é aproximadamente **10× mais rápida** que o MSA, permitindo processar malhas maiores em poucos segundos.
