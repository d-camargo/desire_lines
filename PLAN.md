# PLAN — Desire Lines (suporte a PT-BR e EN)

## Objetivo
Fazer o plugin QGIS "Desire Lines" falar dois idiomas — Inglês (idioma-fonte,
já usado no código e no .ui) e Português do Brasil — usando o mecanismo
padrão de tradução do Qt (self.tr / arquivos .ts / .qm) que o Plugin Builder
já deixou parcialmente instalado. Ao trocar o locale do QGIS para
Português (Brasil), toda a interface do plugin (labels, tooltips, mensagens
da message bar, textos de progresso) deve aparecer em PT-BR; em qualquer
outro locale, deve continuar em Inglês (comportamento atual, inalterado).

## Decisões de arquitetura
- **Idioma-fonte = Inglês.** Não criamos `en.ts`: strings em inglês já são o
  texto-fonte no código/.ui e aparecem por padrão quando nenhum tradutor Qt
  está instalado. Só precisamos criar `i18n/pt.ts` → `i18n/pt.qm`.
- **Um único locale `pt`** (não `pt_BR` separado): `desirelines.py` já reduz
  `QSettings().value('locale/userLocale')` aos 2 primeiros caracteres antes
  de montar `DesireLines_{locale}.qm`, então `pt_BR` e `pt_PT` caem no mesmo
  arquivo `pt`. Isso já é a solução mais simples que funciona — não vamos
  criar variantes regionais.
- **Carregamento do .qm**: já existe em `desirelines.py` (`QTranslator` +
  `QCoreApplication.installTranslator`). Não precisa mudar — só precisa que
  `i18n/DesireLines_pt.qm` exista (gerado a partir de `i18n/pt.ts`).
- **Todo texto visível ao usuário deve passar por `self.tr(...)`.**
  - `desirelines.py`: já está 100% coberto — nenhuma ação necessária.
  - `desirelines_dialog.py`: herda de `QtWidgets.QDialog`, então já tem
    `self.tr()` disponível; hoje quase nenhuma string está envolvida — é o
    grosso do trabalho.
  - `desirelines_dialog_base.ui`: strings do Qt Designer já são
    traduzíveis automaticamente (uic gera `_translate(...)` no
    `setupUi`) — nenhuma ação de código necessária, só entram na extração.
  - Títulos de message bar `'Desire Lines'` (nome do plugin) **não** são
    traduzidos — é um nome próprio, convenção comum em plugins QGIS.
- **`aon.py` continua sem dependência de Qt/GUI** (é intencional, conforme
  seu próprio docstring, para permitir testes fora do QGIS). Hoje
  `pick_metric_crs` retorna uma frase pronta em inglês (`note`) que vai
  direto para a message bar sem tradução. Vamos trocar essa frase pronta por
  um pequeno dado estruturado (`{'code': ..., **params}`) e mover a
  montagem/traduação da frase final para `desirelines_dialog.py`, que é
  quem tem `self.tr()`. É o menor refactor possível para tornar o texto
  traduzível sem dar a `aon.py` uma dependência de Qt widgets.
- **Ferramental de tradução**: reaproveitar o que o Plugin Builder já deixou
  (`Makefile` alvos `transup`/`transcompile`, `scripts/update-strings.sh`,
  `scripts/compile-strings.sh`), só corrigindo o que está quebrado/vazio
  (`pylupdate4` inexistente em ambientes atuais, `LOCALES` vazio). Não vamos
  introduzir uma ferramenta nova (ex.: Transifex, Weblate) — YAGNI para um
  plugin com 2 idiomas.
- **`i18n/af.ts`** é sobra do template do Plugin Builder (Afrikaans, string
  de demonstração "Good morning"/"Goeie more", não relacionada ao plugin) —
  será removida. `test/test_translations.py` testa exatamente esse arquivo
  de demonstração; será reescrito para validar `i18n/pt.qm` com uma string
  real do plugin.
- Arquivos `.qm` compilados **não** são versionados (já estão no
  `.gitignore`) — são artefato de build, gerados por `make transcompile` /
  `pb_tool compile`. Só o `.ts` (fonte editável da tradução) é versionado.

## Passos (executor marca [x] ao concluir)
- [x] 1. Envolver com `self.tr(...)` as strings de mensagem (message bar,
      não o título `'Desire Lines'`) nas funções `_get_layer`, `matrix` e
      `fvector` de `desirelines_dialog.py`. — arquivos: `desirelines_dialog.py`
      Verificação: `grep -n "iface.messageBar" desirelines_dialog.py` nessas
      funções mostra o texto envolto em `self.tr(`.

- [x] 2. Envolver com `self.tr(...)` as strings de validação e de progresso
      dentro de `desirelines()` (mensagem de identificador inválido, texto
      `'Generating desire lines…'` passado a `_push_progress`). — arquivos:
      `desirelines_dialog.py`
      Verificação: mesma checagem via `grep`, mais `pytest test/test_desirelines_dialog.py`
      continua passando.

- [x] 3. Refatorar `aon.pick_metric_crs` para retornar `(crs, reason)` onde
      `reason` é um dict estruturado (`{'code': 'already_metric'|'utm'|'albers'|'no_metric_crs', 'zone': ..., 'epsg': ...}`)
      em vez de uma frase pronta em inglês. Atualizar as chamadas internas
      de `allocate_aon`/demais funções de `aon.py` se dependerem do formato
      antigo. — arquivos: `aon.py`
      Verificação: `python -c "import aon"` sem erro; nenhuma frase em
      inglês é montada dentro de `aon.py`.

