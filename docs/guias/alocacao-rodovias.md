# Alocação em rodovias

A aba **Alocação em rodovias** carrega a matriz OD sobre a **malha rodoviária
real** (SNV/DER), calcula a **capacidade de cada trecho pelo procedimento do
HCM 6ª edição** e devolve volume, relação volume/capacidade (v/c) e nível de
serviço por arco. É o resultado que a rede sintética da aba
[AoN (Delaunay)](aon-delaunay.md) não consegue dar — lá não há capacidade.

!!! danger "Escopo: rodovias rurais/interurbanas"
    A capacidade vem do **HCM cap. 15** (pista simples, duas faixas) e do
    **cap. 12** (pista dupla / multifaixa / freeway). Travessias urbanas
    dentro da malha são **marcadas** com `escopo='urbano'` e contadas no aviso
    final, mas **não** são recalculadas por procedimento urbano — o
    procedimento urbano do HCM (caps. 16-19) exige dados de semáforo que a
    base oficial não traz. Leia esses arcos com reserva.

## A rede: camada existente ou download via GisBR

O grupo *Rede* ("Network") tem duas opções, mutuamente exclusivas:

| Opção | O que preencher | Quando usar |
|---|---|---|
| *Usar uma camada existente* ("Use an existing layer") | *Camada de rodovias* e, opcionalmente, *Campo de id do link* | Você já tem a malha carregada no projeto (arquivo local, recorte próprio) |
| *Baixar via GisBR (malha oficial SNV/DER)* | *UF* (sigla de **2 letras**) e a caixa *Recortar para a extensão dos centroides* | Quer a malha oficial baixada na hora |

O *Campo de id do link* é opcional: serve para o campo `link_id` da saída
apontar de volta para o identificador da sua base. Sem ele, o plugin gera um
id próprio.

