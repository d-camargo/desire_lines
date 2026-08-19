# Arquitetura do Desire Lines

Este documento descreve a estrutura interna do plugin **Desire Lines**, a fronteira de dependências do QGIS, a execução da suíte de testes, o processo de empacotamento e o registro condensado das decisões de arquitetura (**D1–D11**) do módulo de alocação rodoviária.

---

## 1. Mapa dos Módulos

Todo o código-fonte do plugin reside dentro da pasta `desire_lines/`:

```text
desire_lines/
├── __init__.py                # Ponto de entrada do plugin QGIS (classFactory)
├── desirelines.py             # Classe principal: initGui(), run(), unload()
├── desirelines_dialog.py      # Lógica de UI e orquestração (rodar abas 1 a 4)
├── desirelines_dialog_base.ui # Interface Qt Designer (layout das 4 abas)
├── aon.py                     # Núcleo AoN em rede sintética de Delaunay (sem GUI)
├── metadata.txt               # Metadados oficiais lidos pelo QGIS e plugins.qgis.org
├── icon.png                   # Ícone do plugin no QGIS
├── i18n/                      # Traduções (DesireLines_pt.qm)
└── traffic/                   # Subpacote de alocação de tráfego sobre malha rodoviária real
    ├── __init__.py
    ├── hcm.py                 # Procedimentos de capacidade HCM (caps. 12 e 15)
    ├── graph.py               # Grafo dirigido em Python puro (heapq + Dijkstra)
    ├── network.py             # Construção de rede viária e conectores de centroides
    ├── params.py              # Tratamento de parâmetros HCM e proveniência (src_*)
    ├── assignment.py          # Motores de alocação (AoN e MSA + BPR)
    ├── gisbr_bridge.py        # Integração e checagem em runtime do plugin GISBR
    └── outputs.py             # Camadas de saída (capacidade_hcm/alocacao_*) e estilos v/c
```

### Detalhamento dos Componentes

- **`desirelines.py`**: Gerencia o ciclo de vida do plugin na barra de ferramentas e menus do QGIS. Instancia o diálogo `DesireLinesDialog` uma única vez e configura os filtros de seleção dos combos.
- **`desirelines_dialog.py`**: O maior arquivo de orquestração do plugin. Conecta a interface gráfica com as funções de backend, processa a leitura de matrizes, a geração de centroides e aciona as funções de alocação (`run_aon()` para Delaunay e `run_assignment()` para rodovias).
- **`aon.py`**: Módulo independente de GUI para a Aba 3. Realiza a triangulação de Delaunay entre centroides, a seleção de CRS métrico (`pick_metric_crs`) e a alocação All-or-Nothing sobre a rede sintética.
- **`traffic/`**: Subpacote dedicado à Aba 4 (alocação em rodovias reais com HCM). Desenvolvido sem lógica de interface gráfica, desacoplando o motor de cálculo da UI.

---

## 2. Fronteira entre Lógica Pura e PyQGIS

O código do plugin é dividido em duas categorias segundo a dependência da API do QGIS (`qgis.core` e `qgis.PyQt`):

### 2.1 Módulos Python Puro (sem dependência do QGIS)
Estes módulos não importam nenhum componente do QGIS e podem ser executados/testados em qualquer ambiente Python 3:

- **`traffic/hcm.py`**: Cálculos das equações de capacidade do HCM (capacidades de pista simples, pista dupla, multilane e freeway).
- **`traffic/graph.py`**: Implementação do grafo direcionado próprio usando estruturas nativas do Python (`heapq`, `dict`).
- **`traffic/network.py`**: Construtor do grafo viário e cálculo dos conectores entre centroides e nós da rede.
- **`traffic/params.py`**: Regras de parsing de parâmetros HCM e atribuição de proveniência (`src_*`).
- **`traffic/assignment.py`**: Algoritmos de alocação de tráfego AoN e MSA (Method of Successive Averages).

### 2.2 Módulos com Dependência PyQGIS
Estes módulos utilizam classes do QGIS (`QgsVectorLayer`, `QgsFeature`, `QgsGraphAnalyzer`, etc.) e exigem o ambiente QGIS inicializado:

- **`aon.py`**: Utiliza processamento nativo do QGIS (`native:delaunaytriangulation`, `native:polygonstolines`, etc.) e `QgsGraphAnalyzer` para a rede sintética.
- **`traffic/outputs.py`**: Constrói as camadas vetoriais de saída e aplica a simbologia graduada por `v/c`.
- **`traffic/gisbr_bridge.py`**: Faz chamadas via `processing.run('gisbr:...')` ou importa módulos internos do GISBR.
- **`desirelines_dialog.py` / `desirelines.py`**: Interagem diretamente com os widgets Qt e a interface do usuário.

---

## 3. Como Rodar a Suíte de Testes

A suíte de testes do repositório reside em `test/` e é executada via `pytest`.

### Execução Recomendada

