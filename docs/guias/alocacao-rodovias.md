# Alocação em rodovias

O painel **Alocação em rodovias** carrega a matriz OD sobre a **malha rodoviária
real** (SNV/DER), calcula a **capacidade de cada trecho pelo procedimento do
HCM 6ª edição** e devolve volume, relação volume/capacidade (`vc`) e nível de
serviço por arco. É o resultado que a rede sintética da aba
[AoN (Delaunay)](aon-delaunay.md) não consegue dar — lá não há capacidade.

Para abrir o painel, use o **botão único da barra com seta de menu** (o clique abre o diálogo principal; a seta, o menu com *Desire Lines* e *Alocação em rodovias* ["Highway Assignment"]) ou acesse o menu **Vetor ▸ Desire Lines ▸ Alocação em rodovias**.
O painel ancora no lado direito da janela do QGIS e pode permanecer aberto
enquanto você navega no mapa ou edita camadas.

Logo acima das abas, o campo **GeoPackage de saída** ("Output GeoPackage") define o
arquivo `.gpkg` compartilhado onde todas as camadas geradas são gravadas (por padrão
`~/output.gpkg`). Abaixo dele, o painel é dividido em quatro abas operacionais:
**Rede** ("Network"), **Capacidade** ("Capacity"), **Alocação** ("Assignment") e
**Calibração** ("Calibration").

!!! danger "Escopo: rodovias rurais/interurbanas"
    A capacidade vem do **HCM cap. 15** (pista simples, duas faixas) e do
    **cap. 12** (pista dupla / multifaixa / freeway). Travessias urbanas
    dentro da malha são **marcadas** com `escopo='urbano'` e contadas no aviso
    final, mas **não** são recalculadas por procedimento urbano — o
    procedimento urbano do HCM (caps. 16-19) exige dados de semáforo que a
    base oficial não traz. Leia esses arcos com reserva.

## Aba Rede

A aba **Rede** ("Network") define a malha viária de trabalho utilizada tanto para o
cálculo de capacidade quanto para a alocação de tráfego.

O grupo *Rede* ("Network") tem duas opções, mutuamente exclusivas:

| Opção | O que preencher | Quando usar |
|---|---|---|
| *Usar uma camada existente* ("Use an existing layer") | *Camada de rodovias* ("Highway layer") e, opcionalmente, *Campo de id do link (opcional)* ("Link id field (optional)") | Você já tem a malha carregada no projeto (arquivo local, recorte próprio) |
| *Baixar via GisBR (malha oficial SNV/DER)* ("Download via GisBR (official SNV/DER network)") | *Estado (UF)* ("State (UF)") (sigla de **2 letras**), *Área de download* ("Download area"), se regional, *Região* ("Region"), e botão *Baixar malha* ("Download network") | Quer a malha oficial baixada na hora; as execuções usam a camada baixada |

O *Campo de id do link (opcional)* é opcional: serve para o campo `link_id` da saída
apontar de volta para o identificador da sua base. Sem ele, o plugin gera um
id próprio.

