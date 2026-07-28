# coding=utf-8
"""Módulo de alocação de tráfego em rodovias (D4, D8, D10).

Implementa as funções de alocação de tráfego (BPR e AoN).
"""


def bpr_time(t0, v, c, alpha=0.15, beta=4.0):
    """Calcula o tempo de viagem BPR (Bureau of Public Roads) para um arco.

    Fórmula: t = t0 * (1 + alpha * (v / c) ** beta)

    Args:
        t0 (float): Tempo de viagem a fluxo livre em minutos.
        v (float): Volume/fluxo alocado no arco (veíc/h).
        c (float): Capacidade do arco (veíc/h).
        alpha (float): Parâmetro alpha do BPR (padrão 0.15).
        beta (float): Parâmetro beta do BPR (padrão 4.0).

    Returns:
        float: Tempo de viagem ajustado pelo congestionamento.
    """
    t0 = float(t0)
    v = float(v)
    c = float(c)
    alpha = float(alpha)
    beta = float(beta)

    if v <= 0.0:
        return t0

    if c <= 0.0:
        # Quando a capacidade é <= 0 e v > 0, trata a capacidade com um valor mínimo positivo
        # para evitar divisão por zero, resultando em penalização alta e definida.
        c = 1e-6

    return t0 * (1.0 + alpha * ((v / c) ** beta))


def aon_load(graph, custos=None, od_pairs=None, zone_node=None):
    """Executa uma passada All-or-Nothing (AoN) sobre o grafo com os custos dados.

    Para cada par Origem-Destino, encontra o caminho mínimo pelo Dijkstra no grafo e
    carrega 100% do fluxo do par sobre os arcos do caminho mínimo (D4, D10).

    Args:
        graph (Graph): Grafo direcionado de `traffic/graph.py`.
        custos (dict | list | None): Custos correntes por arco para esta passada.
            Se informado, atualiza os custos no `graph`. Se None, usa `graph.costs`.
        od_pairs (iterable | None): Lista ou iterável de pares OD. Aceita:
            - tuplas `(o_zone, d_zone, flow)`
            - tuplas `((o_zone, d_zone), flow)`
            - dict `{(o_zone, d_zone): flow}`
        zone_node (dict | callable | None): Mapeamento `zone_id -> node_key (x, y)`
            de `network.connect_centroids`. Se None ou se a zona não constar no
            dicionário/mapeamento, assume que `o_zone` e `d_zone` já são as tuplas `(x, y)`.

    Returns:
        tuple: (flows, stats)
            flows (list): Lista de floats com o fluxo acumulado por arco, na mesma
                ordem de `graph.arcs`.
            stats (dict): Contadores dos pares OD:
                - `'allocated'`: pares com rota encontrada e fluxo alocado.
                - `'unreachable'`: pares com nó de origem e destino na rede, mas sem rota.
                - `'ignored'`: pares com fluxo <= 0, origem == destino ou sem nó na rede.
    """
    if custos is not None:
        graph.update_costs(custos)

    num_arcs = len(graph.arcs)
    flows = [0.0] * num_arcs

    allocated = 0
    unreachable = 0
    ignored = 0

    if not od_pairs:
        stats = {
            'allocated': 0,
            'unreachable': 0,
            'ignored': 0,
            'alocados': 0,
            'inalcancaveis': 0,
            'ignorados': 0,
        }
        return flows, stats

    # Normaliza od_pairs em uma lista de (o_zone, d_zone, flow)
    normalized_od = []
    if isinstance(od_pairs, dict):
        for key, val in od_pairs.items():
            if isinstance(key, (tuple, list)) and len(key) >= 2:
                normalized_od.append((key[0], key[1], float(val)))
    else:
        for item in od_pairs:
            if isinstance(item, (tuple, list)):
                if len(item) == 3:
                    normalized_od.append((item[0], item[1], float(item[2])))
                elif len(item) == 2:
                    if isinstance(item[0], (tuple, list)) and len(item[0]) >= 2:
                        normalized_od.append((item[0][0], item[0][1], float(item[1])))
                    else:
                        normalized_od.append((item[0], item[1], 1.0))

    # Função auxiliar para resolver nó da zona
    def resolve_node(z):
        if zone_node is None:
            return z
        if callable(zone_node):
            return zone_node(z)
        if isinstance(zone_node, dict):
            return zone_node.get(z)
        return getattr(zone_node, 'get', lambda k: None)(z)

    # Agrupa por origem para rodar 1 Dijkstra por origem (D4)
    by_origin = {}
    for o_zone, d_zone, flow in normalized_od:
        by_origin.setdefault(o_zone, []).append((d_zone, flow))

    for o_zone, dest_list in by_origin.items():
        u = resolve_node(o_zone)
        if u is None or not graph.has_node(u):
            ignored += len(dest_list)
            continue

        # Coleta destinos válidos que pertencem ao grafo
        valid_dest_nodes = set()
        for d_zone, flow in dest_list:
            if flow <= 0.0:
                continue
            v = resolve_node(d_zone)
            if v is not None and graph.has_node(v) and v != u:
                valid_dest_nodes.add(v)

        # Se houver alvos válidos, roda Dijkstra de u até fechar todos os alvos
        dist, pred_arc = graph.shortest_paths(u, targets=valid_dest_nodes) if valid_dest_nodes else ({}, {})

        for d_zone, flow in dest_list:
            if flow <= 0.0:
                ignored += 1
                continue

            v = resolve_node(d_zone)
            if v is None or not graph.has_node(v) or v == u:
                ignored += 1
                continue

            path = graph.path_arcs(pred_arc, v, origin=u)
            if path is None:
                unreachable += 1
            else:
                for arc in path:
                    idx = graph.index_of(arc.arc_id)
                    flows[idx] += flow
                allocated += 1

    stats = {
        'allocated': allocated,
        'unreachable': unreachable,
        'ignored': ignored,
        'alocados': allocated,
        'inalcancaveis': unreachable,
        'ignorados': ignored,
    }
    return flows, stats


