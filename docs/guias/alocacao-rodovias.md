# Alocação em rodovias

O painel **Alocação em rodovias** carrega a matriz OD sobre a **malha rodoviária
real** (SNV/DER), calcula a **capacidade de cada trecho pelo procedimento do
HCM 6ª edição** e devolve volume, relação volume/capacidade (`vc`) e nível de
serviço por arco. É o resultado que a rede sintética da aba
[AoN (Delaunay)](aon-delaunay.md) não consegue dar — lá não há capacidade.

Para abrir o painel, use o **botão único da barra com seta de menu** (o clique abre o diálogo principal; a seta, o menu com *Desire Lines* e *Alocação em rodovias* ["Highway Assignment"]) ou acesse o menu **Vetor ▸ Desire Lines ▸ Alocação em rodovias**.
O painel ancora no lado direito da janela do QGIS e pode permanecer aberto
enquanto você navega no mapa ou edita camadas. Ele é dividido em duas abas
internas: **Alocação** ("Allocation") e **Parâmetros HCM** ("HCM parameters").

!!! danger "Escopo: rodovias rurais/interurbanas"
    A capacidade vem do **HCM cap. 15** (pista simples, duas faixas) e do
    **cap. 12** (pista dupla / multifaixa / freeway). Travessias urbanas
    dentro da malha são **marcadas** com `escopo='urbano'` e contadas no aviso
    final, mas **não** são recalculadas por procedimento urbano — o
    procedimento urbano do HCM (caps. 16-19) exige dados de semáforo que a
    base oficial não traz. Leia esses arcos com reserva.

## Aba Alocação

A aba **Alocação** ("Allocation") reúne as configurações da malha, da matriz e da alocação, além da seleção do arquivo de saída.

### A rede: camada existente ou download via GisBR

O grupo *Rede* ("Network") tem duas opções, mutuamente exclusivas:

| Opção | O que preencher | Quando usar |
|---|---|---|
| *Usar uma camada existente* ("Use an existing layer") | *Camada de rodovias* ("Highway layer") e, opcionalmente, *Campo de id do link (opcional)* ("Link id field (optional)") | Você já tem a malha carregada no projeto (arquivo local, recorte próprio) |
| *Baixar via GisBR (malha oficial SNV/DER)* ("Download via GisBR (official SNV/DER network)") | *Estado (UF)* ("State (UF)") (sigla de **2 letras**), *Área de download* ("Download area") e, se regional, *Região* ("Region") | Quer a malha oficial baixada na hora |

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

As quatro opções regionais (*Região Metropolitana*, *Microrregião*, *Mesorregião* e *Macrorregião de saúde*) exigem o preenchimento da *UF* (2 letras), que faz o plugin carregar dinamicamente as regiões disponíveis daquele estado, e a escolha obrigatória de um item no combo *Região* ("Region"). Enquanto uma região válida não for selecionada, os botões de execução permanecem desabilitados.

A escolha da fonte rodoviária é feita de forma automática a partir do catálogo do GisBR: se a UF possuir base viária estadual cadastrada — como é o caso de Minas Gerais (`der_mg_rodovias`) e Goiás (`go_malha_viaria`) hoje —, o plugin utiliza a malha oficial estadual; caso contrário, recorre automaticamente à malha rodoviária federal do Sistema Nacional de Viação (SNV/DNIT) como reserva (*fallback*).

Quando utilizada a opção *Usar uma camada existente*, a área de estudo também é recortada pela extensão dos centroides (com buffer de conector), limitando o tamanho da rede e acelerando a montagem do grafo. Se o recorte falhar, o plugin exibe um aviso e segue com a malha inteira.

!!! note "Reprojeção automática para CRS métrico"
    Camadas em CRS geográfico (graus) — tanto no download via GisBR quanto em camada existente — são reprojetadas sozinhas para um CRS métrico (UTM da região, ou SIRGAS 2000 / Brazil Albers se a área cobrir mais de uma zona). A camada de saída sai nesse CRS, e o aviso *Malha rodoviária reprojetada…* (*Highway network reprojected…*) aparece na barra de mensagens (*message bar*).