Da raiz do repositório, execute:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest test -q
```

### Por que a variável `QT_QPA_PLATFORM=offscreen` é obrigatória?

Os testes que importam componentes do QGIS ou do PyQt precisam inicializar uma instância de `QApplication` (definida em `test/utilities.py:get_qgis_app()`). Em ambientes sem servidor X/Wayland ativo (como ambientes CI, servidores VPS ou terminais SSH):

- Sem `QT_QPA_PLATFORM=offscreen`, o Qt tenta abrir um display gráfico, falha e encerra o processo Python imediatamente com **core dump** / **segmentation fault**.
- Com `QT_QPA_PLATFORM=offscreen`, o plugin de renderização em memória do Qt é ativado, permitindo que a suíte execute completamente sem interface gráfica.

> **Nota**: O comando `make test` executa apenas uma verificação rápida de sintaxe Python (`ast.parse`) e não substitui a suíte completa do `pytest`.

---

## 4. Empacotamento e Deploy

O empacotamento do plugin para publicação é automatizado pelo `qgis-plugin-ci`.

### Fluxo de Build

1. **Configuração**: Definida no arquivo `.qgis-plugin-ci` na raiz do projeto:
   ```yaml
   plugin_path: desire_lines
   github_organization_slug: d-camargo
   project_slug: desire_lines
   ```
2. **Geração do ZIP**:
   ```bash
   make package
   ```
   Este comando executa `qgis-plugin-ci package $(VERSION) --disable-submodule-update` e salva o artefato resultante na pasta `dist/desire_lines-<versão>.zip`.
3. **Filtros de Exportação**: O arquivo `.gitattributes` utiliza a diretiva `export-ignore` para garantir que arquivos de desenvolvimento (`docs/`, `test/`, `examples/`, `Makefile`, etc.) fiquem de fora do pacote de produção.
4. **Nome do Pacote**: O diretório raiz dentro do arquivo ZIP publicado **deve obrigatoriamente se chamar `desire_lines`**, batendo exatamente com o id cadastrado em `plugins.qgis.org`.

---

## 5. Registro Condensado das Decisões de Arquitetura (D1–D11)

As decisões de arquitetura a seguir orientaram o desenvolvimento do módulo de alocação de tráfego em rodovias (`desire_lines/traffic/`):

- **D1 — HCM-CALC é referência, não dependência**: O HCM-CALC é um aplicativo Windows sem licença livre declarada; os algoritmos do HCM foram reimplementados em Python puro e os exemplos do HCM-CALC são usados apenas como referência nos testes unitários.
- **D2 — Escopo HCM rodoviário restrito ao SNV/DER**: Cobre trechos de pista simples (HCM cap. 15) e pista dupla/multilane/freeway (cap. 12); exclui interseções semaforizadas e cruzamentos urbanos devido à ausência desses dados na base rodoviária oficial.
- **D3 — LOS por faixas de `v/c` (aproximação declarada)**: O Nível de Serviço (LOS de A a F) é determinado por faixas da razão volume/capacidade (`v/c`) para diagnóstico rápido de gargalos, já que a base nacional não fornece a densidade exata do HCM.
- **D4 — Grafo próprio em Python (`heapq`), não `QgsGraph`**: O `QgsGraph` cria arestas por segmento geométrico sem vínculo com os links da feição, o que impediria recalcular o custo do link a cada iteração do MSA; o grafo próprio em Python resolve isso e suporta malhas de até ~50.000 arcos.
- **D5 — Arcos direcionados (um por sentido)**: Cada trecho rodoviário é representado por dois arcos direcionados independentes (A→B e B→A, com geometrias invertidas), permitindo fluxos, capacidades e custos direcionais.
- **D6 — GISBR como dependência com checagem em runtime**: Declara `plugin_dependencies=GisBR` no `metadata.txt`, mas faz a verificação em runtime em `gisbr_bridge.py` para desabilitar suavemente a aba 4 se o plugin GISBR não estiver instalado no QGIS.
- **D7 — Parâmetros HCM com proveniência e padrões documentados**: Aplica a hierarquia (campo oficial → padrão documentado → sobrescrita do usuário) e grava a origem de cada parâmetro nos campos `src_*` para total auditabilidade.
- **D8 — Código em subpacote isolado `traffic/`**: Lógica de alocação e cálculo de capacidade concentrada em `desire_lines/traffic/` sem dependência de widgets de interface gráfica, facilitando testes e manutenção.
- **D9 — Botões de ação separados (Calcular capacidade vs. Alocar)**: Permite que a capacidade operacional HCM seja calculada e inspecionada na tabela de atributos antes de rodar os algoritmos de alocação.
- **D10 — AoN exposto como método de primeira classe**: O método All-or-Nothing (AoN) é exposto ao usuário como opção de primeira classe para análises preliminares em redes grandes, além de ser a etapa base de cada iteração do MSA.
- **D11 — Travessias urbanas sinalizadas (`escopo='urbano'`)**: Trechos urbanos na malha rodoviária não são removidos, mas recebem a capacidade rodoviária como aproximação declarada e são marcados como `escopo='urbano'` para alerta no log e no mapa.
