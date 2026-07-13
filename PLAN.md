# PLAN — Desire Lines (metadata.txt: compatibilidade explícita com QGIS 4.x)

## Objetivo
Tornar explícita, em `metadata.txt` (o único metadata realmente empacotado
pelo plugin — ver `pb_tool.cfg`/`Makefile`, `EXTRAS = metadata.txt icon.png`),
a compatibilidade do plugin com QGIS 4.x, mantendo `qgisMinimumVersion=3.0`
e sem introduzir nenhum teto (`qgisMaximumVersion`) que possa travar
instalação em versões futuras do QGIS.

## Decisões de arquitetura

- **A premissa do pedido não bate com o estado atual do arquivo**: `grep -n
  "qgisMaximumVersion" metadata.txt` não retorna nada, e `git log -p --all --
  metadata.txt` mostra que essa chave **nunca existiu** nesse arquivo (o
  único commit relacionado, `169d786`, criou o `metadados.txt`, um arquivo
  duplicado/legado em pt, não empacotado, fora de escopo). Não há
  `qgisMaximumVersion=3.99.0` para remover.
- Por definição do formato de metadata do QGIS, **ausência** de
  `qgisMaximumVersion` já significa "sem teto de versão" — o plugin já é
  instalável em QGIS 4.x hoje, do ponto de vista do metadata. Isso também
  bate com `docs/topicos/compatibilidade-com-qgis-3-x-e-4-x.md`, que
  registra o trabalho de compat Qt5/Qt6 já feito e testado (gate verde em
  QGIS 3.44 e QGIS 4.2 em container).
- O que falta, então, não é uma correção funcional, é tornar essa
  compatibilidade **explícita e visível** para quem lê o `metadata.txt` /
  changelog exibido na QGIS Plugin Repository. **Solução mais simples**: (a)
  garantir que `qgisMaximumVersion` continue ausente (não adicionar teto
  nenhum, nem um valor alto tipo `4.99.0` — isso só criaria manutenção
  futura, ter que lembrar de bumpar a cada nova major do QGIS); (b)
  adicionar ao bloco `changelog=` já existente em `metadata.txt` uma entrada
  para a versão atual (`version=0.3.0`, hoje sem nenhuma entrada no
  changelog — ele pula direto de `0.2.0` para o número declarado) mencionando
  compatibilidade testada com QGIS 4.x (Qt6/PyQt6), coerente com o trabalho
  já registrado nos docs de tópico.
- `metadados.txt` (duplicado legado em pt, `version=0.2`, não referenciado
  em `pb_tool.cfg` nem `Makefile`) fica **fora de escopo** — não é
  empacotado, não é lido pelo QGIS Plugin Repository.
- Não mexer em `qgisMinimumVersion` (permanece `3.0`).

## Passos (executor marca [x] ao concluir)

- [ ] 1. Confirmar que `metadata.txt` não contém `qgisMaximumVersion`
      (checagem, não deve haver edição neste passo a menos que a linha
      apareça). — arquivos: `metadata.txt`
      Verificação: `grep -n "qgisMaximumVersion" metadata.txt` não retorna
      nada. Se retornar algo, remover a linha inteira nesse mesmo passo.

- [ ] 2. Adicionar uma entrada para a versão atual no bloco `changelog=` de
      `metadata.txt`, acima da entrada `0.2.0` já existente, mencionando
      explicitamente compatibilidade testada com QGIS 4.x (Qt6/PyQt6),
      mantendo a mesma indentação/formato das entradas existentes. —
      arquivos: `metadata.txt`
      Verificação: `grep -n "0.3.0" metadata.txt` mostra a nova entrada
      dentro do bloco `changelog=`, e o texto da entrada cita QGIS 4.x.

- [ ] 3. Confirmar que `qgisMinimumVersion=3.0` continua inalterado. —
      arquivos: `metadata.txt` (checagem, sem edição esperada)
      Verificação: `grep -n "^qgisMinimumVersion" metadata.txt` mostra
      `qgisMinimumVersion=3.0`.

- [ ] 4. Confirmar que `pb_tool.cfg` e `plugin_upload.py` não fazem nenhuma
      checagem própria de `qgisMaximumVersion`/versão máxima que precise
      ficar sincronizada com `metadata.txt`. — arquivos: `pb_tool.cfg`,
      `plugin_upload.py` (checagem, sem edição esperada)
      Verificação: `grep -rn "Maximum\|max_version\|3.99\|4.99" pb_tool.cfg
      plugin_upload.py` não retorna nada relevante.

## Critério de aceite
- `metadata.txt` não tem linha `qgisMaximumVersion` (nenhum teto de versão).
- `metadata.txt` mantém `qgisMinimumVersion=3.0`.
- O bloco `changelog=` de `metadata.txt` tem uma entrada para a versão
  atual mencionando explicitamente compatibilidade com QGIS 4.x.
- Nenhum outro arquivo do projeto (`metadados.txt`, `pb_tool.cfg`,
  `plugin_upload.py`) precisou mudar.
