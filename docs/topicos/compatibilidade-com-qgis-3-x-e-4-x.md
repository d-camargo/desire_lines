# Tópico: compatibilidade-com-qgis-3-x-e-4-x
_Memória deste tópico. O orquestrador lê isto no início de toda conversa._
Atualizado: 2026-07-13 · HEAD: 46f2d68

## Objetivo
Plugin "Desire Lines" rodar a partir do **mesmo código-fonte** (sem branch
nem zip separado) tanto em QGIS 3.x/PyQt5/Qt5 quanto em QGIS 4.x/PyQt6/Qt6.

## Estado atual (o que JÁ está feito e verificado)
- PLAN.md com os 9 passos, todos marcados `[x]`. Confirmado no código (não só no checklist):
  - `resources.py` e `resources.qrc` não existem mais no repo (removidos).
  - Nenhuma ocorrência de `Qt.WaitCursor`, `.exec_()`, `QDialogButtonBox.Ok/.Cancel`
    ou `QDialog.Accepted/.Rejected` (não escopados) em nenhum `.py` do projeto.
  - `plugin_upload.py` sem `standard_library.install_aliases()` morto.
  - `metadata.txt`: `qgisMinimumVersion=3.0` (sem máximo), `version=0.2.0` — inalterado, como planejado.
- Commit `4068130` (mensagem do próprio commit, não verificado por mim rodando o gate agora):
  "Gate verde nos dois ambientes: Qt5 (QGIS 3.44) e Qt6 (QGIS 4.2) — suite 13
  passed e smoke 6/6 módulos em ambos. Review do Opus: APROVADO."
- Depois disso: commit `46f2d68` só rebuild do pacote `dist/desirelines-0.2.0.zip` (binário, sem mudança de código).

## Decisões tomadas
- Sem módulo `core/qgis_compat.py` genérico (padrão usado no projeto irmão
  `gisbr`) — YAGNI aqui, o único caso de type-branching (`QVariant` vs
  `QMetaType` em `aon.py::_double_field`) já era resolvido e local.
- Ícone: abandonado sistema de recurso Qt compilado (`pyrcc5`), carregado por
  caminho de arquivo (`os.path.join(os.path.dirname(__file__), 'icon.png')`).
- Enums Qt sempre na forma escopada (`Qt.CursorShape.WaitCursor`, etc.) —
  funciona idêntico em Qt5 e Qt6, sem necessidade de fallback/try-except.
- Enums nativos do QGIS (`QgsMapLayerProxyModel.PointLayer` etc.) **não**
  foram escopados — sip do QGIS não exige isso, e não devem ser mexidos.
- `qgisMinimumVersion`/`qgisMaximumVersion` mantidos como estavam.

## Pendências / próximo passo
- Nenhuma pendência conhecida no PLAN — todos os 9 passos estão `[x]` e o
  código bate com o que o plano pedia.
- Não verificado nesta sessão: rodar o gate (`planexec.py test ... both`) de
  novo para reconfirmar ao vivo — a evidência de "verde" vem da mensagem do
  commit `4068130`, não de execução própria agora.

## Armadilhas (o que já deu errado aqui — pra não repetir)
- Testar Qt6 "no papel" sem container é furada: o PLAN anterior (pré-VPS com
  containers) só tinha QA manual e não pegou nenhum dos 4 bugs reais.
- `resources.py` gerado por `pyrcc5` falha **silenciosamente** em Qt6 (não dá
  exceção no import, só `QIcon(...).isNull() == True` em runtime) — smoke
  test de import sozinho não pega isso, precisa exercitar o ícone de verdade.
- `plugin_upload.py` com `NameError` de `standard_library` quebrava o smoke
  nos DOIS ambientes (Qt5 e Qt6) — não é bug de compat Qt, é resíduo de
  template QGIS2/`python-future` nunca migrado. Fácil confundir com bug de Qt6.
