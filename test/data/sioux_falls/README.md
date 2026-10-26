# Rede Sioux Falls (Benchmark)

Dados da rede de referência de Sioux Falls utilizados para testes de regressão e validação de topologia de rede no plugin Desire Lines.

## Fonte Original e Atribuição

- **Repositório TransportationNetworks**: [bstabler/TransportationNetworks](https://github.com/bstabler/TransportationNetworks/tree/master/SiouxFalls)
- **Repositório de extração**: [marsuconn/sioux-falls-network](https://github.com/marsuconn/sioux-falls-network) (arquivos `data/SiouxFalls_node.tntp` e `data/SiouxFalls_net.tntp`)
- **Publicação original**: LeBlanc, L.J., Morlok, E.K., Pierskalla, W.P. (1975). *An efficient approach to solving the road network equilibrium traffic assignment problem*. Transportation Research, Vol. 9, pp. 309-318.
- **Coleção TNTP**: Hillel Bar-Gera, Transportation Network Test Problems.

## Licença e Uso

Os dados do TransportationNetworks são disponibilizados publicamente para fins de pesquisa e ensino em planejamento de transportes e engenharia de tráfego.

## Sistema de Coordenadas

As coordenadas nos nós (`x`, `y`) representam **Longitude e Latitude** em graus geográficos no datum WGS 84 (**EPSG:4326**).

- `x`: Longitude (ex.: -96.77041974)
- `y`: Latitude (ex.: 43.61282792)

## Arquivos

- `nodes.csv`: 24 nós com as colunas `node`, `x`, `y`.
- `links.csv`: 76 links direcionados (38 pares bidirecionais) com as colunas `init_node`, `term_node`, `capacity`, `length`, `free_flow_time`.
