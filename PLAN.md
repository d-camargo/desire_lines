# PLAN — Desire Lines (compatibilidade QGIS LTR + versão de desenvolvimento)

## Objetivo
Garantir que o plugin QGIS "Desire Lines" continue funcionando tanto na
versão **LTR** do QGIS (hoje instalada localmente: `3.34.4`, roda sobre
**PyQt5/Qt5**) quanto numa **versão de desenvolvimento** do QGIS (branch
master/nightly, que já roda ou está migrando para **PyQt6/Qt6** — a mudança
de binding Qt é o fator de quebra real entre as duas linhas). O plugin deve
carregar sem erro e as três abas (Origin/Destination Matrix, Desire Lines,
AoN Delaunay) devem funcionar do mesmo jeito nas duas versões, sem regressão
na LTR.

## Decisões de arquitetura
- **`qgis.PyQt` já é o mecanismo de compatibilidade certo** e já é usado em
  todo o código-fonte (`desirelines.py`, `desirelines_dialog.py`, `aon.py`):
  ele resolve para PyQt5 ou PyQt6 conforme o binding real do QGIS em
  execução. Nenhuma mudança é necessária nesses imports — o problema está
  em um único arquivo que **não** usa esse shim.
- **Causa raiz identificada**: `resources.py` (gerado por `pyrcc5` a partir
  de `resources.qrc`, e **versionado em git** — diferente dos `.qm` de
  tradução) tem a linha fixa `from PyQt5 import QtCore`. Numa build de
  desenvolvimento do QGIS rodando sobre PyQt6, o pacote `PyQt5` tipicamente
  nem está instalado → `ModuleNotFoundError` ao importar o módulo →
  `desirelines.py:31 from . import resources` falha → **o plugin inteiro
  não carrega**. Esse é o ponto de quebra concreto, não uma suposição.
  - Correção mais simples: trocar essa única linha para
    `from qgis.PyQt import QtCore`. O restante do arquivo (`qt_resource_data`,
    `qt_resource_name`, `qt_resource_struct_v1/v2`, `qInitResources`) é
    dado binário de recurso Qt e a API `qRegisterResourceData` — ambos
    inalterados entre Qt5 e Qt6, então não há necessidade de recompilar com
    `pyrcc6` nem de abandonar o sistema de recursos Qt (trocar por
    carregamento de ícone via caminho de arquivo seria uma refatoração
    maior que o necessário para o problema real — YAGNI).
  - A regra do `Makefile` que regenera `resources.py` (`pyrcc5 -o $*.py $<`)
    precisa do mesmo ajuste (via `sed` logo após o `pyrcc5`), senão rodar
    `make compile` de novo reintroduz o import fixo em PyQt5.
- **Segundo ponto de risco, menor**: `aon.py` cria campos com
  `QgsField('flow', QVariant.Double)` (3 ocorrências). `QVariant::Type` foi
  removido da API do Qt6 (não é escolha do QGIS, é mudança do próprio Qt) —
  em PyQt6 esse atributo pode simplesmente não existir. O caminho
  recomendado pelo PyQGIS moderno é `QMetaType.Type.Double`. Como não há
  neste ambiente uma build de desenvolvimento do QGIS para confirmar ao
  vivo qual grafia exata (`QMetaType.Type.Double` vs `QMetaType.Double`)
  funciona em qual binding, a solução mais simples e segura é um helper
  pequeno com fallback em cadeia (tenta `QMetaType`, cai para
  `QVariant.Double` se `ImportError`/`AttributeError`) — **confirmando
  empiricamente no console Python do QGIS local (3.34.4)** qual grafia
  responde antes de fixar a ordem do fallback, em vez de adivinhar.
- **Não vamos mudar `qgisMinimumVersion`/`qgisMaximumVersion`**
  (`metadata.txt`, `metadados.txt`): o plugin já é declarado compatível com
  qualquer `3.x`; não é objetivo deste trabalho travar ou anunciar suporte
  à versão de desenvolvimento no `metadata.txt`, só fazer o código não
  quebrar nela.
- **Validação cruzada real (rodar de fato numa build "dev") não é
  automatizável neste ambiente**: só há QGIS `3.34.4` (LTR) instalado
  localmente e não há Docker disponível na máquina. Por isso o passo final
  é QA manual, no mesmo espírito do passo de QA manual do PLAN anterior
  (i18n), usando uma instalação separada de uma versão de desenvolvimento
  do QGIS (nightly/master, canal dev do OSGeo4W, flatpak `org.qgis.qgis3//latest`,
  ou imagem `qgis/qgis:latest` em outra máquina com Docker).

