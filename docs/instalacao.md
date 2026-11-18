# Instalação

## Versões de QGIS suportadas

O `desire_lines/metadata.txt` declara suporte do QGIS 3.0 até a série 4.x
(`qgisMaximumVersion=4.99`) e declara `supportsQt6=True`: o plugin roda tanto em
builds Qt5 quanto Qt6 do QGIS (o código usa enums qualificados e
`QMetaType.Type.<X>`).

| Item | Valor |
|---|---|
| Versão mínima do QGIS | 3.0 |
| Versão máxima do QGIS | 4.99 |
| Qt | Qt5 e Qt6 |
| Versão atual do plugin | 0.7.4 |

## Instalar pelo repositório oficial do QGIS

O Desire Lines está publicado no [repositório oficial de complementos do
QGIS](https://plugins.qgis.org/plugins/desire_lines/). No QGIS, abra
*Complementos → Gerenciar e instalar complementos* ("Plugins → Manage and install
plugins"), procure por **Desire Lines** na aba *Todos* e clique em *Instalar
complemento*. O QGIS avisa quando sai versão nova.

## Onde o plugin aparece depois de instalado

O Desire Lines aparece em dois lugares: na barra de ferramentas de
complementos com um **botão único com seta de menu** (o clique no ícone abre o
diálogo principal *Desire Lines*; a seta abre o menu suspenso com as opções
*Desire Lines* e *Alocação em rodovias* ["Highway Assignment"]), e no menu
*Vetor* → *&Desire Lines* (com as mesmas opções).

![Ícone do Desire Lines na barra de ferramentas e entrada no menu Vetor](https://github.com/user-attachments/assets/69aaddac-a9c1-4cee-a3cb-c3fb0cbf7148)

## Requisito do GISBR (aba Alocação em rodovias)

!!! warning "GISBR é opcional (necessário só para baixar a malha oficial)"
    O [GISBR](https://github.com/d-camargo/gisbr) é opcional: ele é quem busca a
    malha rodoviária oficial (SNV/DNIT, INDE) e requer QGIS 3.16 ou mais
    novo. O Desire Lines verifica em tempo de execução se o GISBR está
    instalado e não pede para instalá-lo quando ele já existe.

    **Sem o GISBR instalado**, aparece **uma** janela ao carregar o plugin
    sugerindo a instalação, com botão para o Gerenciador de Complementos e a
    opção "Não mostrar novamente".

    Mesmo sem o GISBR, as três primeiras abas (*Matriz OD*, *Linhas de desejo*,
    *AoN (Delaunay)*) funcionam normalmente. Na aba *Alocação em rodovias*, o
    aviso visível continua sendo exibido e a opção de baixar a malha pelo GISBR
    fica desabilitada — mas a aba continua utilizável se você já tiver uma
    camada de malha rodoviária carregada no projeto e apontar para ela. Ou seja,
    o que se perde sem o GISBR é o download da malha oficial, não a aba inteira.

    A mensagem exibida é: "O plugin GisBR
    (https://github.com/d-camargo/gisbr) é necessário para obter a malha
    rodoviária oficial."

## Instalação por symlink (desenvolvimento)

Para quem mexe no código, não é preciso empacotar zip a cada mudança. Da raiz
do repositório:

```bash
make deploy            # symlinka desire_lines/ no perfil default do QGIS
make deploy-flatpak    # mesmo symlink, no perfil do QGIS Flatpak
make undeploy          # remove o symlink do perfil default
make undeploy-flatpak  # remove o symlink do perfil Flatpak
```

`make deploy` cria o symlink em
`~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/desire_lines`.
Depois de mudar código, recarregue com o Plugin Reloader ou reinicie o QGIS.

Para entender como o código está organizado, veja [Arquitetura](arquitetura.md).
