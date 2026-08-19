# Instalação

## Versões de QGIS suportadas

O `desire_lines/metadata.txt` declara suporte de QGIS 3.0 até a série 4.x
(`qgisMaximumVersion=4.99`). O código já foi ajustado para rodar sob Qt6 (enums
qualificados, `QMetaType.Type.<X>`), então funciona tanto em builds Qt5 quanto Qt6
do QGIS — mas o `metadata.txt` não declara `supportsQt6=True`: o ajuste é do
código, não uma promessa formal do metadado.

| Item | Valor |
|---|---|
| Versão mínima do QGIS | 3.0 |
| Versão máxima do QGIS | 4.99 |
| Qt | Qt5 e Qt6 |
| Versão atual do plugin | 0.4.0 |

## Instalar pelo ZIP (Gerenciador de Complementos)

1. Baixe o zip do plugin. No QGIS, abra o menu *Complementos → Gerenciar e
   instalar complementos* ("Plugins → Manage and install plugins").

   ![Menu Complementos do QGIS aberto em Gerenciar e instalar complementos](https://github.com/user-attachments/assets/e30e8a55-965b-4c18-8943-7e83ba1dccc1)

2. Na janela que abre, vá em *Instalar a partir do ZIP* ("Install from ZIP"),
   localize o arquivo baixado e clique em *Instalar Complemento*.

   ![Aba Instalar a partir do ZIP com o caminho do arquivo selecionado](https://github.com/user-attachments/assets/d1580b18-e1e3-43e5-bb0a-afe537055b9e)

3. O QGIS mostra um aviso de segurança durante a instalação — confirme com
   *Sim*.

   ![Aviso de segurança do QGIS pedindo confirmação da instalação](https://github.com/user-attachments/assets/e1766428-7feb-4df4-bc14-8fd33d0f1eb9)

4. Terminada a instalação, feche a janela de complementos.

## Onde o plugin aparece depois de instalado

O Desire Lines aparece em dois lugares: na barra de ferramentas de
complementos, e no menu *Vetor* → *&Desire Lines*.

![Ícone do Desire Lines na barra de ferramentas e entrada no menu Vetor](https://github.com/user-attachments/assets/69aaddac-a9c1-4cee-a3cb-c3fb0cbf7148)

## Requisito do GISBR (aba Alocação em rodovias)

!!! warning "GISBR é necessário só para baixar a malha oficial"
    O `metadata.txt` declara `plugin_dependencies=GisBR`, mas quem decide em
    tempo de execução é a checagem `gisbr_bridge.is_available()` — não o
    metadado. O [GISBR](https://github.com/d-camargo/gisbr) é quem busca a
    malha rodoviária oficial (SNV/DNIT, INDE) e requer QGIS 3.16 ou mais
    novo.

    **Sem o GISBR instalado**, as três primeiras abas (*Matriz OD*, *Linhas
    de desejo*, *AoN (Delaunay)*) funcionam normalmente. Na aba *Alocação em
    rodovias* aparece um aviso visível e a opção de baixar a malha pelo
    GISBR fica desabilitada — mas a aba continua utilizável se você já tiver
    uma camada de malha rodoviária carregada no projeto e apontar para ela.
    Ou seja, o que se perde sem o GISBR é o download da malha oficial, não a
    aba inteira.

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