def assign_aon(graph, arcs=None, od_pairs=None, zone_node=None, progress=None):
    """Executa a alocação All-or-Nothing (AoN) sobre a rede.

    Uma passada sobre os custos de fluxo livre (t0). Todo o fluxo de cada par OD
    vai pelo menor caminho, sem realimentar congestionamento.

    Args:
        graph (Graph): Grafo direcionado de `traffic/graph.py`.
        arcs (list | None): Lista de arcos na mesma ordem do grafo. Se None, usa `graph.arcs`.
        od_pairs (iterable | None): Pares OD com demandas.
        zone_node (dict | callable | None): Mapeamento de centróides para nós da rede.
        progress (callable | None): Se informado, chamado como `progress(iter, max_iter)`.

    Returns:
        tuple: (flows, historico, stats)
            - flows (list): Lista de floats com os fluxos por arco.
            - historico (list): Lista com dicionário de status da iteração.
            - stats (dict): Estatísticas acumuladas da alocação.
    """
    if arcs is None:
        arcs = graph.arcs

    t0_costs = [float(arc.t0) for arc in arcs]
    flows, stats = aon_load(graph, custos=t0_costs, od_pairs=od_pairs, zone_node=zone_node)

    if callable(progress):
        progress(1, 1)

    historico = [{'iter': 1, 'max_diff': 0.0, 'gap': None}]
    stats = dict(stats)
    stats['gap'] = None
    stats['method'] = 'aon'
    stats['metodo'] = 'aon'
    stats['iterations'] = 1
    stats['iteracoes'] = 1

    return flows, historico, stats


