# Desire Lines

**Desire Lines** é um plugin do QGIS para **análise de demanda de transporte a partir
de uma matriz Origem/Destino (OD)**. A partir da matriz e de uma camada de zonas de
tráfego, ele gera os centroides, as linhas de desejo e a demanda alocada — sobre uma
rede sintética de vizinhança ou sobre a malha rodoviária real, com capacidade calculada
pelo procedimento do HCM 6ª edição.

É feito para quem planeja transporte, não para quem programa: tudo acontece em um
diálogo de quatro abas dentro do QGIS, e cada etapa grava uma tabela no mesmo
GeoPackage de saída.

## As quatro abas

- **Matriz OD** ("Origin/Destination Matrix") — importa a matriz OD em CSV e a camada
  de zonas de tráfego, e gera os centroides.
- **Linhas de desejo** ("Desire Lines") — traça uma reta por par OD entre os
  centroides, com espessura proporcional ao fluxo.
- **AoN (Delaunay)** — aloca a demanda por All-or-Nothing sobre uma rede sintética de
  Delaunay entre os centroides.
- **Alocação em rodovias** — calcula a capacidade pelo HCM 6ª edição e aloca a demanda
  sobre a malha rodoviária real (SNV), por AoN ou por equilíbrio MSA/BPR.

!!! warning "Escopo da aba Alocação em rodovias"
    Esta aba foi desenvolvida para **rodovias rurais e interurbanas**: travessias
    urbanas dentro da malha são marcadas com `escopo = 'urbano'` e avisadas, não
    recalculadas por procedimento urbano. Ela também **exige o plugin GISBR**
    instalado, que é quem busca a malha oficial (SNV/INDE) — sem ele, a aba fica
    bloqueada.

## Por onde começar

<div class="grid cards" markdown>

-   **[Instalação](instalacao.md)**

    Versões de QGIS suportadas, instalação pelo zip ou pelo gerenciador de
    complementos, e o requisito do GISBR para a aba de rodovias.

-   **[Guias](guias/matriz-od.md)**

    Um guia por aba, do CSV da matriz OD até a alocação em rodovias, mais um
    tutorial ponta a ponta com os dados de exemplo.

-   **[Referência](referencia/formatos-de-entrada.md)**

    Formatos de entrada, campos de cada camada de saída, parâmetros HCM com
    proveniência e o critério de escolha entre os métodos.

-   **[Solução de problemas](solucao-de-problemas.md)**

    O que fazer quando a matriz não lê, o GISBR não aparece ou a alocação sai
    vazia.

</div>
