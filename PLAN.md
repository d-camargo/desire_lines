# PLAN — Desire Lines (Qt6 enum-scoping: 20 erros do QGIS Plugin Repository)

## Objetivo
Corrigir os 20 erros "Enum error, add '<Enum>' before '<Membro>'" reportados
pelo checker automático de compatibilidade Qt6 do QGIS Plugin Repository
(verificação de 2026-07-13 19:06 GMT-3) em `desirelines.py`,
`desirelines_dialog.py` e `aon.py`, escopando cada enum exatamente como o
relatório indica, sem quebrar o comportamento já testado e aprovado em
QGIS 3.44 (Qt5) e QGIS 4.2 (Qt6).

Este PLAN substitui o anterior (ajuste de `qgisMaximumVersion`/changelog em
`metadata.txt`), que já está superado: `metadata.txt` hoje já tem
`qgisMaximumVersion=4.99` e `version=0.3.1` (commits `86f84b9`/`3aa7e1a`,
posteriores àquele plano). Este é um problema novo e não relacionado.

## Decisões de arquitetura

- **Isto reverte uma decisão anterior registrada em
  `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`**: aquele documento
  afirma "Enums nativos do QGIS (`QgsMapLayerProxyModel.PointLayer` etc.)
  não foram escopados — sip do QGIS não exige isso, e não devem ser
  mexidos." Isso continua verdadeiro em **runtime** (os containers QGIS
  3.44/4.2 aceitam a forma não-escopada), mas o checker do QGIS Plugin
  Repository trata a forma não-escopada como **erro de compatibilidade
  Qt6** independente do runtime aceitar — provavelmente porque o
  repositório está validando contra uma política de estilo/forward-compat,
  não contra um teste de execução real. Como o objetivo agora é passar
  nesse checker (é o gate que está bloqueando o plugin), escopar os 20
  enums é necessário, mesmo sem quebra funcional aparente hoje.
- **Aplicar exatamente o prefixo que o relatório indica** para cada
  ocorrência — o relatório já diz qual enum aninhado usar, não é preciso
  adivinhar:
  - `QgsMapLayerProxyModel.<X>` → `QgsMapLayerProxyModel.Filter.<X>`
    (`PointLayer`, `NoGeometry`, `PolygonLayer`)
  - `QgsFieldProxyModel.<X>` → `QgsFieldProxyModel.Filter.<X>` (`Int`,
    `Double`)
  - `QgsFileWidget.SaveFile` → `QgsFileWidget.StorageMode.SaveFile`
  - `Qgis.Info` → `Qgis.MessageLevel.Info`
  - `QgsGraduatedSymbolRenderer.Jenks` → `QgsGraduatedSymbolRenderer.Mode.Jenks`
  - `QgsGraduatedSymbolRenderer.GraduatedSize` →
    `QgsGraduatedSymbolRenderer.GraduatedMethod.GraduatedSize`
  - `QgsVectorFileWriter.CreateOrOverwriteLayer` →
    `QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer`
  - `QgsVectorLayerDirector.DirectionBoth` →
    `QgsVectorLayerDirector.Direction.DirectionBoth`
  - `QMetaType.Double` (em `aon.py:253`) → `QMetaType.Type.Double`
- **Caso especial — `aon.py:253`**: essa linha é o `except` interno de
  `_double_field()`, um fallback deliberado para quando
  `QMetaType.Type.Double` (linha 251, já escopado) falha com
  `AttributeError`/`TypeError`. Escopar a linha 253 do mesmo jeito que a
  251 torna as duas linhas idênticas, ou seja, o `except` interno vira
  código morto (se a tentativa escopada falha, a "alternativa" escopada
  igual falha do mesmo jeito). **Não decidir isso às cegas agora** — o
  passo correspondente deve confirmar, rodando nos dois containers, se
  `QMetaType.Type` está sempre disponível no range suportado
  (`qgisMinimumVersion=3.0`); só então simplificar removendo o
  `try/except` interno redundante (mantendo o `except` externo que cai
  para `QVariant.Double`, que continua sendo a rede de segurança real para
  bindings antigos sem `QMetaType`).