def assign_msa(
    graph,
    arcs=None,
    od_pairs=None,
    zone_node=None,
    max_iter=10,
    gap_tol=0.01,
    alpha=0.15,
    beta=4.0,
    progress=None,
):
    """Executa a alocação de Equilíbrio via MSA (Method of Successive Averages) + BPR.

    Itera AoN sobre custos atualizados pela relação fluxo/capacidade (BPR),
    distribuindo o tráfego entre rotas concorrentes.

    Args:
        graph (Graph): Grafo direcionado.
        arcs (list | None): Lista de arcos na mesma ordem do grafo. Se None, usa `graph.arcs`.
        od_pairs (iterable | None): Pares OD com demandas.
        zone_node (dict | callable | None): Mapeamento de centróides para nós da rede.
        max_iter (int): Número máximo de iterações (padrão 10).
        gap_tol (float): Tolerância de parada para o gap relativo (padrão 0.01).
        alpha (float): Parâmetro alpha do BPR (padrão 0.15).
        beta (float): Parâmetro beta do BPR (padrão 4.0).
        progress (callable | None): Se informado, chamado como `progress(iter, max_iter)`
            a cada iteração.

    Returns:
        tuple: (flows, historico, stats)
            - flows (list): Lista de floats com os fluxos equilibrados por arco.
            - historico (list): Dicionários por iteração com {'iter', 'max_diff', 'gap'}.
            - stats (dict): Estatísticas da última iteração.
    """
    if arcs is None:
        arcs = graph.arcs

    num_arcs = len(arcs)
    t0_costs = [float(arc.t0) for arc in arcs]
    capacities = [float(arc.capacity) for arc in arcs]

    # Iteração 1: AoN em t0
    v_current, last_stats = aon_load(
        graph, custos=t0_costs, od_pairs=od_pairs, zone_node=zone_node
    )
    historico = [{'iter': 1, 'max_diff': 0.0, 'gap': None}]

    if callable(progress):
        progress(1, max_iter)

    for k in range(2, max_iter + 1):
        # 1. Calcula tempos correntes BPR com v_current
        current_times = [
            bpr_time(t0_costs[i], v_current[i], capacities[i], alpha=alpha, beta=beta)
            for i in range(num_arcs)
        ]

        # 2. Carrega fluxo auxiliar (AoN) sobre os tempos correntes
        f_aux, last_stats = aon_load(
            graph, custos=current_times, od_pairs=od_pairs, zone_node=zone_node
        )

        # 3. Atualiza fluxos via MSA: V_k = V_{k-1} + (F_k - V_{k-1}) / k
        step_size = 1.0 / float(k)
        v_next = [
            v_current[i] + step_size * (f_aux[i] - v_current[i])
            for i in range(num_arcs)
        ]

        # 4. Métricas de convergência
        max_diff = max(
            (abs(v_next[i] - v_current[i]) for i in range(num_arcs)), default=0.0
        )

        sum_v_t = sum(v_current[i] * current_times[i] for i in range(num_arcs))
        sum_f_t = sum(f_aux[i] * current_times[i] for i in range(num_arcs))
        gap = (sum_v_t - sum_f_t) / sum_v_t if sum_v_t > 0.0 else 0.0

        historico.append({'iter': k, 'max_diff': max_diff, 'gap': gap})

        v_current = v_next

        if callable(progress):
            progress(k, max_iter)

        if gap is not None and 0.0 <= gap <= gap_tol:
            break

    stats = dict(last_stats)
    stats['gap'] = historico[-1]['gap']
    stats['method'] = 'msa'
    stats['metodo'] = 'msa'
    stats['iterations'] = len(historico)
    stats['iteracoes'] = len(historico)

    return v_current, historico, stats


VALID_METHODS = ('aon', 'msa')


def assign(
    graph,
    arcs=None,
    od_pairs=None,
    method='msa',
    zone_node=None,
    max_iter=10,
    gap_tol=0.01,
    alpha=0.15,
    beta=4.0,
    progress=None,
):
    """Ponto de entrada único para alocação de tráfego na rede (D10).

    Despacha para `assign_aon` ou `assign_msa` conforme `method`, mas os dois
    devolvem sempre a mesma tripla `(fluxos, historico, stats)` — é seguro
    trocar de método sem mudar o código que consome o resultado.

    Args:
        graph (Graph): Grafo direcionado.
        arcs (list | None): Lista de arcos na mesma ordem do grafo. Se None, usa `graph.arcs`.
        od_pairs (iterable | None): Pares OD com demandas.
        method (str): Método de alocação, um de `VALID_METHODS` ('aon' ou 'msa'). Padrão 'msa'.
        zone_node (dict | callable | None): Mapeamento de centróides para nós da rede.
        max_iter (int): Número máximo de iterações (para MSA; ignorado no AoN).
        gap_tol (float): Tolerância de parada do gap (para MSA; ignorado no AoN).
        alpha (float): Parâmetro alpha do BPR (para MSA; ignorado no AoN).
        beta (float): Parâmetro beta do BPR (para MSA; ignorado no AoN).
        progress (callable | None): Se informado, chamado como `progress(iter, max_iter)`.

    Returns:
        tuple: (flows, historico, stats)

    Raises:
        ValueError: Se `method` não estiver em `VALID_METHODS`.
    """
    method_norm = str(method).lower() if method else 'msa'
    if method_norm not in VALID_METHODS:
        raise ValueError(
            "Método de alocação desconhecido: {!r}. Métodos válidos: {}".format(
                method, ', '.join(VALID_METHODS)
            )
        )

    if method_norm == 'aon':
        return assign_aon(graph, arcs=arcs, od_pairs=od_pairs, zone_node=zone_node, progress=progress)

    return assign_msa(
        graph,
        arcs=arcs,
        od_pairs=od_pairs,
        zone_node=zone_node,
        max_iter=max_iter,
        gap_tol=gap_tol,
        alpha=alpha,
        beta=beta,
        progress=progress,
    )


__all__ = ['bpr_time', 'aon_load', 'assign_aon', 'assign_msa', 'assign', 'VALID_METHODS']

