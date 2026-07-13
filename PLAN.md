# PLAN — Desire Lines (compatibilidade QGIS 3.x/Qt5 e 4.x/Qt6, codebase único)

## Objetivo
Fazer o plugin QGIS "Desire Lines" carregar e funcionar, a partir do
**mesmo código-fonte** (sem branch nem zip separado), tanto em QGIS 3.x
sobre **PyQt5/Qt5** quanto em QGIS 4.x sobre **PyQt6/Qt6**. Critério de
pronto = gate automatizado verde nos dois ambientes:
`python3 /home/diego/.hermes/skills/planexec/scripts/planexec.py test /home/diego/projects/desire-lines both`.

Este PLAN substitui o anterior (mesmo arquivo, tópico
`compatibilidade-com-qgis-3-x-e-4-x`), que tinha sido escrito **sem** poder
testar de fato contra Qt6 (não havia QGIS dev nem Docker/Podman
disponíveis — só QA manual era possível). Agora a VPS tem os dois
ambientes reais em container (`docker.io/qgis/qgis:3.44` = Qt5,
`docker.io/qgis/qgis:4.2.0` = Qt6), então este PLAN é baseado em falhas
**reproduzidas de verdade**, não em suposição.

## Decisões de arquitetura

- **Estado herdado do PLAN anterior, reconfirmado válido e mantido como
  está** (não mexer, já funciona nos dois ambientes):
  - `resources.py` já importa `from qgis.PyQt import QtCore` (não mais
    `from PyQt5 import QtCore`), e a regra `%.py : %.qrc` do `Makefile` já
    tem o `sed -i` que preserva isso ao regenerar via `make compile`.
  - `aon.py` já tem um helper `_double_field(name)` (usado nas 3 chamadas
    que criam campo double) que tenta `QMetaType.Type.Double`, cai para
    `QMetaType.Double`, e por fim `QVariant.Double` — confirmado passando
    em `test/test_aon.py` tanto em Qt5 quanto em Qt6 na suíte containerizada
    já rodada. **Nenhuma mudança necessária aqui.**
  - Por causa disso, **não vamos criar um módulo `core/qgis_compat.py`
    genérico** só para replicar o padrão do gisbr: o único caso real de
    "branching" (QVariant vs QMetaType) já está resolvido e concentrado em
    um único helper. Os outros bugs achados abaixo não são resolvidos por
    um helper de tipos — são reescopo de enum ou remoção de sistema de
    recurso — então um módulo de compat adicional seria abstração sem uso
    real (YAGNI). Se um terceiro ponto do código precisar do mesmo tipo de
    fallback no futuro, aí sim extrair.

