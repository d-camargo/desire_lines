# Matriz OD

A aba **Matriz Origem/Destino** ("Origin/Destination Matrix") é a primeira das
quatro abas do plugin. Ela prepara os dois insumos que todas as outras abas
usam: a matriz OD lida como tabela e os centroides das zonas de tráfego,
gravando ambos no mesmo GeoPackage de saída.

## Passo a passo

1. **Importar a matriz.** Escolha o CSV no seletor de arquivo (filtro
    `CSV(*csv)`) e clique em *Ler CSV* ("Read CSV"). A leitura assume
    encoding **windows-1252** e delimitador **`;`**, sem geometria. A tabela
    entra no projeto com o nome `matrix` e é gravada no GeoPackage como a
    tabela `output`.

2. **Formato largo ou longo.** Marque *Formato da Matriz de Demanda de
    Viagens* ("Travel Demand Matrix format") quando a matriz estiver em
    **formato largo (wide)** — uma coluna `OD` mais uma coluna por destino. O
    plugin converte para **formato longo** com `pandas.melt` (`id_vars='OD'`),
    gerando as colunas `Origem`, `Destino` e `Passageiros`, grava um
    `matrix_long.csv` ao lado do arquivo original e passa a usar esse arquivo
    daí em diante. Desmarcada, a matriz já deve estar em formato longo (uma
    linha por par OD).

    !!! warning "Exige pandas"
        A conversão wide→long depende de `pandas` estar disponível no Python
        do QGIS. Sem ele, o plugin mostra uma mensagem de erro pedindo para
        instalar a biblioteca e recarregar o plugin.

3. **Zonas de tráfego.** A camada *Zona de tráfego (formato shp ou gpkg)*
    ("Traffic zone (shp or gpkg format)") chega por dois caminhos
    equivalentes:

    - importe um SHP/GPKG no seletor e clique em *Ler Vetor* ("Read
      Vector") — a camada entra no projeto como `traffic_zones` e é
      selecionada automaticamente no combo logo abaixo; ou
    - escolha, no combo "…ou selecione uma camada de zonas de tráfego já
      existente no projeto (deixe em branco para usar o arquivo importado
      acima):", uma camada de polígonos já aberta no projeto — o combo só
      lista camadas de polígono e pode ficar vazio.

    Se o combo ficar vazio, o botão de centroides cai no *fallback* de
    procurar uma camada chamada `traffic_zones`.

4. **GeoPackage de Saída** ("Output GeoPackage"). O seletor de arquivo
    (filtro `GeoPackage (*.gpkg)`) define onde tudo é gravado; se o caminho
    não terminar em `.gpkg`, a extensão é acrescentada. Deixando em branco, o
    plugin usa um `output.gpkg` na pasta do CSV da matriz — ou, na falta
    dele, na pasta do arquivo vetorial, e em último caso na pasta pessoal do
    usuário. Vale preencher explicitamente, para saber onde o resultado foi
    parar.

5. **Adicionar Centroides às Zonas de Tráfego** ("Add Centroids to Traffic
    Zones"). Roda o algoritmo `native:centroids` com `ALL_PARTS=True` (uma
    feição de centroide por parte de multipolígono) sobre a camada de zonas
    escolhida, grava a tabela `centroids` no GeoPackage e adiciona a camada
    ao projeto.

## O que sai no GeoPackage

| Tabela | Conteúdo |
|---|---|
| `output` | A matriz OD como tabela, sem geometria — uma linha por par OD |
| `centroids` | Pontos, um por zona (ou parte de multipolígono), herdando os atributos da camada de zonas |

As abas seguintes leem exatamente essas duas camadas. Para o formato
esperado do CSV da matriz e da camada de zonas, veja [Formatos de
entrada](../referencia/formatos-de-entrada.md).

## O que as próximas abas vão pedir dessa matriz

Os combos *Origem* ("Origin"), *Destino* ("Destination") e *ID de Tráfego*
("Traffic ID") aparecem nas abas seguintes (Linhas de desejo, AoN (Delaunay),
Alocação em rodovias), não nesta — mas é aqui que se decide se eles terão o
que escolher:

- a matriz precisa ter uma coluna de origem, uma de destino e uma coluna de
  valor/fluxo, uma linha por par OD;
- *Origem* e *Destino* apontam para as colunas de identificador da matriz;
- *ID de Tráfego* aponta para o campo da camada de centroides que traz o
  mesmo identificador;
- o campo de valor — *Valor para Linhas de Desejo* ("Value to Desire Lines"),
  na aba seguinte — é a coluna numérica de fluxo.

Na conversão wide→long as colunas resultantes se chamam `Origem`, `Destino`
e `Passageiros`.

!!! warning "Os ids precisam usar o mesmo esquema"
    Os identificadores da matriz e o campo de id dos centroides têm que usar
    o mesmo esquema de codificação. Quando não usam, a alocação não encontra
    par nenhum e o plugin avisa "Nenhum par OD correspondeu aos ids dos
    centroides" — ver [Solução de problemas](../solucao-de-problemas.md).

**Próximo passo:** [Linhas de desejo](linhas-de-desejo.md).