- [x] 4. Atualizar `test/test_aon.py` para checar `reason['code']` (e
      `reason.get('zone')`/`reason.get('epsg')` quando aplicável) em vez de
      `assertIn('UTM', note)` / `assertIn('Albers', note)` / `assertIn('metric', note)`.
      — arquivos: `test/test_aon.py`
      Verificação: `pytest test/test_aon.py` passa.

- [x] 5. Em `desirelines_dialog.py`, adicionar um pequeno mapeamento
      código→`self.tr(...)` para montar a frase final do CRS a partir do
      `reason` estruturado (passo 3), e usar esse texto tanto na mensagem
      de erro (`metric_crs is None`) quanto na mensagem de sucesso final de
      `run_aon`. Envolver com `self.tr(...)` as demais strings de
      `run_aon` (mínimo de 3 centróides, nenhum par OD casado, texto de
      progresso `'Allocating (AoN over Delaunay)…'`, e os fragmentos de
      `notes` — unreachable/missing/skipped). — arquivos: `desirelines_dialog.py`
      Verificação: `grep -n "self.tr(" desirelines_dialog.py` cobre todas as
      strings identificadas nos passos 1, 2 e 5; `pytest test/test_desirelines_dialog.py test/test_aon.py` passa.

- [x] 6. Remover `i18n/af.ts` (sobra de template, não usada pelo plugin) e
      reescrever `test/test_translations.py` para carregar
      `i18n/DesireLines_pt.qm` e comparar a tradução de uma string real do
      plugin (ex.: `QCoreApplication.translate('DesireLinesDialog', 'Read CSV')`)
      contra o texto em PT-BR esperado. — arquivos: `i18n/af.ts` (remover),
      `test/test_translations.py`
      Verificação: o teste falha antes do passo 9 (arquivo `pt.qm` ainda não
      existe/ainda não tem a tradução) e passa depois — confirma que o teste
      está de fato exercitando a tradução nova.

- [x] 7. Corrigir `scripts/update-strings.sh` para chamar `pylupdate5` (em
      vez de `pylupdate4`, que não existe mais em ambientes QGIS 3
      atuais). — arquivos: `scripts/update-strings.sh`
      Verificação: `which pylupdate5` resolve no ambiente de dev; rodar o
      script manualmente não dá "command not found".

- [x] 8. Configurar o locale `pt` no build: `Makefile` → `LOCALES = pt` e
      `LRELEASE = lrelease` (descomentar/ajustar); `pb_tool.cfg` → seção
      `[files]`, campo `locales: pt`. — arquivos: `Makefile`, `pb_tool.cfg`
      Verificação: `make transup` roda sem erro e cria/atualiza `i18n/pt.ts`.

- [ ] 9. Rodar `make transup` para extrair todas as strings marcadas com
      `tr(...)` (Python) e todas as strings do `.ui` para `i18n/pt.ts`, e
      preencher manualmente `<translation>` em Português do Brasil para
      cada `<source>` extraída (inclui labels/tooltips do `.ui` e todas as
      mensagens envolvidas em `self.tr()` nos passos 1, 2 e 5). — arquivos:
      `i18n/pt.ts`
      Verificação: `i18n/pt.ts` não tem nenhuma tag `<translation type="unfinished"></translation>`
      vazia restante (`grep -c "unfinished" i18n/pt.ts` = 0 ou só em itens
      intencionalmente não traduzidos, ex.: nome do plugin).

- [ ] 10. Rodar `make transcompile` para compilar `i18n/pt.ts` →
      `i18n/DesireLines_pt.qm`, e confirmar que `pytest test/test_translations.py`
      (reescrito no passo 6) passa. — arquivos: `i18n/DesireLines_pt.qm`
      (gerado, não versionado)
      Verificação: `pytest test/test_translations.py` verde.

- [ ] 11. QA manual no QGIS: em Configurações → Opções → Geral, marcar
      "Sobrepor idioma do sistema" com Português (Brasil), reiniciar o
      QGIS/recarregar o plugin, abrir as duas abas (Desire Lines e AoN
      Delaunay) e conferir que labels, tooltips e todas as mensagens da
      message bar (sucesso, aviso, erro, progresso) aparecem em PT-BR;
      depois voltar o locale ao padrão e confirmar que tudo volta a
      aparecer em Inglês, sem strings quebradas ou "unfinished". — arquivos:
      nenhum (validação funcional)
      Verificação: capturas de tela ou checklist manual, uma por idioma,
      cobrindo os fluxos "Read CSV → Desire Lines" e "Allocate (AoN)".

## Critério de aceite
- Com o locale do QGIS em Português (Brasil), toda a interface do plugin
  (labels do `.ui`, tooltips, mensagens de erro/aviso/sucesso da message
  bar, textos de progresso) aparece em PT-BR; com qualquer outro locale,
  aparece em Inglês (comportamento atual preservado).
- `aon.py` continua sem import de módulos Qt/GUI (`qgis.PyQt`) — a
  tradução acontece inteiramente em `desirelines_dialog.py`.
- `i18n/af.ts` não existe mais; `i18n/pt.ts` é versionado e
  `i18n/DesireLines_pt.qm` é gerado por `make transcompile` (não
  versionado, conforme `.gitignore`).
- `pytest test/` passa (inclui `test_aon.py`, `test_desirelines_dialog.py`,
  `test_translations.py`).
- `make transup` roda sem erro em um ambiente QGIS 3 atual (com
  `pylupdate5` e `lrelease` disponíveis).