- **4 causas raiz novas, cada uma confirmada rodando no container real**
  (não suposição):

  1. **`plugin_upload.py` quebra o smoke nos DOIS ambientes** (Qt5 e Qt6
     igualmente — não é um bug de compatibilidade Qt, é resíduo do
     template QGIS2/`python-future`): linha 13 chama
     `standard_library.install_aliases()` sem nunca importar
     `standard_library` (o `from future import standard_library` original
     foi removido/nunca migrado). O resto do arquivo já é Python 3 puro e
     funcional (usa `xmlrpc.client` diretamente) e é o script usado por
     `make upload`. **Decisão**: apagar só a linha morta, não o arquivo —
     apagar o arquivo inteiro tiraria a única forma de publicar o plugin
     via `make upload`, e o resto do arquivo não tem nenhum outro problema
     de Python 2/3 ou de Qt5/Qt6 (ele nem importa Qt). Apagar uma linha
     morta é estritamente mais simples e não perde funcionalidade.

  2. **Ícone não carrega em Qt6** (`test_resources.py::test_icon_png`
     falha: `icon.isNull()` é `True`). Causa: `resources.py` foi gerado
     por `pyrcc5` (formato binário de recurso Qt versão 1/2, hardcoded nas
     variáveis `qt_resource_struct_v1/v2`); esse formato não é reconhecido
     pelo motor de recursos do Qt6 — o import não quebra (por isso o smoke
     "passa" para esse módulo), mas o recurso registrado não é encontrado
     em runtime, então `QIcon(':/plugins/desirelines/icon.png')` volta
     nulo. **Decisão**: não manter dois builds (`pyrcc5` + `pyrcc6`) — é
     exatamente esse tipo de duplicação que o pedido do usuário quer
     evitar ("um único codebase"). Em vez disso, abandonar o sistema de
     recurso Qt compilado para o ícone e carregar `icon.png` por caminho
     de arquivo relativo ao plugin (`os.path.join(os.path.dirname(__file__), 'icon.png')`),
     igual ao que o `gisbr` já faz em `provider.py` (que não tem
     `resources.py`/`resources.qrc` nenhum e passa 55/55 em Qt5 e Qt6).
     Confirmado que nada mais no projeto depende do prefixo de recurso
     `:/plugins/...` (o `.ui` referencia `icon.png` direto, sem
     `<resources>`, e `metadata.txt`/`EXTRAS` do Makefile já copiam
     `icon.png` cru para o diretório de deploy). Consequência: apagar
     `resources.py`, `resources.qrc` e toda a plumbing de compilação
     (`COMPILED_RESOURCE_FILES`, regra `%.py : %.qrc`, `RESOURCE_SRC`,
     entrada no `PEP8EXCLUDE`, entrada no `clean:`, `resource_files:` do
     `pb_tool.cfg`) — não deixar código morto de geração para um sistema
     que não é mais usado.

  3. **`Qt.WaitCursor` (não escopado) não existe em PyQt6** — confirmado
     rodando `from qgis.PyQt.QtCore import Qt; Qt.WaitCursor` no container
     Qt6 (`AttributeError`). Usado em produção em `desirelines_dialog.py`
     (2 ocorrências, linhas ~324 e ~516) — bug real, ainda não pego pela
     suíte atual porque os testes de diálogo falham antes de alcançar esse
     caminho de código (ver item 4), mas quebraria em uso real assim que o
     usuário rodar qualquer operação longa (Read CSV/Add
     Centroids/Allocate) no QGIS 4.x. **Decisão**: trocar para
     `Qt.CursorShape.WaitCursor` — confirmado que essa forma escopada
     funciona **idêntica** em Qt5 e Qt6 (testado nos dois containers), ou
     seja, não precisa de fallback/try-except, só escopar o enum.
     Da mesma família: `self.dlg.exec_()` em `desirelines.py` (linha
     ~218) — `exec_` (com underscore) **não existe mais** em `QDialog` no
     PyQt6 (confirmado: `hasattr(d, 'exec_')` é `False` em Qt6, `True` em
     Qt5; `exec` sem underscore existe nos dois). Trocar para
     `self.dlg.exec()`.
     As classes próprias do QGIS (`QgsMapLayerProxyModel.PointLayer`,
     `QgsFieldProxyModel.Int/.Double`, etc., usadas mais abaixo no mesmo
     método) foram checadas e **continuam funcionando sem escopo** em
     Qt6 — o binding sip do QGIS para seus próprios enums não segue a
     mesma regra estrita do PyQt6 puro. Não mexer nelas.

  4. **Enums não escopados nos testes de diálogo** —
     `test/test_desirelines_dialog.py` usa `QDialogButtonBox.Ok`,
     `QDialogButtonBox.Cancel`, `QDialog.Accepted`, `QDialog.Rejected`
     (todos não escopados), que não existem mais como atributo direto da
     classe em PyQt6 (confirmado via `AttributeError` no container Qt6).
     Trocar para `QDialogButtonBox.StandardButton.Ok`/`.Cancel` e
     `QDialog.DialogCode.Accepted`/`.Rejected` — confirmado que essas
     formas escopadas funcionam idênticas em Qt5 e Qt6.

- **Não vamos mudar `qgisMinimumVersion`/`qgisMaximumVersion`** em
  `metadata.txt`/`metadados.txt` (`qgisMinimumVersion=3.0`, sem máximo) —
  mantém-se assim; o objetivo é o código não quebrar em 4.x, não anunciar
  suporte restrito.

## Passos (executor marca [x] ao concluir)

- [x] 1. `resources.py` importa via `qgis.PyQt` (não `PyQt5` direto) e a
      regra de `make compile` no `Makefile` preserva isso. — arquivos:
      `resources.py`, `Makefile`
      Verificação: já confirmado, herdado do PLAN anterior.

- [x] 2. `aon.py` cria os 3 campos double via helper `_double_field` com
      fallback `QMetaType.Type.Double` → `QMetaType.Double` →
      `QVariant.Double`. — arquivos: `aon.py`
      Verificação: já confirmado — `test/test_aon.py` passa em Qt5 **e**
      Qt6 na suíte containerizada.

- [x] 3. Remover a linha morta `standard_library.install_aliases()` de
      `plugin_upload.py` (linha 13), sem apagar o arquivo. — arquivos:
      `plugin_upload.py`
      Verificação: `python3 -c "import ast; ast.parse(open('plugin_upload.py').read())"`
      não quebra; rodar o smoke do gate
      (`planexec.py test ... qgis3` e `... qgis4`) mostra
      `ok    plugin_upload.py` nos dois, em vez de `FALHA ... NameError`.

