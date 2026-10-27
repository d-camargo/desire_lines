# Desire Lines — Documentação

Este arquivo era a referência funcional e técnica do plugin **Desire Lines**.

A documentação do projeto foi reorganizada e expandida em um site oficial de documentação viva:

👉 **[https://desirelines.dcamargo.com.br](https://desirelines.dcamargo.com.br)**

Os arquivos fonte da documentação agora residem na pasta [`docs/`](docs/) do repositório.

---

## Mapeamento de Conteúdo (Seção Antiga → Nova Página)

Para facilitar a localização de conteúdos citados anteriormente neste arquivo, utilize o mapa abaixo:

| Seção Antiga | Descrição | Nova Página na Documentação |
|---|---|---|
| **§1. Visão geral** | Visão geral do plugin, abas e arquivo de saída único (`.gpkg`). | [Visão Geral / Início](https://desirelines.dcamargo.com.br/) (`docs/index.md`) |
| **§2. Aba 1 — Origin/Destination Matrix** | Leitura de matrizes CSV, formato longo/largo, suporte a pandas e centroides. | [Guia: Matriz OD](https://desirelines.dcamargo.com.br/guias/matriz-od/) (`docs/guias/matriz-od.md`) e [Formatos de Entrada](https://desirelines.dcamargo.com.br/referencia/formatos-de-entrada/) (`docs/referencia/formatos-de-entrada.md`) |
| **§3. Aba 2 — Desire Lines** | Geração de linhas de desejo por SQL virtual layer e simbologia graduada. | [Guia: Linhas de Desejo](https://desirelines.dcamargo.com.br/guias/linhas-de-desejo/) (`docs/guias/linhas-de-desejo.md`) |
| **§4. Aba 3 — AoN (Delaunay)** | Alocação All-or-Nothing sintética sobre triangulação de Delaunay e CRS métrico. | [Guia: AoN (Delaunay)](https://desirelines.dcamargo.com.br/guias/aon-delaunay/) (`docs/guias/aon-delaunay.md`) |
| **§5. Aba 4 — Alocação em rodovias** | Passo a passo da alocação rodoviária real com HCM e equilíbrio (AoN, MSA e Frank-Wolfe; parâmetros de rede capacidade/tempo livre/mão única). | [Guia: Alocação em Rodovias](https://desirelines.dcamargo.com.br/guias/alocacao-rodovias/) (`docs/guias/alocacao-rodovias.md`) e [Parâmetros HCM](https://desirelines.dcamargo.com.br/referencia/parametros-hcm/) (`docs/referencia/parametros-hcm.md`) |
| **§6. Arquitetura do código** | Estrutura dos módulos (`desirelines_dialog.py`, `aon.py`, `traffic/*`) e fronteira GUI × lógica pura. | [Arquitetura](https://desirelines.dcamargo.com.br/arquitetura/) (`docs/arquitetura.md`) |
| **§7. Testes** | Suíte de testes unitários e como executá-la. | [Arquitetura — Testes](https://desirelines.dcamargo.com.br/arquitetura/#3-como-rodar-a-suite-de-testes) (`docs/arquitetura.md`) |
| **§8. Notas e limitações** | Requisitos de ambiente, encodings e limitações de escopo. | [Solução de Problemas](https://desirelines.dcamargo.com.br/solucao-de-problemas/) (`docs/solucao-de-problemas.md`) e [Métodos](https://desirelines.dcamargo.com.br/referencia/metodos/) (`docs/referencia/metodos.md`) |
| **§9. Decisões de Arquitetura (D1–D11)** | Registro das decisões de design do módulo de alocação de tráfego rodoviário e validação com Sioux Falls. | [Arquitetura — Decisões D1–D11](https://desirelines.dcamargo.com.br/arquitetura/#5-registro-condensado-das-decisoes-de-arquitetura-d1d11) (`docs/arquitetura.md`) e [Métodos](https://desirelines.dcamargo.com.br/referencia/metodos/) (`docs/referencia/metodos.md`) |

---

## Atualizações Técnicas da Versão 0.7.0

* **Algoritmo Frank-Wolfe (FW + BPR)**: Novo método de equilíbrio do usuário por busca linear (bisseção de $\lambda$ na derivada da função de Beckmann) com convergência acelerada em relação ao MSA. Novos padrões do painel: 100 iterações e tolerância de gap 0,001. Detalhado em [Métodos de Alocação](https://desirelines.dcamargo.com.br/referencia/metodos/) (`docs/referencia/metodos.md`).
* **Validação com Sioux Falls**: O motor atinge erro médio de 0,14% e erro máximo de 0,7% contra os fluxos de referência analíticos de Sioux Falls sob 300 iterações de Frank-Wolfe. Veja a tabela de diagnóstico completa em [Métodos — Validação com Sioux Falls](https://desirelines.dcamargo.com.br/referencia/metodos/#6-validacao-com-sioux-falls) (`docs/referencia/metodos.md`).
* **Parâmetros de Rede e a Sentinela `0`**: Suporte aos parâmetros `capacidade`, `tempo_livre` e `mao_unica`. A sentinela `0.0` sinaliza cálculo automático pelo HCM ou geometria ÷ velocidade livre; valores `> 0` sobrepõem o cálculo com os dados informados da malha.
* **Mapeamento Direto de Campos (D2)**: Seleção de coluna nos controles *field:* da interface gráfica repassa o mapeamento diretamente para o resolvedor como dado `oficial`, com prioridade sobre nomes candidatos padrão.
* **Rastreabilidade e Proveniência**: Novos atributos de proveniência `src_capacidade`, `src_tempo_livre` e `src_mao_unica`, além da camada de saída `alocacao_fw`. Consulte [Campos de Saída](https://desirelines.dcamargo.com.br/referencia/campos-de-saida/) (`docs/referencia/campos-de-saida.md`).

---

> Para informações sobre a estrutura do código, a suíte de testes e o empacotamento, veja
> [Arquitetura](https://desirelines.dcamargo.com.br/arquitetura/) (`docs/arquitetura.md`).