## Passos (executor marca [x] ao concluir)
- [x] 1. Trocar em `resources.py` a linha `from PyQt5 import QtCore` por
      `from qgis.PyQt import QtCore`. — arquivos: `resources.py`
      Verificação: `grep -n "PyQt5" resources.py` não retorna nada;
      `grep -n "from qgis.PyQt import QtCore" resources.py` encontra a
      linha; `pytest test/test_resources.py` continua passando no QGIS
      LTR local.

- [x] 2. Ajustar a regra de geração de `resources.py` no `Makefile`
      (`%.py : %.qrc $(RESOURCES_SRC)`) para, logo após o `pyrcc5`, rodar
      um `sed -i` trocando `from PyQt5 import QtCore` por
      `from qgis.PyQt import QtCore` — para que regenerar o arquivo
      (`make compile`) não reintroduza o import fixo. — arquivos: `Makefile`
      Verificação: `rm resources.py && make compile` produz um
      `resources.py` que já nasce com `from qgis.PyQt import QtCore` (sem
      precisar do passo 1 manualmente).

- [x] 3. No console Python do QGIS LTR local (3.34.4), confirmar
      interativamente qual grafia de `QMetaType` funciona para criar um
      `QgsField` double (`from qgis.PyQt.QtCore import QMetaType` +
      `QMetaType.Type.Double` e/ou `QMetaType.Double`), e então em
      `aon.py` extrair a criação dos 3 `QgsField(..., QVariant.Double)`
      para uma função helper (ex.: `_double_field(name)`) que tenta a(s)
      grafia(s) de `QMetaType` confirmada(s) e cai para `QVariant.Double`
      em `ImportError`/`AttributeError`. — arquivos: `aon.py`
      Verificação: `pytest test/test_aon.py` continua passando no QGIS LTR
      local.

- [x] 4. Rodar a suíte completa (`pytest test/`) no QGIS LTR local
      (3.34.4) para confirmar que nada regrediu com os passos 1–3. —
      arquivos: nenhum
      Verificação: `pytest test/` verde.

- [ ] 5. QA manual numa build de **desenvolvimento** do QGIS (nightly/
      master, tipicamente PyQt6/Qt6): instalar o plugin lá (zip via
      `make deploy` / `pb_tool zip`), verificar no log de mensagens/log
      Python que ele carrega **sem** `ModuleNotFoundError` nem outra
      exceção, que o ícone aparece no menu/barra de ferramentas, e repetir
      o fluxo das três abas (Read CSV → Add Centroids → Desire Lines →
      Allocate AoN). Repetir o mesmo roteiro na LTR local (3.34.4) para
      confirmar ausência de regressão. — arquivos: nenhum (validação
      funcional)
      Verificação: checklist manual, um por versão do QGIS, sem erros no
      log e com as três abas funcionando nas duas versões.

- [ ] 6. Se o passo 5 revelar quebras adicionais de API na versão dev
      (avisos de depreciação virando erro, mudança de assinatura em
      `qgis.core`/`qgis.analysis` usada por `aon.py` ou
      `desirelines_dialog.py`), registrar cada uma como um novo passo
      neste PLAN, com o erro reproduzido, antes de corrigir — não
      adivinhar/corrigir preventivamente sem reproduzir. — arquivos: a
      definir conforme achado
      Verificação: cada nova quebra encontrada vira um passo com sua
      própria verificação.

## Critério de aceite
- `resources.py` não importa `PyQt5` diretamente em nenhum lugar; usa
  `qgis.PyQt`, e regenerar via `make compile` preserva isso.
- `aon.py` cria os campos `flow`/`flow_ab`/`flow_ba` sem depender de
  `QVariant.Double` existir como único caminho possível — há fallback via
  `QMetaType` confirmado empiricamente contra o QGIS LTR local.
- `pytest test/` passa integralmente no QGIS LTR local (3.34.4).
- QA manual confirma que o plugin carrega e as três abas funcionam tanto na
  LTR instalada quanto numa build de desenvolvimento do QGIS, sem
  `ModuleNotFoundError` nem outras exceções no log.
- Nenhuma mudança em `qgisMinimumVersion`/`qgisMaximumVersion`.