- [x] 4. Trocar o carregamento do ícone do menu/toolbar de recurso Qt
      compilado para caminho de arquivo: em `desirelines.py`, remover
      `from . import resources` (linha ~31) e trocar
      `icon_path = ':/plugins/desirelines/icon.png'` (linha ~167) por um
      caminho absoluto resolvido a partir de `__file__`
      (`os.path.join(os.path.dirname(__file__), 'icon.png')`). —
      arquivos: `desirelines.py`
      Verificação: `python3 -c "import ast; ast.parse(open('desirelines.py').read())"`
      não quebra; `grep -n "import resources\|:/plugins" desirelines.py`
      não retorna nada.

- [x] 5. Apagar o sistema de recurso Qt compilado, agora sem uso: arquivos
      `resources.py` e `resources.qrc`; no `Makefile` remover
      `COMPILED_RESOURCE_FILES`, a regra `%.py : %.qrc $(RESOURCES_SRC)`,
      a variável `RESOURCE_SRC`, a entrada `resources.py` do
      `PEP8EXCLUDE`, a referência a `$(COMPILED_RESOURCE_FILES)` no alvo
      `deploy` e no alvo `clean`; no `pb_tool.cfg` remover/zerar
      `resource_files: resources.qrc`. — arquivos: `Makefile`,
      `pb_tool.cfg`, apagar `resources.py`, `resources.qrc`
      Verificação: `grep -rn "resources\.\(py\|qrc\)\|pyrcc" Makefile
      pb_tool.cfg` não retorna nada (fora comentários já removidos);
      `ls resources.py resources.qrc` falha (arquivos não existem).

- [x] 6. Atualizar `test/test_resources.py` para testar o carregamento do
      ícone por caminho de arquivo (mesma lógica de resolução do passo 4),
      em vez do caminho de recurso `:/plugins/...`. — arquivos:
      `test/test_resources.py`
      Verificação: o teste continua chamando `QIcon(...)` e
      `assertFalse(icon.isNull())`, só troca a origem do path.

- [x] 7. Escopar os enums Qt quebrados em produção: em
      `desirelines_dialog.py`, trocar as 2 ocorrências de `Qt.WaitCursor`
      por `Qt.CursorShape.WaitCursor`; em `desirelines.py`, trocar
      `self.dlg.exec_()` por `self.dlg.exec()`. — arquivos:
      `desirelines_dialog.py`, `desirelines.py`
      Verificação: `grep -n "Qt.WaitCursor\|\.exec_()" desirelines_dialog.py desirelines.py`
      não retorna nada.

- [x] 8. Escopar os enums Qt quebrados em `test/test_desirelines_dialog.py`:
      `QDialogButtonBox.Ok` → `QDialogButtonBox.StandardButton.Ok`;
      `QDialogButtonBox.Cancel` → `QDialogButtonBox.StandardButton.Cancel`;
      `QDialog.Accepted` → `QDialog.DialogCode.Accepted`;
      `QDialog.Rejected` → `QDialog.DialogCode.Rejected`. — arquivos:
      `test/test_desirelines_dialog.py`
      Verificação: os mesmos `grep` acima não retornam nada nesse arquivo.

- [x] 9. Rodar o gate completo nos dois ambientes e confirmar verde:
      `python3 /home/diego/.hermes/skills/planexec/scripts/planexec.py test /home/diego/projects/desire-lines both`.
      Se sobrar qualquer falha nova (não coberta pelos passos 3–8),
      registrar como passo adicional neste PLAN com o erro reproduzido
      antes de corrigir — não adivinhar. — arquivos: nenhum
      Verificação: saída termina em `✓ verde em: qgis3, qgis4`
      (`suite=OK smoke=OK` nos dois blocos).

## Critério de aceite
- `planexec.py test /home/diego/projects/desire-lines both` termina com
  `✓ verde em: qgis3, qgis4` — suíte pytest **e** smoke de import passam
  nos dois ambientes, a partir do mesmo código (sem branch nem zip
  separado).
- Nenhum módulo do plugin importa `PyQt5`/`resources.py` diretamente;
  `resources.py`/`resources.qrc` não existem mais no repo.
- Nenhum uso de enum Qt não escopado (`Qt.WaitCursor`, `QDialogButtonBox.Ok`,
  `QDialog.Accepted`, etc.) nem de `.exec_()` no código do plugin ou nos
  testes.
- `plugin_upload.py` importa sem `NameError` (smoke mostra `ok` para ele
  nos dois ambientes).
- `qgisMinimumVersion`/`qgisMaximumVersion` em `metadata.txt`/`metadados.txt`
  inalterados.
