# coding=utf-8
"""Módulo de alocação de tráfego em rodovias (D3, D4, D8, D10).

Implementa as funções de alocação de tráfego (BPR, AoN, MSA e Frank-Wolfe).
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


def _bpr_coeffs(arcs, alpha=0.15, beta=4.0):
    """Extrai os coeficientes (alpha, beta) do BPR por arco (D4).

    Para cada arco, usa `arc.params.get('bpr_alpha')` e `'bpr_beta'` quando presentes,
    senão recorre aos argumentos `alpha` e `beta` (arcos com `params={}` usam o global).

    Args:
        arcs (iterable): Coleção de arcos (`network.Arc` ou compatíveis).
        alpha (float): Valor global padrão de alpha (padrão 0.15).
        beta (float): Valor global padrão de beta (padrão 4.0).

    Returns:
        tuple: (alphas, betas) como listas de floats na mesma ordem de `arcs`.
    """
    g_alpha = 0.15 if alpha is None else float(alpha)
    g_beta = 4.0 if beta is None else float(beta)

    alphas = []
    betas = []
    for arc in arcs:
        params = getattr(arc, 'params', None) or {}
        a = params.get('bpr_alpha')
        b = params.get('bpr_beta')
        try:
            a_val = float(a) if a is not None else g_alpha
        except (ValueError, TypeError):
            a_val = g_alpha
        try:
            b_val = float(b) if b is not None else g_beta
        except (ValueError, TypeError):
            b_val = g_beta
        alphas.append(a_val)
        betas.append(b_val)
    return alphas, betas


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
        zone_node (dict | callable | None): Mapeamento `zone_id -> nó` de
            `network.anchor_centroids` — o nó virtual
            `(network.CONNECTOR_LINK_ID, zone_id)`, de onde o Dijkstra parte
            pelo conector. Se None ou se a zona não constar no
            dicionário/mapeamento, assume que `o_zone` e `d_zone` já são nós
            do grafo.

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
    alphas, betas = _bpr_coeffs(arcs, alpha=alpha, beta=beta)

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
            bpr_time(t0_costs[i], v_current[i], capacities[i], alpha=alphas[i], beta=betas[i])
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


def _beckmann_derivative(lam, v, y, t0_costs, capacities, alphas, betas):
    """Calcula a derivada da função de Beckmann ao longo da direção (y - v).

    d/dλ Σ ∫_0^{v_a + λ(y_a - v_a)} t_a(w) dw = Σ t_a(v_a + λ(y_a - v_a)) · (y_a - v_a)

    `alphas` e `betas` são sequências de coeficientes BPR indexadas por arco.
    """
    total = 0.0
    for i in range(len(v)):
        diff = y[i] - v[i]
        if diff == 0.0:
            continue
        v_lam = v[i] + lam * diff
        a = alphas[i]
        b = betas[i]
        t_lam = bpr_time(t0_costs[i], v_lam, capacities[i], alpha=a, beta=b)
        total += t_lam * diff
    return total


def _line_search_fw(v, y, t0_costs, capacities, alphas, betas, max_evals=30):
    """Busca linear por bisseção de λ ∈ [0, 1] na derivada da função de Beckmann (D3).

    Como o custo de viagem BPR é não-decrescente em relação ao volume, a derivada
    é monotonicamente não-decrescente em λ.
    """
    d0 = _beckmann_derivative(0.0, v, y, t0_costs, capacities, alphas=alphas, betas=betas)
    if d0 >= 0.0:
        return 0.0
    d1 = _beckmann_derivative(1.0, v, y, t0_costs, capacities, alphas=alphas, betas=betas)
    if d1 <= 0.0:
        return 1.0

    low = 0.0
    high = 1.0
    for _ in range(max_evals):
        mid = (low + high) * 0.5
        d_mid = _beckmann_derivative(mid, v, y, t0_costs, capacities, alphas=alphas, betas=betas)
        if d_mid < 0.0:
            low = mid
        else:
            high = mid
    return (low + high) * 0.5


def assign_fw(
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
    """Executa a alocação de Equilíbrio via Frank-Wolfe (FW) + BPR (D3).

    Iteração: AoN em t0 -> a cada k: tempos BPR em v, AoN auxiliar y, gap relativo
    (mesma fórmula do MSA), para se 0 <= gap <= gap_tol; senão busca linear por
    bisseção de λ ∈ [0, 1] na derivada da função de Beckmann (30 bisseções),
    v ← v + λ(y - v).

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
    alphas, betas = _bpr_coeffs(arcs, alpha=alpha, beta=beta)

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
            bpr_time(t0_costs[i], v_current[i], capacities[i], alpha=alphas[i], beta=betas[i])
            for i in range(num_arcs)
        ]

        # 2. Carrega fluxo auxiliar (AoN) sobre os tempos correntes
        f_aux, last_stats = aon_load(
            graph, custos=current_times, od_pairs=od_pairs, zone_node=zone_node
        )

        # 3. Gap relativo (mesma fórmula do MSA)
        sum_v_t = sum(v_current[i] * current_times[i] for i in range(num_arcs))
        sum_f_t = sum(f_aux[i] * current_times[i] for i in range(num_arcs))
        gap = (sum_v_t - sum_f_t) / sum_v_t if sum_v_t > 0.0 else 0.0

        if gap is not None and 0.0 <= gap <= gap_tol:
            historico.append({'iter': k, 'max_diff': 0.0, 'gap': gap})
            if callable(progress):
                progress(k, max_iter)
            break

        # 4. Busca linear por bisseção de lambda em [0, 1] (30 bisseções)
        lam = _line_search_fw(
            v_current, f_aux, t0_costs, capacities, alphas=alphas, betas=betas, max_evals=30
        )
        v_next = [
            v_current[i] + lam * (f_aux[i] - v_current[i])
            for i in range(num_arcs)
        ]

        max_diff = max(
            (abs(v_next[i] - v_current[i]) for i in range(num_arcs)), default=0.0
        )
        historico.append({'iter': k, 'max_diff': max_diff, 'gap': gap})

        v_current = v_next

        if callable(progress):
            progress(k, max_iter)

    stats = dict(last_stats)
    stats['gap'] = historico[-1]['gap']
    stats['method'] = 'fw'
    stats['metodo'] = 'fw'
    stats['iterations'] = len(historico)
    stats['iteracoes'] = len(historico)

    return v_current, historico, stats


