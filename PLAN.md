# PLAN — Desire Lines (nome da pasta do plugin no ZIP: `desire_lines`)

## Objetivo
Fazer o ZIP gerado pelo `Makefile` (`make package` / `make zip` / `make upload`)
conter a pasta **`desire_lines`** (com underscore) na raiz, não `desirelines`
(sem underscore) — que é o nome já registrado em plugins.qgis.org e o que o
validador de upload exige (ver comentário já existente em `pb_tool.cfg`,
seção `[plugin]`: "Must match the package name already registered on
plugins.qgis.org (desire_lines) — the upload validator rejects a mismatched
folder name").

## Decisões de arquitetura

- **Causa raiz confirmada**: `Makefile` define `PLUGINNAME = desirelines`
  (linha 43). Essa variável é usada tanto para o diretório de deploy
  (`$(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)`) quanto para o prefixo
  do zip nos alvos `zip` (`cd ...; zip -9r $(CURDIR)/$(PLUGINNAME).zip
  $(PLUGINNAME)`) e `package` (`git archive --prefix=$(PLUGINNAME)/ -o
  $(PLUGINNAME).zip $(VERSION)`). Confirmado inspecionando
  `dist/desirelines-0.3.0.zip` já gerado: a pasta raiz dentro do zip é
  `desirelines/`, não `desire_lines/`.
- **`pb_tool.cfg` já está correto** (`name: desire_lines`, com o comentário
  explicando o motivo) — só o `Makefile` ficou dessincronizado. Não é
  preciso decidir nada de novo ali, só confirmar que os dois ficam
  consistentes depois da mudança.
- **Solução mais simples**: mudar só o valor da variável `PLUGINNAME` no
  `Makefile`, de `desirelines` para `desire_lines`. Não renomear os módulos
  Python (`desirelines.py`, `desirelines_dialog.py`, etc.) — o nome da
  pasta do pacote no ZIP é independente do nome dos arquivos `.py` dentro
  dela (o `__init__.py` já usa import relativo `from .desirelines import
  DesireLines`, que funciona não importa o nome do diretório pai). Renomear
  os módulos seria escopo maior que o pedido e tocaria imports, testes,
  `i18n/pt.ts` (que referencia os caminhos `../desirelines.py`) e o
  `Makefile` inteiro — não é necessário para resolver o bug relatado.
  Confirmado por grep que `PLUGINNAME` só aparece na linha 43 do Makefile
  e que nenhum outro arquivo do repo (CI, scripts, docs) referencia
  `PLUGINNAME` ou hardcoda `desirelines.zip`/`desirelines-<versão>.zip`
  fora do próprio `Makefile` e de um doc (`docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`,
  que só relata este mesmo bug — não precisa virar código).
- **Nome do arquivo .zip final também muda** (de `desirelines.zip`/
  `desirelines-<versão>.zip` para `desire_lines.zip`/`desire_lines-<versão>.zip`),
  como efeito colateral direto de mudar `PLUGINNAME` — aceitável e desejado,
  já que o nome do arquivo de zip não é o que o QGIS valida, mas manter os
  dois (pasta interna e nome do arquivo) consistentes é mais simples e
  menos confuso do que desacoplá-los com uma variável nova só para o nome
  do arquivo.
- **`dist/desirelines-0.3.0.zip` (artefato já gerado, errado) não faz parte
  do código-fonte** — não precisa ser corrigido/regravado por este PLAN;
  o próximo `make package`/`make zip` já vai gerar o nome certo. Não vamos
  apagar esse arquivo antigo automaticamente (pode ser artefato que o
  usuário ainda queira inspecionar) — só sinalizar no critério de aceite
  que um novo build deve ser gerado para substituí-lo.

## Passos (executor marca [x] ao concluir)

- [ ] 1. Em `Makefile`, trocar `PLUGINNAME = desirelines` (linha 43) por
      `PLUGINNAME = desire_lines`. — arquivos: `Makefile`
      Verificação: `grep -n "^PLUGINNAME" Makefile` mostra
      `PLUGINNAME = desire_lines`.

- [ ] 2. Rodar `make package VERSION=<tag ou commit atual>` (ou `make zip`,
      conforme o fluxo já usado pelo projeto) e inspecionar o zip gerado.
      — arquivos: nenhum (gera `desire_lines.zip` ou
      `desire_lines-<versão>.zip` na raiz)
      Verificação: `unzip -l desire_lines*.zip | head` mostra a pasta raiz
      `desire_lines/` (não `desirelines/`); `unzip -l desire_lines*.zip |
      grep -c '^\s*desirelines/'` retorna `0`.

- [ ] 3. Confirmar que `pb_tool.cfg` (`name: desire_lines`) e o `Makefile`
      agora concordam, e que nenhum outro arquivo do repo ainda referencia
      `PLUGINNAME` com o valor antigo. — arquivos: nenhum (checagem)
      Verificação: `grep -rn "PLUGINNAME" Makefile` só mostra a definição e
      seus usos via `$(PLUGINNAME)`; `grep -n "name:" pb_tool.cfg` mostra
      `desire_lines`.

- [ ] 4. Apagar o artefato antigo e desatualizado `dist/desirelines-0.3.0.zip`
      (pasta interna errada) e, se o fluxo de release do projeto usa a
      pasta `dist/`, colocar ali o novo zip gerado no passo 2 com o nome
      correto. — arquivos: `dist/desirelines-0.3.0.zip` (remover),
      `dist/` (novo zip)
      Verificação: `ls dist/` não mostra mais nenhum arquivo com
      `desirelines` sem underscore; mostra o novo `desire_lines*.zip`.

## Critério de aceite
- `Makefile` tem `PLUGINNAME = desire_lines`.
- Um zip gerado por `make package` (ou `make zip`) contém a pasta raiz
  `desire_lines/`, nunca `desirelines/`.
- `pb_tool.cfg` e `Makefile` concordam no nome da pasta do plugin
  (`desire_lines`).
- Nenhum artefato obsoleto com a pasta `desirelines/` (sem underscore)
  permanece em `dist/`.