- Sem módulo de compat genérico novo (`core/qgis_compat.py`) — mantém a
  decisão já tomada (YAGNI): o único ponto de type-branching real
  (`_double_field`) já é local e pequeno.
- Não mexer em `qgisMinimumVersion`/`qgisMaximumVersion` — fora de escopo,
  esse problema é só sobre uso de enum não-escopado no código Python.

## Passos (executor marca [x] ao concluir)

- [x] 1. Ler `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md` por
      inteiro e confirmar que ele registra a decisão antiga (não escopar
      enums nativos do QGIS) que este PLAN está revertendo — checagem, sem
      edição neste passo. — arquivos: `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`
      Verificação: trecho "não devem ser mexidos" (ou equivalente) presente
      no arquivo.

- [x] 2. Em `desirelines.py`, escopar as 12 ocorrências nas linhas 194,
      195, 198, 201, 202, 203, 204, 207, 208, 209, 210, 211, 212, trocando
      `QgsMapLayerProxyModel.<X>` por `QgsMapLayerProxyModel.Filter.<X>` e
      `QgsFieldProxyModel.<X>` por `QgsFieldProxyModel.Filter.<X>`. —
      arquivos: `desirelines.py`
      Verificação: `grep -nE "QgsMapLayerProxyModel\.(PointLayer|NoGeometry|PolygonLayer)\b" desirelines.py`
      e `grep -nE "QgsFieldProxyModel\.(Int|Double)\b" desirelines.py` (sem
      `.Filter.` antes do membro) não retornam nada.

- [x] 3. Em `desirelines_dialog.py:81`, trocar `QgsFileWidget.SaveFile` por
      `QgsFileWidget.StorageMode.SaveFile`. — arquivos:
      `desirelines_dialog.py`
      Verificação: `grep -n "QgsFileWidget.StorageMode.SaveFile" desirelines_dialog.py`
      retorna a linha 81.

- [x] 4. Em `desirelines_dialog.py:351`, trocar `Qgis.Info` por
      `Qgis.MessageLevel.Info`. — arquivos: `desirelines_dialog.py`
      Verificação: `grep -n "Qgis.MessageLevel.Info" desirelines_dialog.py`
      retorna a linha 351.

- [x] 5. Em `desirelines_dialog.py:374` e `:377`, trocar
      `QgsGraduatedSymbolRenderer.Jenks` por
      `QgsGraduatedSymbolRenderer.Mode.Jenks` e
      `QgsGraduatedSymbolRenderer.GraduatedSize` por
      `QgsGraduatedSymbolRenderer.GraduatedMethod.GraduatedSize`. —
      arquivos: `desirelines_dialog.py`
      Verificação: `grep -n "GraduatedSymbolRenderer.Mode.Jenks\|GraduatedSymbolRenderer.GraduatedMethod.GraduatedSize" desirelines_dialog.py`
      retorna as duas linhas.

- [x] 6. Em `desirelines_dialog.py:560`, trocar
      `QgsVectorFileWriter.CreateOrOverwriteLayer` por
      `QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer`. —
      arquivos: `desirelines_dialog.py`
      Verificação: `grep -n "ActionOnExistingFile.CreateOrOverwriteLayer" desirelines_dialog.py`
      retorna a linha 560.

- [x] 7. Em `aon.py:185`, trocar `QgsVectorLayerDirector.DirectionBoth` por
      `QgsVectorLayerDirector.Direction.DirectionBoth`. — arquivos:
      `aon.py`
      Verificação: `grep -n "QgsVectorLayerDirector.Direction.DirectionBoth" aon.py`
      retorna a linha 185.

