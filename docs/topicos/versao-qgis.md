# Tópico: versao-qgis
_Memória deste tópico. O orquestrador lê isto no início de toda conversa._
Atualizado: 2026-07-13 · HEAD: e1a9217

## Objetivo
Fazer o plugin QGIS "Desire Lines" funcionar tanto no QGIS LTR local
(3.34.4, PyQt5/Qt5) quanto numa build de desenvolvimento do QGIS
(nightly/master, PyQt6/Qt6), sem regressão na LTR e sem mudar
`qgisMinimumVersion`/`qgisMaximumVersion`.

## Estado atual (o que JÁ está feito e verificado)
- Passo 1: `resources.py` não importa mais `PyQt5` direto — linha 9 é
  `from qgis.PyQt import QtCore`. Confirmado no arquivo.
- Passo 2: `Makefile` (regra `%.py : %.qrc`) roda `sed -i` após o `pyrcc5`
  trocando `from PyQt5 import QtCore` por `from qgis.PyQt import QtCore`
  (Makefile:93). Confirmado no arquivo.
- Passo 3: `aon.py` tem helper que cria `QgsField` double tentando
  `QMetaType.Type.Double` → `QMetaType.Double` → fallback `QVariant.Double`
  (aon.py:249-256). Confirmado no arquivo.
- Passo 4 (rodar `pytest test/` completo na LTR local): marcado [x] no
  PLAN.md, mas não executado por mim nesta sessão — não verificado
  diretamente, só a alegação no commit `6880b0d` ("passos 1-4 concluídos").
- Versão do plugin em `metadata.txt`: 0.2.0 (changelog já documenta a
  feature AoN Delaunay; nada no changelog menciona compat QGIS dev — como
  decidido, não deveria).

## Decisões tomadas
- Causa raiz da quebra em build dev/PyQt6: só `resources.py` importava
  `PyQt5` fixo; resto do código já usa o shim `qgis.PyQt`.
- Não mexer em `qgisMinimumVersion`/`qgisMaximumVersion` — plugin já
  declarado compatível com qualquer `3.x`.
- Fallback em cadeia para `QMetaType` em vez de escolher uma grafia única,
  porque não há QGIS dev instalado neste ambiente para confirmar ao vivo.

## Pendências / próximo passo
- Passo 5 (QA manual): instalar o plugin numa build de QGIS dev
  (nightly/master, tipicamente PyQt6/Qt6), confirmar carregamento sem
  `ModuleNotFoundError`, ícone aparece, e as 3 abas (Read CSV → Add
  Centroids → Desire Lines → Allocate AoN) funcionam. Repetir roteiro na
  LTR local para checar ausência de regressão. **Não automatizável neste
  ambiente**: só há QGIS 3.34.4 (LTR) local, sem Docker.
- Passo 6 (condicional): se o passo 5 revelar quebras de API adicionais,
  registrar cada uma como novo passo no PLAN.md com o erro reproduzido
  antes de corrigir — não adivinhar.

## Armadilhas (o que já deu errado aqui — pra não repetir)
- `resources.py` é gerado por `pyrcc5` e é versionado em git (diferente dos
  `.qm` de tradução) — regenerar via `make compile` sem o `sed` do passo 2
  reintroduz o import fixo em PyQt5.
- `QVariant.Type` foi removido do próprio Qt6 (não é escolha do QGIS) — não
  dá pra confirmar a grafia certa de `QMetaType` sem uma build QGIS/PyQt6
  real; por isso o fallback em cadeia em vez de fixar uma grafia.