!!! warning "O download depende do plugin GisBR"
    A opção de download só habilita se o plugin
    [GisBR](https://github.com/d-camargo/gisbr) estiver instalado — sem ele, o
    aviso no topo do painel fica visível e o plugin volta sozinho para *Usar uma
    camada existente*. O resto do painel **funciona normalmente** com camada
    própria; só o download é bloqueado.

O combo *Área de download* ("Download area") define a abrangência territorial da malha a ser baixada e recortada, com seis opções disponíveis:

1. **Extensão dos centroides (+ raio)** ("Centroid extent (+ radius)"): a área de estudo é a envoltória retangular dos centroides carregados acrescida do raio configurado em *Conector máximo (m)* ("Max connector (m)"). É a opção padrão e recomendada para focar o grafo apenas nos arredores da demanda.
2. **UF inteira** ("Whole state"): faz o download da malha completa do estado informado em *Estado (UF)* ("State (UF)").
3. **Região Metropolitana** ("Metropolitan area"): recorta a malha pela extensão da Região Metropolitana selecionada.
4. **Microrregião** ("Micro-region"): recorta a malha pela extensão da microrregião geográfica (IBGE) selecionada.
5. **Mesorregião** ("Meso-region"): recorta a malha pela extensão da mesorregião geográfica (IBGE) selecionada.
6. **Macrorregião de saúde** ("Health macro-region"): recorta a malha pela extensão da macrorregião de saúde selecionada.

As quatro opções regionais (*Região Metropolitana*, *Microrregião*, *Mesorregião* e *Macrorregião de saúde*) exigem o preenchimento da *UF* (2 letras), que faz o plugin carregar dinamicamente as regiões disponíveis daquele estado, e a escolha obrigatória de um item no combo *Região* ("Region"). Enquanto uma região válida não for selecionada, o botão de download permanece desabilitado.

O download é acionado pelo botão **Baixar malha** ("Download network"). Ao informar o *Estado (UF)*, o plugin preenche a lista **Fontes** ("Sources") com todas as bases rodoviárias oficiais disponíveis para aquela UF no catálogo do GisBR — a malha federal do DNIT (SNV) e as bases estaduais cadastradas (DERs) —, todas marcadas por padrão. O usuário pode desmarcar qualquer fonte antes de iniciar o download. Caso o download de qualquer uma das fontes marcadas falhe (por exemplo, por indisponibilidade de servidor), o processo é **interrompido imediatamente** com mensagem de erro nomeando a fonte que falhou, evitando gravar malhas incompletas.

O download roda em **segundo plano**: o progresso e o cancelamento são acompanhados pelo **gerenciador de tarefas do QGIS** (canto inferior), e o QGIS continua perfeitamente usável durante todo o processo.

Quanto ao recorte da malha:

- No modo **UF inteira** e nos recortes regionais (*Região Metropolitana*, *Microrregião*, *Mesorregião* e *Macrorregião de saúde*), a malha é cortada pelo **limite oficial** (IBGE, via GisBR), com folga de 500 m na divisa.
- No modo **Extensão dos centroides (+ raio)**, o recorte segue o retângulo dos centroides acrescido da distância máxima (*Conector máximo (m)*).

Quando mais de uma fonte está marcada, o plugin realiza a **junção geométrica com precedência**:

- **Precedência DNIT → estaduais**: a malha federal do DNIT é a referência principal e entra integralmente; as malhas estaduais subsequentes contribuem apenas com os trechos que não duplicam vias já presentes.
- **Tratamento de sobreposição**: trechos estaduais sobrepostos à malha de referência ao longo de **≥ 100 m dentro de uma faixa de 20 m** de tolerância são aparados (subtraídos). Toques curtos em entroncamentos (< 100 m) são preservados para manter a integridade das conexões, e fragmentos residuais com menos de 50 m são descartados. Trechos planejados de qualquer fonte são eliminados previamente.
- **Costura topológica (30 m)**: pontas soltas a **até 30 m** de outra via são conectadas por *snap* na ponta mais próxima (nó-nó) ou projetadas ortogonalmente dividindo a via atingida em uma junção em "T". Cruzamentos em níveis diferentes (como viadutos e passagens em desnível) sem pontas soltas próximas **não** são conectados, preservando a ausência de conversão real.

Cada feição da malha resultante recebe os atributos de rastreabilidade **`fonte`** (identificador da base de origem, como `dnit_snv` ou `der_mg_rodovias`) e **`ajuste`** (vazio para inalterada, `'aparada'` para cortes de sobreposição, `'costurada'` para conexões de pontas, ou `'aparada+costurada'`). Os demais campos das fontes são unificados. A malha final é gravada no GeoPackage de saída como a camada **`malha_gisbr_<uf>`** (por exemplo, `malha_gisbr_mg`), carregada diretamente no projeto QGIS e selecionada automaticamente em *Usar uma camada existente*, pronta para o cálculo de capacidade e a alocação. A mensagem final na barra de mensagens separa os trechos **removidos por duplicidade**, **aparados** e **costurados** (com relatório detalhado por fonte no Registro de Mensagens).

Quando utilizada a opção *Usar uma camada existente*, a área de estudo também é recortada pela extensão dos centroides (com buffer de conector), limitando o tamanho da rede e acelerando a montagem do grafo. Se o recorte falhar, o plugin exibe um aviso e segue com a malha inteira.

!!! note "Reprojeção automática para CRS métrico"
    Camadas em CRS geográfico (graus) — tanto no download via GisBR quanto em camada existente — são reprojetadas sozinhas para um CRS métrico (UTM da região, ou SIRGAS 2000 / Brazil Albers se a área cobrir mais de uma zona). A camada de saída sai nesse CRS, e o aviso *Malha rodoviária reprojetada…* (*Highway network reprojected…*) aparece na barra de mensagens (*message bar*).

## Aba Capacidade

A aba **Capacidade** ("Capacity") reúne as configurações operacionais e geométricas para o cálculo de capacidade HCM e parâmetros da rede viária.

O grupo *Parâmetros HCM (padrão, ou sobrescrever globalmente / por campo)* ("HCM parameters (default, or override globally / by field)") traz a tabela de parâmetros para os 18 parâmetros operacionais do sistema (tipo de segmento, faixas, terreno, % de veículos pesados, FFS, PHF, largura de faixa e acostamento, ultrapassagem proibida, densidade de acessos, divisão direcional, alfa e beta do BPR, capacidade informada, tempo livre e mão única).

Cada linha da tabela é composta por quatro colunas:

| Coluna | Descrição |
|---|---|
| **Parâmetro** ("Parameter") | Nome do parâmetro operacional ou geométrico do HCM. |
| **Valor onde não há dado** ("Value where there is no data") | Valor utilizado caso a feição na malha e a camada complementar não tragam informação (etapa 6 da cascata). Se modificado pelo usuário em relação ao catálogo, é registrado como proveniência **`usuario`**. |
| **Fixar** ("Fix") | Caixa de seleção (`QCheckBox`) que, quando marcada (sem campo mapeado), força o valor digitado sobre toda a rede viária (etapa 1 da cascata). O valor prevalece sobre atributos da camada e complementos, sendo registrado com proveniência **`usuario`**. |
| **Campo da camada** ("Layer field") | *Combobox* que permite mapear diretamente qualquer coluna da camada viária ao parâmetro (etapa 2 da cascata). Valores lidos com sucesso recebem proveniência **`oficial`**. |

Quando você utiliza a opção *Baixar via GisBR (malha oficial SNV/DER)* na aba Rede, a malha viária baixada (`malha_gisbr_<uf>`) já chega padronizada no esquema de 21 colunas no vocabulário técnico do HCM (Decisões D2 e D3). Dessa forma, o plugin reconhece e lê automaticamente os dados oficiais diretamente da camada sem que você precise mapear nenhum campo manualmente.

### Grupo Dados complementares (opcional)

Localizado logo abaixo da tabela de parâmetros, o grupo **Dados complementares (opcional)** ("Complementary data (optional)") permite enriquecer a malha viária com dados de fontes secundárias (Decisões D4 e D6):

* **Camada complementar** ("Complementary layer"): *Combobox* que aceita qualquer camada vetorial adicional carregada no projeto QGIS (linhas como eixos do OSM ou `osm_links_rm<id>`, pontos como postos de contagem contendo % de veículos pesados, ou polígonos como áreas urbanizadas do IBGE). Deixe vazio caso deseje trabalhar apenas com os dados da rede viária.
* **Distância máxima** ("Max. distance"): Raio de busca em metros (padrão **30 m**). O plugin avalia o ponto médio geométrico de cada link rodoviário e busca a feição complementar mais próxima dentro do raio configurado (medido no CRS métrico da malha).

Os atributos da feição complementar encontrada passam por tradução automática (`oficiais.traduz`) e busca por candidatos padrão, e os parâmetros absorvidos recebem a proveniência **`complementar`** (etapa 5 da cascata).

### Parâmetros Especiais de Rede e a Sentinela `0`

Três parâmetros permitem incorporar diretamente atributos conhecidos de malhas já calibradas (como redes municipais ou benchmarks tipo Sioux Falls):

* **Capacidade por sentido (0 = HCM)** (`capacidade`): Capacidade por sentido em veíc/h. A sentinela **`0`** indica cálculo automático pelo procedimento do HCM 6ª edição (Cap. 15 pista simples ou Cap. 12 pista dupla/freeway). Qualquer valor **`> 0`** substitui a capacidade do HCM.
* **Tempo de fluxo livre (0 = comprimento ÷ FFS)** (`tempo_livre`): Tempo em fluxo livre em minutos. A sentinela **`0`** calcula o tempo com base no comprimento geométrico e na velocidade livre (`comprimento ÷ vel_livre`). Qualquer valor **`> 0`** substitui o tempo calculado.
* **Mão única (sentido da geometria)** (`mao_unica`): Booleano. Se verdadeiro (`True`, `1`, `'sim'`, `'yes'`), gera apenas o arco no sentido da geometria (`fw`), omitindo o reverso (`bw`). Se falso (`False`), gera os dois arcos direcionados (`fw` e `bw`).

### Precedência e Cascata de Resolução (Decisões D4 e D7)

A resolução dos parâmetros ocorre em duas passadas através de uma cascata rigorosa de 8 etapas implementada em `params.resolve()`. A primeira etapa que fornecer um valor válido vence:

| Precedência | Origem | Registrada como |
|---|---|---|
| 1º | Parâmetro fixado na UI marcando a opção **Fixar** (sem campo mapeado) | `usuario` |
| 2º | Coluna da camada selecionada na coluna **Campo da camada** | `oficial` |
| 3º | Tradução automática de atributos de fontes oficiais conhecidas (`oficiais.traduz`) | `oficial` |
| 4º | Colunas com nomes candidatos padrão presentes na feição (incluindo o esquema da malha padronizada) | `oficial` |
| 5º | Feição mais próxima da **Camada complementar** a até a distância máxima configurada | `complementar` |
| 6º | Valor digitado na coluna **Valor onde não há dado** | `usuario` |
| 7º | Padrão por classe de rodovia (`PADRAO_POR_CLASSE`: pista dupla, simples ou não pavimentada) | `padrao` |
| 8º | Padrão de fábrica do catálogo do plugin (`PARAMS`) | `padrao` |

!!! note "A proveniência vai para a camada de saída"
    Cada arco carrega um campo `src_<parâmetro>` com `oficial`, `complementar`, `usuario` ou
    `padrao`, e a mensagem final resume quantos (arco, parâmetro) vieram de
    cada origem. É o que separa "capacidade calculada com o dado da base" de
    "capacidade calculada com o padrão de fábrica" — ver
    [Parâmetros HCM](../referencia/parametros-hcm.md).

### Botão Calcular capacidade

O botão **Calcular capacidade** ("Compute capacity"), localizado no rodapé da aba, roda **só** a parte HCM:
monta os arcos a partir da malha, resolve os parâmetros operacionais e publica a camada
**`capacidade_hcm`**, com `volume = 0` no GeoPackage de saída compartilhado. Serve para conferir a capacidade e a
proveniência **antes** de gastar tempo com a alocação — e não exige matriz nem
centroides, só a rede. Arcos cuja capacidade sai **zero ou inválida** são descartados.

## Aba Alocação

A aba **Alocação** ("Assignment") configura a demanda e executa a alocação de tráfego sobre a malha rodoviária.

O grupo *Alocação* ("Assignment") pede a matriz e os centroides:

| Campo | O que escolher |
|---|---|
| *Matriz OD* ("OD matrix") | Camada da matriz — o combo lista camadas **sem geometria** |
| *Origem* ("Origin") / *Destino* ("Destination") | Colunas de id de zona na matriz |
| *Demanda (veíc/h)* ("Demand (veh/h)") | Coluna numérica de demanda — aqui a unidade importa: a capacidade HCM é em **veículos por hora por sentido** |
| *Centroides* ("Centroids") | Camada de centroides |
| *ID de Tráfego* ("Traffic id") | Campo dos centroides com o mesmo id usado em Origem/Destino |
| *Conector máximo (m)* ("Max connector (m)") | Distância máxima aceita entre um centroide e a malha rodoviária (`max_dist_m`, padrão 5000 m) |

Cada centroide é ligado à malha por um **conector** de ida e volta (os conectores ligam o centroide à malha para o cálculo, mas **não aparecem** na camada de saída), com
capacidade alta e custo desprezível — ele existe só para injetar a demanda na
rede, não representa via nenhuma. A âncora é o ponto mais próximo **do link** (o link é
dividido ali). Centroide cuja distância à malha está além do
*Conector máximo (m)* fica **fora** da alocação, e o plugin diz quantos.

### Método: AoN, Equilíbrio MSA ou Equilíbrio Frank-Wolfe

O campo *Método* ("Method") define o algoritmo de carregamento:

| Método | Como carrega | Quando usar |
|---|---|---|
| *Tudo-ou-Nada (sem restrição de capacidade)* ("All-or-Nothing (no capacity restraint)") | Uma passada pelo caminho de menor tempo a **fluxo livre**; todo o fluxo do par vai por esse caminho | Diagnóstico de sobrecarga: onde a demanda excede a capacidade se ninguém desviar |
| *Equilíbrio MSA + BPR* ("Equilibrium MSA + BPR") | Iterativo: o tempo de cada arco cresce com o carregamento (função **BPR**, `t = t0 · (1 + α·(v/c)^β)`) e a demanda se redistribui pela **média de sucessivas** (passo rígido $1/k$) | Estimativa de equilíbrio para estudos didáticos ou comparativo com métodos clássicos |
| *Equilíbrio Frank-Wolfe + BPR* ("Equilibrium Frank-Wolfe + BPR") | Iterativo com passo ótimo: a cada iteração avalia a função de Beckmann e calcula o tamanho de passo ótimo $\lambda$ por **busca linear por bisseção** | **Padrão recomendado**: Equilíbrio do Usuário de Wardrop com rápida convergência a gaps rigorosos |

*Iterações* ("Iterations", padrão **100**, configurável até 5000) e *Tolerância do gap* ("Gap tolerance", padrão **0,001**) valem para os métodos de equilíbrio (**Frank-Wolfe** e **MSA**) — com Tudo-ou-Nada selecionado, ambos os campos ficam desabilitados. O algoritmo encerra quando o gap atinge a tolerância configurada ou quando se esgota o número de iterações; a mensagem final na barra de mensagens informa o gap alcançado e o número de iterações executadas.

O método selecionado por padrão é o **Equilíbrio Frank-Wolfe + BPR**, pois sua convergência é substancialmente mais rápida que a do MSA, alcançando precisão superior em menos iterações.

!!! warning "Sob AoN, vc > 1 não é equilíbrio — é sobrecarga"
    No AoN a capacidade **nunca** volta para o custo, então nada impede que um
    arco receba mais viagens do que comporta. O gap sai como "n/a" de
    propósito. Um `vc` acima de 1 ali diz *"a demanda excede a capacidade neste
    trecho"*, não *"este é o carregamento de equilíbrio"*.

### Botão Alocar

O botão **Alocar** ("Assign"), no rodapé da aba, executa o processo completo de construção do grafo, leitura da matriz OD e alocação de tráfego, publicando a camada **`alocacao_fw`**, **`alocacao_msa`** ou **`alocacao_aon`** (conforme o método escolhido) no GeoPackage compartilhado.

Ao concluir com sucesso, o plugin preenche e seleciona automaticamente a camada recém-publicada no campo *Camada de alocação* da **Aba Calibração**.

## Aba Calibração

A aba **Calibração** ("Calibration") confronta os volumes alocados pelo modelo contra contagens volumétricas observadas em campo (como os postos de contagem do PNCT/DNIT), calculando a estatística **GEH** e avaliando a aderência da macrossimulação a critérios normativos.

### Entradas da calibração

O grupo *Calibração com contagens de tráfego (GEH)* ("Calibration with traffic counts (GEH)") reúne os parâmetros necessários para a avaliação:

| Campo | O que preencher | Descrição |
|---|---|---|
| *Camada de alocação* ("Assignment layer") | Camada linear de alocação | Camada contendo os atributos `link_id` e `volume`. É preenchida automaticamente com a camada recém-gerada ao acionar o botão *Alocar*. |
| *Postos de contagem* ("Count posts") | Camada de pontos | Camada contendo a localização espacial dos postos de contagem de tráfego. |
| *Campo da contagem* ("Count field") | Coluna numérica | Campo da camada de postos com o volume observado (ex.: VMDa). |
| *Campo de id do posto (opcional)* ("Post id field (optional)") | Coluna identificadora (opcional) | Identificador legível do posto de contagem. Se vazio, o plugin adota o `FID` da feição. |
| *Distância máxima de casamento* ("Max. snapping distance") | Distância em metros (padrão **200 m**) | Raio máximo de busca para associar um posto ao trecho alocado mais próximo. |
| *Fator modelo → contagem* ("Model → count factor") | Fator numérico (padrão **1,0000**) | Multiplicador de escala aplicado ao volume alocado para compatibilizar unidades temporais e conceituais. |

### Casamento espacial posto → trecho

Para relacionar cada posto com a rede viária alocada, o algoritmo executa o casamento (*snapping*) espacial:

1. **Trecho mais próximo e soma dos dois sentidos**: A camada de alocação possui uma feição por arco dirigido (`fw` e `bw`), e trechos divididos pela ancoragem de centroides mantêm o mesmo `link_id`. Como as contagens em postos rodoviários (como o PNCT) são bidirecionais, o plugin localiza o trecho mais próximo ao posto e **soma os volumes de todas as feições do mesmo `link_id` cuja distância ao posto esteja dentro de 1 metro da menor distância**. Esse procedimento soma os dois sentidos (`fw` + `bw`) do mesmo trecho físico (e preserva vias de mão única naturalmente em um arco único).
2. **Postos sem trecho associado (`sem_link`)**: Se a menor distância entre o posto e a rede for superior à *Distância máxima de casamento* (padrão 200 m), o posto é considerado afastado da malha modelada. Ele é gravado na camada de saída com `faixa = 'sem_link'` e `geh` nulo (`NULL`), ficando **excluído** do total avaliado ($n$) nos percentuais do critério DNIT e no %RMSE.
3. **Contagens inválidas**: Postos com contagens nulas, não numéricas, negativas ou com geometria vazia são desconsiderados do cálculo e contabilizados no registro de mensagens.

### Fator modelo → contagem (Unidades)

Em respeito à regra de transparência de que **nada é assumido em silêncio**, o plugin exige que o usuário defina explicitamente a conversão entre a unidade da matriz e a unidade das contagens:

* A capacidade HCM e a matriz de viagens são modeladas habitualmente em **veículos por hora de pico** (veíc/h de pico).
* As contagens de rodovias (como as bases oficiais do PNCT) costumam ser expressas em **Volume Médio Diário anual (VMDa)**.
* Se a hora de pico representa, por exemplo, uma fração $K = 0,10$ do volume diário ($VMDa \approx \text{Pico} / K$), o **Fator modelo → contagem** deve ser definido como **$10,0$** ($1 / K$).
* O volume modelado comparado é calculado como $M = \text{volume alocado} \times \text{fator}$. O fator utilizado fica registrado no atributo `fator` de cada feição de saída.

### Botão Calibrar e leitura dos resultados

O botão **Calibrar** ("Calibrate"), posicionado no rodapé da aba, executa o casamento espacial e o cálculo do GEH, gravando a camada de pontos **`calibracao_geh`** no GeoPackage compartilhado. A camada é carregada no projeto QGIS e estilizada com símbolos categorizados por faixa de GEH:

* **Faixa A** ($GEH < 5$): verde (`#2ca02c`) — excelente calibração;
* **Faixa B** ($5 \le GEH < 10$): amarelo (`#ffff33`) — aderência aceitável;
* **Faixa C** ($10 \le GEH < 12$): laranja (`#ff7f00`) — divergência moderada;
* **Faixa D** ($GEH \ge 12$): vermelho (`#d7191c`) — divergência acentuada;
* **Sem link** (`sem_link`): cinza (`#808080`) — postos situados além da distância máxima de casamento.

Ao concluir, a barra de mensagens do QGIS apresenta o diagnóstico geral:
> `Calibração: N postos (k sem trecho a até X m) — A p% · A+B q% · %RMSE r — Critério DNIT (≥60% A, ≥95% A+B): atendido (ou não atendido) (fator f)`

A notificação é exibida em verde (*success*) quando o critério oficial do DNIT é satisfeito e em amarelo (*warning*) caso não seja atendido. Adicionalmente, o **Registro de Mensagens** do QGIS (*Message Log*, aba *Desire Lines*) relaciona os 10 postos com maior valor de GEH (posto, contagem, modelado e GEH), orientando onde concentrar ajustes de capacidade, zoneamento ou geração de viagens.

## O resultado

Todas as camadas são gravadas no arquivo configurado em **GeoPackage de saída**:
as camadas de alocação **`alocacao_fw`**, **`alocacao_msa`** ou **`alocacao_aon`**, a camada prévia **`capacidade_hcm`** (gerada pelo botão *Calcular capacidade*) e a camada de pontos **`calibracao_geh`** (gerada pelo botão *Calibrar*).

As camadas de arcos são estilizadas por **`vc`** em classes fixas de A a F (verde até
0,35; roxo grosso acima de 1,00). Campos principais da alocação:

| Campo | Significado |
|---|---|
| `arc_id` / `link_id` / `sentido` | Identificação do arco dirigido e do link de origem (`fw`/`bw`) |
| `tipo` | Classificação do arco: `link` (original intacto) ou `link_dividido` (dividido para ancorar centróide) |
| `faixas`, `comp_m`, `vel_livre` | Faixas por sentido, comprimento em metros, velocidade de fluxo livre |
| `capacidade` | Capacidade por sentido em veíc/h (HCM ou informada) |
| `volume` | Volume alocado no arco |
| `vc` | `volume / capacidade` |
| `los` | Nível de serviço **aproximado**, derivado do `vc` (o LOS oficial do HCM usa densidade/velocidade média de viagem) |
| `tempo_h`, `atraso_h` | Tempo de viagem no arco e atraso sobre o fluxo livre |
| `metodo`, `escopo` | Método usado (`fw`/`msa`/`aon`/`capacidade`) e `rodoviario` ou `urbano` |
| `src_*` | Proveniência de cada parâmetro (incluindo `src_capacidade`, `src_tempo_livre`, `src_mao_unica`): `oficial`, `complementar`, `usuario` ou `padrao` |

A mensagem de sucesso ao final da alocação resume os pares alocados,
número de arcos, proveniência, contagem de arcos urbanos, gap,
linhas da matriz com id desconhecido e pares **inalcançáveis** (rede
desconexa) — ver [Campos de saída](../referencia/campos-de-saida.md)
e [Solução de problemas](../solucao-de-problemas.md).

!!! warning "Os ids precisam usar o mesmo esquema"
    Se *Origem*, *Destino* e *ID de Tráfego* não usarem a mesma codificação,
    nenhum par casa e a alocação aborta com aviso. Mesma armadilha da
    [Matriz OD](matriz-od.md).

**Próximo passo:** [Exemplos](exemplos.md).