- [x] 8. Em `aon.py::_double_field` (linha 253), decidir com base em
      evidência (não achismo): rodar/inspecionar se `QMetaType.Type` está
      disponível em ambos os containers de teste (QGIS 3.44/Qt5 e QGIS
      4.2/Qt6). Se sim nos dois, simplificar a função removendo o
      `try/except (AttributeError, TypeError)` interno redundante,
      deixando só `QgsField(name, QMetaType.Type.Double)` dentro do
      `try` externo que cai para `QVariant.Double`. Se algum ambiente
      testado realmente não tiver `QMetaType.Type`, manter a linha 253 tal
      qual está (não-escopada, com uma linha de comentário curta
      explicando por quê) e documentar essa exceção deliberada — não
      "corrigir" às cegas só para calar o checker. — arquivos: `aon.py`
      Verificação: `_double_field` continua retornando um `QgsField` do
      tipo double nos dois containers (coberto pelo passo 10); código sem
      branch morto (duas tentativas idênticas em sequência).

- [x] 9. Rodar uma varredura final cobrindo os 20 itens do relatório do
      QGIS Plugin Repository, confirmando que nenhuma forma não-escopada
      resta (exceto a exceção documentada do passo 8, se aplicável). —
      arquivos: `desirelines.py`, `desirelines_dialog.py`, `aon.py`
      Verificação: repetir os greps dos passos 2-7 de uma vez; nenhum
      retorna ocorrência não-escopada além da eventual exceção do passo 8.

- [x] 10. Rodar o gate de teste nos dois containers QGIS (comando já
      documentado na memória do projeto: `python3
      /home/diego/.hermes/skills/planexec/scripts/planexec.py test
      desire-lines both`) e confirmar suíte + smoke verdes em QGIS 3.44
      (Qt5) e QGIS 4.2 (Qt6) após o escopamento dos enums. — arquivos: n/a
      (execução)
      Verificação: saída do comando mostra suíte e smoke passando (mesmo
      padrão "gate verde" já usado neste projeto) nos dois ambientes.

- [x] 11. Atualizar `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`,
      corrigindo a linha "Enums nativos do QGIS... não foram escopados...
      e não devem ser mexidos" para refletir o novo estado (agora
      escopados, motivado pelo checker do QGIS Plugin Repository, não por
      quebra de runtime) e registrando a data/decisão. — arquivos:
      `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`
      Verificação: o arquivo não contém mais a afirmação antiga sem
      ressalva; menciona os 20 erros corrigidos e a razão (checker do
      repositório, não falha em runtime).

- [x] 12. Bump de versão em `metadata.txt` (padrão já usado: `version=`
      + nova entrada em `changelog=` acima da mais recente) documentando o
      fix de enum-scoping Qt6, para gerar um novo zip a submeter ao QGIS
      Plugin Repository. — arquivos: `metadata.txt`
      Verificação: `grep -n "version="  metadata.txt` mostra a versão
      incrementada (ex.: `0.3.2`), e o bloco `changelog=` tem uma entrada
      nova citando a correção dos enums Qt6.

## Critério de aceite
- Nenhuma das 20 ocorrências apontadas pelo relatório do QGIS Plugin
  Repository continua sem escopo em `desirelines.py`,
  `desirelines_dialog.py` e `aon.py` (exceto uma eventual exceção
  documentada e justificada no passo 8).
- Gate de teste (suíte + smoke) verde em QGIS 3.44 (Qt5) **e** QGIS 4.2
  (Qt6) depois da mudança.
- `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md` não contradiz mais o
  código (reflete que os enums nativos do QGIS agora são escopados).
- `metadata.txt` tem uma versão nova com changelog descrevendo o fix, pronta
  para reempacotar e reenviar ao QGIS Plugin Repository.
- Nenhum comportamento funcional do plugin muda (mesmos filtros de
  camada/campo, mesmo estilo graduado, mesma lógica de roteamento AoN) —
  só a forma de referenciar os enums.
