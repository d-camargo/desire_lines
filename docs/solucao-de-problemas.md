# Solução de problemas

Um item por sintoma. Cada um traz a **mensagem** como ela aparece na barra de
mensagens do QGIS (em português, quando a tradução PT-BR está ativa), a
**causa** e **o que fazer**. Se você chegou aqui com uma mensagem na tela,
procure por ela nesta página (`Ctrl+F`).

---

## A opção de baixar a malha pelo GISBR está desabilitada

!!! warning "Mensagem"
    "O plugin GisBR (https://github.com/d-camargo/gisbr) é necessário para
    obter a malha rodoviária oficial." — exibida como um aviso fixo no topo da
    aba *Alocação em rodovias*.

**Causa.** O plugin [GISBR](https://github.com/d-camargo/gisbr) não está
instalado ou não foi detectado. A checagem é feita em tempo de execução
(`gisbr_bridge.is_available()`), não pelo `plugin_dependencies` do metadado:
ela tenta importar `gisbr.core.sources`/`gisbr.core.connectors.wfs` e, se
falhar, procura o provedor de processamento `gisbr` registrado no QGIS.

**O que fazer.**

* A **aba não fica inteira desabilitada** — o que desliga é só o rádio
  *Baixar via GisBR (malha oficial SNV/DER)*. Se você já tem uma camada de
  malha rodoviária no projeto, escolha *usar camada existente* e a aba
  funciona normalmente.
* Para recuperar o download, instale o GISBR (QGIS 3.16+) e reabra o diálogo —
  ver [Instalação](instalacao.md).

---

## Falha ao baixar a malha do GISBR

!!! warning "Mensagem"
    "Falha ao obter a malha rodoviária do GisBR: …" (o final varia conforme o
    erro devolvido pelo GISBR).

**Causa.** O GISBR está instalado, mas a busca não voltou com uma camada: rede
indisponível, o serviço WFS do SNV/INDE fora do ar ou lento, proxy/firewall
bloqueando, ou UF/recorte que não produziu feição alguma.

**O que fazer.**

1. Teste o próprio GISBR isoladamente (baixe a malha por ele) — se falhar lá,
   o problema não é do Desire Lines.
2. Confira a conexão e as configurações de proxy do QGIS
   (*Configurações → Opções → Rede*).
3. Confira a sigla da UF: o botão só habilita com **exatamente 2 letras**.
4. Se o serviço estiver instável, baixe a malha uma vez, salve em GeoPackage e
   passe a usar o modo *camada existente* — evita depender da rede a cada
   execução.

---

## A malha ficou vazia depois do recorte

!!! warning "Mensagem"
    "A malha rodoviária ficou vazia após o recorte."

**Causa.** O recorte pela área de estudo (envelope dos centroides mais a
folga do conector) não interceptou nenhuma feição da malha. Quase sempre é
**divergência de CRS ou de região**: centroides em um lugar, malha em outro.

**O que fazer.**

* Verifique se centroides e malha estão na mesma região do mapa — carregue as
  duas camadas e olhe.
* Confirme o CRS declarado de cada camada (um CRS errado desloca tudo).
* Aumente *Conector máx. (m)*: ele também aumenta a folga do recorte.
* Se estiver baixando pelo GISBR, confira se a UF é a da área de estudo.

!!! note "Aviso parecido, mas não fatal"
    "Não foi possível recortar a malha pela área de estudo (…); usando a malha
    completa." — aqui o recorte falhou e o plugin **seguiu** com a malha
    inteira. Não invalida o resultado, só deixa a execução mais lenta.

---

## Nenhum centroide (ou poucos) conectou-se à malha

!!! warning "Mensagens"
    "Nenhum centróide pôde ser conectado à malha rodoviária (nó mais próximo
    além de … m)." (crítica, interrompe) ou "{n} centróide(s) não conectados à
    malha rodoviária." (aviso, segue com os demais).

**Causa.** O conector de centroide liga cada centroide ao nó mais próximo da
rede, mas só até a distância máxima configurada. Zonas grandes, zonas sem
rodovia por perto ou uma malha esparsa deixam o centroide fora do alcance.

**O que fazer.**

* **Aumente *Conector máx. (m)*** na aba *Alocação em rodovias* (padrão
  5000 m). É o ajuste que resolve a maioria dos casos.
* Se só algumas zonas ficam de fora, veja se são zonas periféricas ou ilhas —
  pode ser mais correto excluí-las da análise do que esticar o conector a
  ponto de inventar um acesso que não existe.
* Um conector exageradamente longo distorce o caminho mínimo: prefira o menor
  valor que conecte todas as zonas de interesse.