VALID_METHODS = ('aon', 'msa', 'fw')


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

    Despacha para `assign_aon`, `assign_msa` ou `assign_fw` conforme `method`, mas os três
    devolvem sempre a mesma tripla `(fluxos, historico, stats)` — é seguro
    trocar de método sem mudar o código que consome o resultado.

    Args:
        graph (Graph): Grafo direcionado.
        arcs (list | None): Lista de arcos na mesma ordem do grafo. Se None, usa `graph.arcs`.
        od_pairs (iterable | None): Pares OD com demandas.
        method (str): Método de alocação, um de `VALID_METHODS` ('aon', 'msa' ou 'fw'). Padrão 'msa'.
        zone_node (dict | callable | None): Mapeamento de centróides para nós da rede.
        max_iter (int): Número máximo de iterações (para MSA e FW; ignorado no AoN).
        gap_tol (float): Tolerância de parada do gap (para MSA e FW; ignorado no AoN).
        alpha (float): Parâmetro alpha do BPR (para MSA e FW; ignorado no AoN).
        beta (float): Parâmetro beta do BPR (para MSA e FW; ignorado no AoN).
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

    if method_norm == 'fw':
        return assign_fw(
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


__all__ = [
    'bpr_time',
    'aon_load',
    'assign_aon',
    'assign_msa',
    'assign_fw',
    'assign',
    'VALID_METHODS',
]

