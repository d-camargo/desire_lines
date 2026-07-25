# coding=utf-8
"""Grafo próprio de roteamento sobre os arcos direcionados (D4, D8).

Por que não `QgsGraph`/`QgsVectorLayerDirector` (D4): o director cria uma
aresta **por segmento geométrico** e não devolve o vínculo aresta->feição, o
que impede acumular fluxo **por link** (a capacidade é do link) e congela o
custo no `makeGraph` — obrigaria a reconstruir o grafo a cada iteração do MSA.

Aqui o grafo é montado **uma vez** sobre os `Arc` de `network.py`: nó é a
extremidade do arco já arredondada à tolerância de snap (`network.node_key`),
o custo é um vetor paralelo aos arcos **atualizado in-place** entre iterações,
e o Dijkstra (`heapq`, stdlib) devolve **predecessor-arco** — não predecessor-nó
— para que o caminho reconstruído seja a lista dos arcos percorridos, pronta
para receber fluxo. O mesmo grafo serve às N iterações do MSA e ao AoN de
passada única.

Módulo em Python puro: não importa nada do QGIS e é testável sem ele.
"""

import heapq

INFINITY = float('inf')


class Graph(object):
    """Grafo direcionado de roteamento, com custo por arco mutável.

    Os arcos são indexados por posição; `costs[i]` é o custo corrente do arco
    `arcs[i]` (inicialmente `arc.t0`, o tempo a fluxo livre). A topologia é
    imutável depois da construção — só o vetor de custos muda entre iterações.

    Attributes:
        arcs (list): Arcos direcionados (objetos `network.Arc`), na ordem de entrada.
        costs (list): Custo corrente de cada arco, na mesma ordem de `arcs`.
        adjacency (dict): {nó: [índices dos arcos que saem do nó]}.
    """

    def __init__(self, arcs):
        """Monta a topologia a partir dos arcos direcionados.

        Args:
            arcs (iterable): Arcos direcionados (`network.Arc` ou objetos com
                `arc_id`, `from_node`, `to_node` e `t0`), incluindo os
                conectores de centróide de `network.connect_centroids`.

        Raises:
            ValueError: se dois arcos compartilharem o mesmo `arc_id`.
        """
        self.arcs = list(arcs)
        self.costs = [float(arc.t0) for arc in self.arcs]
        self.adjacency = {}
        self._index_by_id = {}

        for i, arc in enumerate(self.arcs):
            if arc.arc_id in self._index_by_id:
                raise ValueError(f"Arco duplicado no grafo: arc_id={arc.arc_id!r}.")
            self._index_by_id[arc.arc_id] = i
            self.adjacency.setdefault(arc.from_node, []).append(i)
            # Um nó só de chegada (sem arco saindo) também precisa existir como
            # destino alcançável do Dijkstra.
            self.adjacency.setdefault(arc.to_node, [])

    def __len__(self):
        """Retorna o número de arcos do grafo."""
        return len(self.arcs)

    @property
    def nodes(self):
        """list: Nós do grafo (tuplas (x, y) arredondadas à tolerância de snap)."""
        return list(self.adjacency.keys())

    def has_node(self, node):
        """Informa se o nó existe no grafo.

        Args:
            node (tuple): Nó (x, y) na convenção de `network.node_key`.

        Returns:
            bool: True se o nó pertence ao grafo.
        """
        return node in self.adjacency

    def index_of(self, arc_id):
        """Retorna o índice do arco a partir do seu `arc_id`.

        Args:
            arc_id: Identificador do arco direcionado.

        Returns:
            int: Índice em `arcs`/`costs`.

        Raises:
            KeyError: se o `arc_id` não existir no grafo.
        """
        return self._index_by_id[arc_id]

    def cost_of(self, arc_id):
        """Retorna o custo corrente de um arco.

        Args:
            arc_id: Identificador do arco direcionado.

        Returns:
            float: Custo corrente (minutos).
        """
        return self.costs[self._index_by_id[arc_id]]

    def set_cost(self, arc_id, cost):
        """Atualiza in-place o custo de um arco (D4).

        Args:
            arc_id: Identificador do arco direcionado.
            cost (float): Novo custo, não negativo (Dijkstra exige custo >= 0).

        Raises:
            ValueError: se `cost` for negativo.
        """
        value = float(cost)
        if value < 0.0:
            raise ValueError(f"Custo negativo não é admitido no Dijkstra: {value!r}.")
        self.costs[self._index_by_id[arc_id]] = value

    def update_costs(self, costs):
        """Atualiza in-place os custos de vários arcos de uma vez.

        Chamada a cada iteração do MSA com os custos realimentados pelo BPR.

        Args:
            costs (dict | list): {arc_id: custo} ou sequência de custos na
                mesma ordem de `arcs`.

        Raises:
            ValueError: se a sequência tiver tamanho diferente de `arcs` ou se
                algum custo for negativo.
        """
        if isinstance(costs, dict):
            for arc_id, cost in costs.items():
                self.set_cost(arc_id, cost)
            return

        costs = list(costs)
        if len(costs) != len(self.arcs):
            raise ValueError(
                f"Esperados {len(self.arcs)} custos, recebidos {len(costs)}."
            )
        for i, cost in enumerate(costs):
            value = float(cost)
            if value < 0.0:
                raise ValueError(f"Custo negativo não é admitido no Dijkstra: {value!r}.")
            self.costs[i] = value

    def reset_costs(self):
        """Devolve todos os custos ao tempo de fluxo livre (`t0`).

        Útil para rodar AoN e MSA sobre o mesmo grafo sem reconstruí-lo.
        """
        for i, arc in enumerate(self.arcs):
            self.costs[i] = float(arc.t0)

    def shortest_paths(self, origin, targets=None):
        """Roda um Dijkstra a partir de `origin` (uma execução por origem, D4).

        Usa `heapq` com remoção preguiçosa (entradas obsoletas são descartadas
        ao serem retiradas). Se `targets` for informado, encerra assim que
        todos os destinos pedidos estiverem fechados.

        Args:
            origin (tuple): Nó de origem.
            targets (iterable | None): Nós de destino de interesse; se None,
                varre o grafo inteiro.

        Returns:
            tuple: (dist, pred_arc)
                dist (dict): {nó: custo mínimo desde `origin`}; nós não
                    alcançados ficam de fora (equivalem a `INFINITY`).
                pred_arc (dict): {nó: índice do arco usado para chegar nele};
                    a origem não aparece. É o **predecessor-arco** que
                    `path_arcs` usa para remontar a rota.

        Raises:
            KeyError: se `origin` não pertencer ao grafo.
        """
        if origin not in self.adjacency:
            raise KeyError(f"Nó de origem fora do grafo: {origin!r}.")

        pending = set(targets) if targets is not None else None
        if pending is not None:
            pending.discard(origin)

        dist = {origin: 0.0}
        pred_arc = {}
        visited = set()
        heap = [(0.0, origin)]

        while heap:
            d, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)

            if pending is not None:
                pending.discard(node)
                if not pending:
                    break

            for i in self.adjacency[node]:
                arc = self.arcs[i]
                nxt = arc.to_node
                if nxt in visited:
                    continue
                candidate = d + self.costs[i]
                if candidate < dist.get(nxt, INFINITY):
                    dist[nxt] = candidate
                    pred_arc[nxt] = i
                    heapq.heappush(heap, (candidate, nxt))

        return dist, pred_arc

    def path_arcs(self, pred_arc, destination, origin=None):
        """Remonta a rota até `destination` como lista de arcos (D4).

        Args:
            pred_arc (dict): Predecessores-arco devolvidos por `shortest_paths`.
            destination (tuple): Nó de destino.
            origin (tuple | None): Nó de origem do Dijkstra. Informe-o para que
                o auto-par (origem == destino) devolva caminho vazio em vez de
                `None` — a origem nunca tem predecessor.

        Returns:
            list: Arcos, na ordem origem -> destino. Lista vazia se o destino
                for a própria origem; None se o destino for inalcançável
                (grafo desconexo), distinguindo os dois casos.
        """
        if destination in pred_arc:
            path = []
            node = destination
            while node in pred_arc:
                i = pred_arc[node]
                arc = self.arcs[i]
                path.append(arc)
                node = arc.from_node
            path.reverse()
            return path

        if origin is not None and destination == origin:
            return []

        return None

    def path_to(self, origin, destination):
        """Atalho de conveniência: Dijkstra de `origin` e rota até `destination`.

        Para vários destinos a partir da mesma origem, prefira chamar
        `shortest_paths` uma vez e `path_arcs` por destino — é justamente a
        economia de "1 Dijkstra por origem, não por par OD" (D4).

        Args:
            origin (tuple): Nó de origem.
            destination (tuple): Nó de destino.

        Returns:
            tuple: (arcos, custo). `arcos` é None e `custo` é `INFINITY` se o
                destino for inalcançável.
        """
        if origin == destination:
            return [], 0.0

        dist, pred_arc = self.shortest_paths(origin, targets=[destination])
        if destination not in dist:
            return None, INFINITY
        return self.path_arcs(pred_arc, destination), dist[destination]


def build_graph(arcs):
    """Constrói o grafo de roteamento a partir dos arcos direcionados.

    Args:
        arcs (iterable): Arcos de `network.build_network`, somados aos
            conectores de `network.connect_centroids`.

    Returns:
        Graph: Grafo pronto para o AoN e para as iterações do MSA.
    """
    return Graph(arcs)


__all__ = ['Graph', 'build_graph', 'INFINITY']
