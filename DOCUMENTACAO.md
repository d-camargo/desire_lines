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
| **§5. Aba 4 — Alocação em rodovias** | Passo a passo da alocação rodoviária real com HCM (capacidade, AoN e MSA). | [Guia: Alocação em Rodovias](https://desirelines.dcamargo.com.br/guias/alocacao-rodovias/) (`docs/guias/alocacao-rodovias.md`) e [Parâmetros HCM](https://desirelines.dcamargo.com.br/referencia/parametros-hcm/) (`docs/referencia/parametros-hcm.md`) |
| **§6. Arquitetura do código** | Estrutura dos módulos (`desirelines_dialog.py`, `aon.py`, `traffic/*`) e fronteira GUI × lógica pura. | [Arquitetura](https://desirelines.dcamargo.com.br/arquitetura/) (`docs/arquitetura.md`) |
| **§7. Testes** | Suíte de testes unitários e como executá-la. | [Arquitetura — Testes](https://desirelines.dcamargo.com.br/arquitetura/#execucao-de-testes) (`docs/arquitetura.md`) |
| **§8. Notas e limitações** | Requisitos de ambiente, encodings e limitações de escopo. | [Solução de Problemas](https://desirelines.dcamargo.com.br/solucao-de-problemas/) (`docs/solucao-de-problemas.md`) e [Métodos](https://desirelines.dcamargo.com.br/referencia/metodos/) (`docs/referencia/metodos.md`) |
| **§9. Decisões de Arquitetura (D1–D11)** | Registro das decisões de design do módulo de alocação de tráfego rodoviário. | [Arquitetura — Decisões D1–D11](https://desirelines.dcamargo.com.br/arquitetura/#decisoes-de-arquitetura-d1d11) (`docs/arquitetura.md`) e [Métodos](https://desirelines.dcamargo.com.br/referencia/metodos/) (`docs/referencia/metodos.md`) |

---

> Para outras informações sobre desenvolvimento, veja a fonte única de regras em [`GEMINI.md`](GEMINI.md).