!!! warning "O download depende do plugin GisBR"
    A opção de download só habilita se o plugin
    [GisBR](https://github.com/d-camargo/gisbr) estiver instalado — sem ele, o
    aviso no topo da aba fica visível e o plugin volta sozinho para *Usar uma
    camada existente*. O resto da aba **funciona normalmente** com camada
    própria; só o download é bloqueado.

Com *Recortar para a extensão dos centroides* marcada, a área de estudo é a
**envoltória dos centroides mais o raio de conector** (*Conector máximo*).
Isso limita o download e também recorta uma camada existente — rede menor,
grafo mais rápido. Se o recorte falhar, o plugin avisa e segue com a malha
inteira.

## Parâmetros HCM: nada é assumido em silêncio

O grupo *Parâmetros HCM* traz uma linha por parâmetro (tipo de segmento,
faixas, terreno, % de veículos pesados, FFS, PHF, largura de faixa e
acostamento, ultrapassagem proibida, densidade de acessos, divisão direcional,
alfa e beta do BPR). Cada linha oferece **duas saídas**: um valor global,
digitado ali, e um **campo da camada de rodovias** que vale mais que ele.

A ordem de precedência, por arco e por parâmetro, é:

| Precedência | Origem | Registrada como |
|---|---|---|
| 1º | Campo da camada de rodovias (o *field:* da linha, quando preenchido) | `oficial` |
| 2º | Valor global digitado na aba | `usuario` |
| 3º | Padrão do catálogo do plugin | `padrao` |

!!! note "A proveniência vai para a camada de saída"
    Cada arco carrega um campo `src_<parâmetro>` com `oficial`, `usuario` ou
    `padrao`, e a mensagem final resume quantos (arco, parâmetro) vieram de
    cada origem. É o que separa "capacidade calculada com o dado da base" de
    "capacidade calculada com o padrão de fábrica" — ver
    [Parâmetros HCM](../referencia/parametros-hcm.md).

## Calcular capacidade sem alocar

O botão *Calcular capacidade* ("Compute capacity") roda **só** a parte HCM:
monta os arcos a partir da malha, resolve os parâmetros e publica a camada
**`capacidade_hcm`**, com `volume = 0`. Serve para conferir a capacidade e a
proveniência **antes** de gastar tempo com a alocação — e não exige matriz nem
centroides, só a rede.

Arcos cuja capacidade sai **zero ou inválida** são descartados, e o plugin diz
quantos: mantê-los faria o v/c dividir por zero e reportar nível de serviço F
onde na verdade falta dado.

## A alocação

O grupo *Alocação* pede a matriz e os centroides:

| Campo | O que escolher |
|---|---|
| *Matriz OD* ("OD matrix") | Camada da matriz — o combo lista camadas **sem geometria** |
| *Origem* / *Destino* | Colunas de id de zona na matriz |
| *Demanda (veíc/h)* ("Demand (veh/h)") | Coluna numérica de demanda — aqui a unidade importa: a capacidade HCM é em **veículos por hora por sentido** |
| *Centroides* ("Centroids") | Camada de centroides |
| *ID de Tráfego* ("Traffic id") | Campo dos centroides com o mesmo id usado em Origem/Destino |
| *Conector máximo (m)* ("Max connector (m)") | Distância máxima aceita entre um centroide e o nó mais próximo da malha (padrão 5000 m) |

Cada centroide é ligado à malha por um **conector** de ida e volta, com
capacidade alta e custo desprezível — ele existe só para injetar a demanda na
rede, não representa via nenhuma. Centroide cujo nó mais próximo está além do
*Conector máximo* fica **fora** da alocação, e o plugin diz quantos.

### Método: AoN ou Equilíbrio MSA + BPR

| Método | Como carrega | Quando usar |
|---|---|---|
| *Tudo-ou-Nada (sem restrição de capacidade)* | Uma passada pelo caminho de menor tempo a **fluxo livre**; todo o fluxo do par vai por esse caminho | Diagnóstico de sobrecarga: onde a demanda excede a capacidade se ninguém desviar |
| *Equilíbrio MSA + BPR* | Iterativo: o tempo de cada arco cresce com o carregamento (função **BPR**, `t = t0 · (1 + α·(v/c)^β)`) e a demanda se redistribui pela **média de sucessivas** (MSA) | Estimativa de carregamento com congestionamento realimentado |

*Iterações* (padrão 10) e *Tolerância do gap* (padrão 0,01) só valem para o
MSA — com AoN selecionado, os dois campos ficam desabilitados. O MSA para
quando o gap cai abaixo da tolerância ou quando as iterações acabam; a
mensagem final informa o gap alcançado e em quantas iterações.

!!! warning "Sob AoN, v/c > 1 não é equilíbrio — é sobrecarga"
    No AoN a capacidade **nunca** volta para o custo, então nada impede que um
    arco receba mais viagens do que comporta. O gap sai como "n/a" de
    propósito. Um v/c acima de 1 ali diz *"a demanda excede a capacidade neste
    trecho"*, não *"este é o carregamento de equilíbrio"*.

## O resultado

A camada sai no mesmo GeoPackage de saída, com nome conforme o método —
**`alocacao_aon`** ou **`alocacao_msa`** (e `capacidade_hcm` pelo botão de
capacidade) — e é estilizada por **v/c** em classes fixas de A a F (verde até
0,35; roxo grosso acima de 1,00). Campos principais:

| Campo | Significado |
|---|---|
| `arc_id` / `link_id` / `sentido` | Identificação do arco dirigido e do link de origem (`fw`/`bw`) |
| `faixas`, `comp_m`, `vel_livre` | Faixas por sentido, comprimento em metros, velocidade de fluxo livre |
| `capacidade` | Capacidade HCM, em veíc/h **por sentido** |
| `volume` | Volume alocado no arco |
| `vc` | `volume / capacidade` |
| `los` | Nível de serviço **aproximado**, derivado do v/c (o LOS oficial do HCM usa densidade/velocidade média de viagem) |
| `tempo_h`, `atraso_h` | Tempo de viagem no arco e atraso sobre o fluxo livre |
| `metodo`, `escopo` | Método usado (`aon`/`msa`/`capacidade`) e `rodoviario`, `urbano` ou `conector` |
| `src_*` | Proveniência de cada parâmetro HCM: `oficial`, `usuario` ou `padrao` |

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