---

## Zona da matriz sem centroide correspondente

!!! warning "Mensagens"
    "Nenhum par OD correspondeu aos ids dos centroides. Verifique se Origem,
    Destino e ID de Tráfego usam o mesmo esquema de id." (aba *AoN
    (Delaunay)*) · "Nenhum par OD corresponde aos centróides conectados.
    Verifique se Origem, Destino e Id de tráfego usam o mesmo esquema de
    identificação." (aba *Alocação em rodovias*) · "{n} linha(s) da matriz com
    ids desconhecidos" (aviso no resumo, quando só parte não casou).

**Causa.** Os ids de origem/destino da matriz não batem com o campo de id
escolhido na camada de centroides. Causas típicas: campos diferentes
selecionados nos combos, id numérico de um lado e texto do outro, espaços em
branco, zeros à esquerda, ou zonas que existem na matriz e não na camada.

**O que fazer.**

1. Confira os três combos (*Origem*, *Destino*, *ID de Tráfego*) — o id da
   camada tem de ser o mesmo esquema dos ids da matriz.
2. O plugin normaliza ids antes de comparar (`_zone_key`): `10.0` e `10`
   casam, espaços nas pontas são ignorados. O que **não** casa é `"010"` com
   `10`, nem ids de esquemas diferentes — ver
   [Formatos de entrada](referencia/formatos-de-entrada.md).
3. Se a mensagem for o aviso de "{n} linha(s) da matriz com ids
   desconhecidos", a execução terminou: essas linhas foram **descartadas**, e
   o resultado cobre só o resto. Vale conferir se o descarte é aceitável.

---

## Capacidade nula ou inválida

!!! warning "Mensagens"
    "{n} de {N} arcos descartados por capacidade nula ou inválida." (aviso) ·
    "Nenhum arco tem capacidade válida; revise os parâmetros HCM." (crítica,
    interrompe).

**Causa.** A capacidade sai do procedimento HCM; um valor não positivo
significa que os insumos daquele arco são inutilizáveis (número de faixas
zerado, tipo de pista ausente, largura ou fator fora de faixa). Manter esses
arcos daria divisão por zero em v/c e reportaria LOS F onde o problema é dado
faltando — por isso eles são **removidos**.

**O que fazer.**

* Confira os campos da malha mapeados para os parâmetros HCM e os valores
  globais de sobrescrita — ver
  [Parâmetros HCM](referencia/parametros-hcm.md).
* Use o campo de proveniência (`src_*`) da camada de saída para ver quais
  parâmetros vieram como `oficial`, `padrao` ou `usuario`: descarte em massa
  costuma significar que um campo esperado não existe na malha.
* Se o descarte for pequeno e localizado, inspecione esses arcos na tabela de
  atributos antes de aceitar o resultado.

---

## CRS geográfico em análise métrica

!!! warning "Mensagem"
    "não foi possível determinar um SRC métrico automaticamente; reprojete os
    centroides para um sistema métrico (UTM) e tente novamente."

**Causa.** Distâncias, comprimentos e conectores são calculados em metros. O
plugin escolhe sozinho um CRS métrico (zona UTM automática se a área couber em
uma zona; senão SIRGAS 2000 / Brazil Albers, EPSG:10857). A mensagem aparece
quando nem essa escolha automática foi possível — em geral porque o CRS de
origem dos centroides está ausente ou é inconsistente com as coordenadas.

**O que fazer.**

* Reprojete os centroides para um CRS métrico (UTM da região, ou EPSG:10857) e
  rode de novo.
* Confirme que o CRS **declarado** da camada é o CRS real dos dados — camada
  em graus marcada como métrica (ou o contrário) é a causa mais comum.
* Sobre a regra de escolha automática, ver
  [AoN (Delaunay)](guias/aon-delaunay.md).

---

## Execução muito lenta em rede grande

**Causa.** O motor de grafo é Python puro (existe por decisão D4 — o motor
nativo do QGIS não permite atualizar custo de arco entre iterações). O
envelope confortável é de cerca de **50.000 arcos direcionados**; o MSA roda
um Dijkstra por origem **a cada iteração**, então o custo cresce com
`iterações × origens`.

**O que fazer.**

* **Use AoN** para diagnóstico e para iterar rápido: é uma passada só,
  aproximadamente 10× mais rápido que o MSA com 10 iterações.
* Reduza *Iterações máx.* do MSA, ou afrouxe a tolerância de gap.
* Recorte a malha à área de estudo (deixe o recorte ligado) e reduza o número
  de zonas/origens únicas — é o que mais pesa.
* Detalhes em [Métodos](referencia/metodos.md).