### A alocação

O grupo *Alocação* ("Assignment") pede a matriz e os centroides:

| Campo | O que escolher |
|---|---|
| *Matriz OD* ("OD matrix") | Camada da matriz — o combo lista camadas **sem geometria** |
| *Origem* ("Origin") / *Destino* ("Destination") | Colunas de id de zona na matriz |
| *Demanda (veíc/h)* ("Demand (veh/h)") | Coluna numérica de demanda — aqui a unidade importa: a capacidade HCM é em **veículos por hora por sentido** |
| *Centroides* ("Centroids") | Camada de centroides |
| *ID de Tráfego* ("Traffic id") | Campo dos centroides com o mesmo id usado em Origem/Destino |
| *Conector máximo (m)* ("Max connector (m)") | Distância máxima aceita entre um centroide e a malha rodoviária (`max_dist_m`, padrão 5000 m) |

Cada centroide é ligado à malha por um **conector** de ida e volta (estilizado como conector tracejado cinza), com
capacidade alta e custo desprezível — ele existe só para injetar a demanda na
rede, não representa via nenhuma. A âncora é o ponto mais próximo **do link** (o link é
dividido ali). Centroide cuja distância à malha está além do
*Conector máximo (m)* fica **fora** da alocação, e o plugin diz quantos.

#### Método: AoN, Equilíbrio MSA ou Equilíbrio Frank-Wolfe

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

### GeoPackage de saída e botões de ação

Abaixo do grupo de alocação, o campo *GeoPackage de saída* ("Output GeoPackage") define o arquivo `.gpkg` onde as camadas geradas serão gravadas. Se deixado em branco, o plugin utiliza o caminho padrão `~/output.gpkg`.

Ao final da aba *Alocação*, dois botões acionam os processamentos:

* **Calcular capacidade** ("Compute capacity"): roda **só** a parte HCM:
  monta os arcos a partir da malha, resolve os parâmetros e publica a camada
  **`capacidade_hcm`**, com `volume = 0`. Serve para conferir a capacidade e a
  proveniência **antes** de gastar tempo com a alocação — e não exige matriz nem
  centroides, só a rede. Arcos cuja capacidade sai **zero ou inválida** são descartados.
* **Alocar** ("Assign"): executa o processo completo de construção do grafo, leitura da matriz OD e alocação de tráfego, publicando a camada **`alocacao_fw`**, **`alocacao_msa`** ou **`alocacao_aon`** (conforme o método escolhido).

## Aba Parâmetros HCM

A aba **Parâmetros HCM** ("HCM parameters") contém o grupo *Parâmetros HCM (padrão, ou sobrescrever globalmente / por campo)* ("HCM parameters (default, or override globally / by field)"), que reúne as configurações operacionais e geométricas para o cálculo de capacidade HCM e parâmetros de rede.

Nada é assumido em silêncio: a aba traz uma linha por parâmetro para os 18 parâmetros do sistema (tipo de segmento,
faixas, terreno, % de veículos pesados, FFS, PHF, largura de faixa e
acostamento, ultrapassagem proibida, densidade de acessos, divisão direcional,
alfa e beta do BPR, capacidade informada, tempo livre e mão única).

Cada linha oferece **duas saídas**: um valor global digitado no controle e um *combobox* *field:* ("field:") para mapear qualquer coluna da camada de rodovias.

### Parâmetros Especiais de Rede e a Sentinela `0`

Três parâmetros permitem incorporar diretamente atributos conhecidos de malhas já calibradas (como redes municipais ou benchmarks tipo Sioux Falls):

* **Capacidade por sentido (0 = HCM)** (`capacidade`): Capacidade por sentido em veíc/h. A sentinela **`0`** indica cálculo automático pelo procedimento do HCM 6ª edição (Cap. 15 pista simples ou Cap. 12 pista dupla/freeway). Qualquer valor **`> 0`** substitui a capacidade do HCM.
* **Tempo de fluxo livre (0 = comprimento ÷ FFS)** (`tempo_livre`): Tempo em fluxo livre em minutos. A sentinela **`0`** calcula o tempo com base no comprimento geométrico e na velocidade livre (`comprimento ÷ vel_livre`). Qualquer valor **`> 0`** substitui o tempo calculado.
* **Mão única (sentido da geometria)** (`mao_unica`): Booleano. Se verdadeiro (`True`, `1`, `'sim'`, `'yes'`), gera apenas o arco no sentido da geometria (`fw`), omitindo o reverso (`bw`). Se falso (`False`), gera os dois arcos direcionados (`fw` e `bw`).

### Precedência e Mapeamento de Campos (Decisão D2)

Quando você seleciona uma coluna no combo *field:* de qualquer parâmetro, esse mapeamento é repassado diretamente para a resolução (`field_map`). O valor encontrado na coluna mapeada é adotado com proveniência **`oficial`**.

A ordem de precedência rigorosa por feição e por parâmetro é:

| Precedência | Origem | Registrada como |
|---|---|---|
| 1º | Valor global digitado na aba (se diferente de sentinela 0 para capacidade/tempo livre) | `usuario` |
| 2º | Coluna da camada selecionada no combo *field:* daquela linha | `oficial` |
| 3º | Colunas com nomes candidatos padrão presentes na feição | `oficial` |
| 4º | Padrão do catálogo de fábrica do plugin | `padrao` |

!!! note "A proveniência vai para a camada de saída"
    Cada arco carrega um campo `src_<parâmetro>` com `oficial`, `usuario` ou
    `padrao`, e a mensagem final resume quantos (arco, parâmetro) vieram de
    cada origem. É o que separa "capacidade calculada com o dado da base" de
    "capacidade calculada com o padrão de fábrica" — ver
    [Parâmetros HCM](../referencia/parametros-hcm.md).

## O resultado

A camada sai no GeoPackage de saída configurado no campo *GeoPackage de saída*, com nome conforme o método —
**`alocacao_fw`**, **`alocacao_msa`** ou **`alocacao_aon`** (e `capacidade_hcm` pelo botão **Calcular capacidade**) — e é estilizada por **`vc`** em classes fixas de A a F (verde até
0,35; roxo grosso acima de 1,00). Campos principais:

| Campo | Significado |
|---|---|
| `arc_id` / `link_id` / `sentido` | Identificação do arco dirigido e do link de origem (`fw`/`bw`) |
| `tipo` | Classificação do arco: `link` (original intacto), `link_dividido` (dividido para ancorar centróide) ou `conector` |
| `faixas`, `comp_m`, `vel_livre` | Faixas por sentido, comprimento em metros, velocidade de fluxo livre |
| `capacidade` | Capacidade por sentido em veíc/h (HCM ou informada) |
| `volume` | Volume alocado no arco |
| `vc` | `volume / capacidade` |
| `los` | Nível de serviço **aproximado**, derivado do `vc` (o LOS oficial do HCM usa densidade/velocidade média de viagem) |
| `tempo_h`, `atraso_h` | Tempo de viagem no arco e atraso sobre o fluxo livre |
| `metodo`, `escopo` | Método usado (`fw`/`msa`/`aon`/`capacidade`) e `rodoviario`, `urbano` ou `conector` |
| `src_*` | Proveniência de cada parâmetro (incluindo `src_capacidade`, `src_tempo_livre`, `src_mao_unica`): `oficial`, `usuario` ou `padrao` |

A mensagem de sucesso ao final é onde as perdas aparecem: pares alocados,
número de arcos, resumo de proveniência, contagem de arcos urbanos, gap,
linhas da matriz com id desconhecido e pares **inalcançáveis** (rede
desconexa). Vale ler — ver [Campos de saída](../referencia/campos-de-saida.md)
e [Solução de problemas](../solucao-de-problemas.md).

!!! warning "Os ids precisam usar o mesmo esquema"
    Se *Origem*, *Destino* e *ID de Tráfego* não usarem a mesma codificação,
    nenhum par casa e a alocação aborta com aviso. Mesma armadilha da
    [Matriz OD](matriz-od.md).

**Próximo passo:** [Exemplos](exemplos.md).
