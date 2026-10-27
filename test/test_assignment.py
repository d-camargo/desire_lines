# coding=utf-8
import unittest
from desire_lines.traffic.network import Arc
from desire_lines.traffic.graph import build_graph
from desire_lines.traffic.assignment import (
    bpr_time,
    aon_load,
    assign_aon,
    assign_msa,
    assign_fw,
    assign,
    VALID_METHODS,
    _bpr_coeffs,
)


class TestBprTime(unittest.TestCase):
    """Testes para a função bpr_time (passo 12)."""

    def test_bpr_time_zero_flow(self):
        """BPR em v=0 devolve t0."""
        self.assertEqual(bpr_time(10.0, 0, 1000), 10.0)

    def test_bpr_time_capacity_flow(self):
        """BPR em v=c devolve 1.15*t0 com alpha=0.15 e beta=4.0."""
        self.assertAlmostEqual(bpr_time(10.0, 1000, 1000), 11.5, places=5)

    def test_bpr_time_zero_capacity(self):
        """Trata c <= 0 de forma definida sem levantar exceção."""
        self.assertEqual(bpr_time(10.0, 0, 0), 10.0)
        t_congested = bpr_time(10.0, 100, 0)
        self.assertGreater(t_congested, 10.0)

    def test_bpr_time_custom_params(self):
        """Testa parâmetros alpha e beta personalizados."""
        res = bpr_time(20.0, 500, 1000, alpha=0.2, beta=2.0)
        # 20.0 * (1 + 0.2 * (0.5)^2) = 20.0 * (1 + 0.05) = 21.0
        self.assertAlmostEqual(res, 21.0, places=5)


class TestAonLoad(unittest.TestCase):
    """Testes para a função aon_load (passo 12)."""

    def setUp(self):
        """Monta uma rede diamante para testes.

        Nós: A=(0,0), B=(10,0), C=(5,5), D=(5,-5)
        Caminho 1 (norte): A -> C -> B (custo total t0 10.0 + 10.0 = 20.0)
        Caminho 2 (sul):   A -> D -> B (custo total t0 5.0 + 5.0 = 10.0)
        """
        self.nA = (0.0, 0.0)
        self.nB = (10.0, 0.0)
        self.nC = (5.0, 5.0)
        self.nD = (5.0, -5.0)

        # Arcos caminho norte
        self.arc1 = Arc("a1", "L1", self.nA, self.nC, 50.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        self.arc2 = Arc("a2", "L2", self.nC, self.nB, 50.0, 10.0, 1000.0, "rodoviario", {}, {}, [])

        # Arcos caminho sul (mais rápido a fluxo livre)
        self.arc3 = Arc("a3", "L3", self.nA, self.nD, 50.0, 5.0, 1000.0, "rodoviario", {}, {}, [])
        self.arc4 = Arc("a4", "L4", self.nD, self.nB, 50.0, 5.0, 1000.0, "rodoviario", {}, {}, [])

        self.arcs = [self.arc1, self.arc2, self.arc3, self.arc4]
        self.graph = build_graph(self.arcs)

    def test_aon_load_allocates_to_shortest_path(self):
        """`aon_load` põe todo o fluxo do par no caminho mínimo."""
        od_pairs = [(self.nA, self.nB, 500.0)]
        flows, stats = aon_load(self.graph, od_pairs=od_pairs)

        # Caminho sul (a3, a4) deve receber 500.0
        # Caminho norte (a1, a2) deve receber 0.0
        self.assertEqual(flows, [0.0, 0.0, 500.0, 500.0])
        self.assertEqual(stats['allocated'], 1)
        self.assertEqual(stats['unreachable'], 0)
        self.assertEqual(stats['ignored'], 0)

    def test_aon_load_unreachable_destination(self):
        """Conta pares sem rota sem levantar exceção."""
        n_isolated = (99.0, 99.0)
        # Adiciona um nó isolado criando um arco fake até ele sem volta
        isolated_arc = Arc("a_iso", "L_iso", self.nA, n_isolated, 10.0, 5.0, 1000.0, "rodoviario", {}, {}, [])
        graph = build_graph(self.arcs + [isolated_arc])

        # Par de n_isolated para nB (não há arco saindo de n_isolated)
        od_pairs = [(n_isolated, self.nB, 300.0)]
        flows, stats = aon_load(graph, od_pairs=od_pairs)

        self.assertEqual(stats['allocated'], 0)
        self.assertEqual(stats['unreachable'], 1)
        self.assertEqual(stats['ignored'], 0)

    def test_aon_load_ignored_pairs(self):
        """Pares com fluxo <= 0, origem == destino ou fora do grafo são ignorados."""
        od_pairs = [
            (self.nA, self.nA, 100.0),        # Origem == Destino
            (self.nA, self.nB, 0.0),          # Fluxo zero
            ((999.0, 999.0), self.nB, 50.0), # Nó origem fora do grafo
        ]
        flows, stats = aon_load(self.graph, od_pairs=od_pairs)
        self.assertEqual(stats['allocated'], 0)
        self.assertEqual(stats['unreachable'], 0)
        self.assertEqual(stats['ignored'], 3)
        self.assertEqual(sum(flows), 0.0)

    def test_aon_load_with_zone_node_dict(self):
        """Suporta zone_node como dict de mapeamento de centróide para nó da rede."""
        zone_node = {0: self.nA, 1: self.nB}
        od_pairs = [(0, 1, 250.0)]

        flows, stats = aon_load(self.graph, od_pairs=od_pairs, zone_node=zone_node)
        self.assertEqual(flows, [0.0, 0.0, 250.0, 250.0])
        self.assertEqual(stats['allocated'], 1)

    def test_aon_load_custom_custos(self):
        """Passando custos customizados altera a escolha de rota."""
        # Aumenta o custo do caminho sul (a3, a4) para 30.0 cada
        custos = {"a1": 10.0, "a2": 10.0, "a3": 30.0, "a4": 30.0}
        od_pairs = [(self.nA, self.nB, 400.0)]

        flows, stats = aon_load(self.graph, custos=custos, od_pairs=od_pairs)
        # Agora o caminho norte (a1, a2) é o mais rápido (20.0 < 60.0)
        self.assertEqual(flows, [400.0, 400.0, 0.0, 0.0])
        self.assertEqual(stats['allocated'], 1)


class TestAssign(unittest.TestCase):
    """Testes para a função assign, assign_aon e assign_msa (passo 13)."""

    def setUp(self):
        """Rede diamante:
        Caminho Norte (a1, a2): t0=10.0 + 10.0 = 20.0, capacidade=1000
        Caminho Sul (a3, a4): t0=5.0 + 5.0 = 10.0, capacidade=1000
        """
        self.nA = (0.0, 0.0)
        self.nB = (10.0, 0.0)
        self.nC = (5.0, 5.0)
        self.nD = (5.0, -5.0)

        self.arc1 = Arc("a1", "L1", self.nA, self.nC, 50.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        self.arc2 = Arc("a2", "L2", self.nC, self.nB, 50.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        self.arc3 = Arc("a3", "L3", self.nA, self.nD, 50.0, 5.0, 1000.0, "rodoviario", {}, {}, [])
        self.arc4 = Arc("a4", "L4", self.nD, self.nB, 50.0, 5.0, 1000.0, "rodoviario", {}, {}, [])

        self.arcs = [self.arc1, self.arc2, self.arc3, self.arc4]
        self.graph = build_graph(self.arcs)

    def test_assign_aon(self):
        """assign_aon aloca no caminho mais curto sem iteração de congestionamento."""
        od_pairs = [(self.nA, self.nB, 600.0)]
        flows, historico, stats = assign_aon(self.graph, od_pairs=od_pairs)

        self.assertEqual(flows, [0.0, 0.0, 600.0, 600.0])
        self.assertEqual(len(historico), 1)
        self.assertEqual(stats['method'], 'aon')
        self.assertIsNone(stats['gap'])

    def test_assign_msa_shifts_flow_under_congestion(self):
        """assign_msa distribui o tráfego entre rotas com o congestionamento BPR."""
        # Demanda alta (5000) congestionará o caminho sul
        od_pairs = [(self.nA, self.nB, 5000.0)]
        flows, historico, stats = assign_msa(self.graph, od_pairs=od_pairs, max_iter=5)

        self.assertGreater(len(historico), 1)
        self.assertEqual(stats['method'], 'msa')
        # Com o caminho sul muito congestionado na iter 1, a iter 2 coloca fluxo no caminho norte
        # Ambos os caminhos devem terminar com fluxo positivo
        self.assertGreater(flows[0], 0.0)
        self.assertGreater(flows[2], 0.0)
        self.assertAlmostEqual(sum(flows), 10000.0, places=2)  # 2 arcos por caminho * 5000 no total

    def test_assign_method_dispatch(self):
        """`assign` despacha corretamente entre métodos 'aon', 'msa' e 'fw' (D3, D10)."""
        od_pairs = [(self.nA, self.nB, 400.0)]

        flows_aon, hist_aon, stats_aon = assign(self.graph, od_pairs=od_pairs, method='aon')
        self.assertEqual(stats_aon['metodo'], 'aon')
        self.assertEqual(stats_aon['method'], 'aon')
        self.assertIsNone(stats_aon['gap'])
        self.assertEqual(stats_aon['iteracoes'], 1)
        # AoN concentra 100% no caminho barato (sul: a3, a4)
        self.assertEqual(flows_aon, [0.0, 0.0, 400.0, 400.0])

        flows_msa, hist_msa, stats_msa = assign(self.graph, od_pairs=od_pairs, method='msa', max_iter=3)
        self.assertEqual(stats_msa['metodo'], 'msa')
        self.assertEqual(stats_msa['method'], 'msa')

        flows_fw, hist_fw, stats_fw = assign(self.graph, od_pairs=od_pairs, method='fw', max_iter=3)
        self.assertEqual(stats_fw['metodo'], 'fw')
        self.assertEqual(stats_fw['method'], 'fw')

        # Mesmas chaves de stats em todos os métodos
        self.assertEqual(set(stats_aon.keys()), set(stats_msa.keys()))
        self.assertEqual(set(stats_msa.keys()), set(stats_fw.keys()))

    def test_assign_fw_two_parallel_routes_analytical_equilibrium(self):
        """FW converge para <= 0,5% do volume analítico em rede de 2 rotas paralelas em <= 50 it."""
        nA = (0.0, 0.0)
        nB = (10.0, 0.0)
        # Rota 1: t0=23.0, cap=1000.0; Rota 2: t0=68.0, cap=1000.0
        # Demanda D = 3000.0 de nA para nB
        # Solução analítica de equilíbrio (BPR alpha=0.15, beta=4.0):
        # v1* = 2000.0, v2* = 1000.0
        # t1(2000) = 23.0 * (1 + 0.15 * (2000/1000)^4) = 23.0 * 3.4 = 78.2
        # t2(1000) = 68.0 * (1 + 0.15 * (1000/1000)^4) = 68.0 * 1.15 = 78.2
        # Tempos exatamente iguais a 78.2 minutos nas duas rotas.
        arc1 = Arc("a1", "L1", nA, nB, 10.0, 23.0, 1000.0, "rodoviario", {}, {}, [])
        arc2 = Arc("a2", "L2", nA, nB, 10.0, 68.0, 1000.0, "rodoviario", {}, {}, [])
        graph = build_graph([arc1, arc2])
        od_pairs = [(nA, nB, 3000.0)]

        flows_fw, historico_fw, stats_fw = assign_fw(graph, od_pairs=od_pairs, max_iter=50)

        v1_analitico = 2000.0
        v2_analitico = 1000.0
        err1 = abs(flows_fw[0] - v1_analitico) / v1_analitico
        err2 = abs(flows_fw[1] - v2_analitico) / v2_analitico

        self.assertLessEqual(err1, 0.005)  # <= 0,5 % do volume analítico
        self.assertLessEqual(err2, 0.005)  # <= 0,5 % do volume analítico
        self.assertLessEqual(stats_fw['iterations'], 50)

        # Tempos iguais nas duas rotas sob o fluxo encontrado
        t1 = bpr_time(23.0, flows_fw[0], 1000.0)
        t2 = bpr_time(68.0, flows_fw[1], 1000.0)
        self.assertAlmostEqual(t1, t2, delta=0.5)

    def test_assign_fw_gap_less_or_equal_msa(self):
        """Com o mesmo max_iter, o gap final do FW é <= o do MSA."""
        nA = (0.0, 0.0)
        nB = (10.0, 0.0)
        arc1 = Arc("a1", "L1", nA, nB, 10.0, 23.0, 1000.0, "rodoviario", {}, {}, [])
        arc2 = Arc("a2", "L2", nA, nB, 10.0, 68.0, 1000.0, "rodoviario", {}, {}, [])
        graph = build_graph([arc1, arc2])
        od_pairs = [(nA, nB, 3000.0)]

        _, _, stats_fw = assign(graph, od_pairs=od_pairs, method='fw', max_iter=3, gap_tol=1e-9)
        _, _, stats_msa = assign(graph, od_pairs=od_pairs, method='msa', max_iter=3, gap_tol=1e-9)
        self.assertIsNotNone(stats_fw['gap'])
        self.assertIsNotNone(stats_msa['gap'])
        self.assertLessEqual(stats_fw['gap'], stats_msa['gap'])

        # Também na rede diamante com congestionamento
        od_diamond = [(self.nA, self.nB, 5000.0)]
        _, _, stats_fw_d = assign(self.graph, od_pairs=od_diamond, method='fw', max_iter=5, gap_tol=1e-9)
        _, _, stats_msa_d = assign(self.graph, od_pairs=od_diamond, method='msa', max_iter=5, gap_tol=1e-9)
        self.assertLessEqual(stats_fw_d['gap'], stats_msa_d['gap'])

    def test_assign_fw_contract_and_progress(self):
        """Contrato da tripla (flows, historico, stats) de FW é idêntico ao do MSA."""
        od_pairs = [(self.nA, self.nB, 2000.0)]
        progress_calls = []

        def on_progress(k, total):
            progress_calls.append((k, total))

        flows_fw, hist_fw, stats_fw = assign_fw(
            self.graph, od_pairs=od_pairs, max_iter=4, progress=on_progress
        )
        flows_msa, hist_msa, stats_msa = assign_msa(self.graph, od_pairs=od_pairs, max_iter=4)

        # 1. flows
        self.assertIsInstance(flows_fw, list)
        self.assertEqual(len(flows_fw), len(self.graph.arcs))
        self.assertTrue(all(isinstance(v, float) for v in flows_fw))

        # 2. historico
        self.assertIsInstance(hist_fw, list)
        self.assertGreaterEqual(len(hist_fw), 1)
        self.assertEqual(hist_fw[0]['iter'], 1)
        self.assertEqual(hist_fw[0]['max_diff'], 0.0)
        self.assertIsNone(hist_fw[0]['gap'])
        for h in hist_fw[1:]:
            self.assertIn('iter', h)
            self.assertIn('max_diff', h)
            self.assertIn('gap', h)

        # 3. stats
        self.assertIsInstance(stats_fw, dict)
        self.assertEqual(stats_fw['method'], 'fw')
        self.assertEqual(stats_fw['metodo'], 'fw')
        self.assertEqual(stats_fw['iterations'], len(hist_fw))
        self.assertEqual(stats_fw['iteracoes'], len(hist_fw))
        self.assertEqual(stats_fw['gap'], hist_fw[-1]['gap'])
        self.assertEqual(set(stats_fw.keys()), set(stats_msa.keys()))

        # 4. progress(k, max_iter)
        self.assertTrue(len(progress_calls) >= 1)
        self.assertEqual(progress_calls[0], (1, 4))
        for k, total in progress_calls:
            self.assertEqual(total, 4)
            self.assertGreaterEqual(k, 1)

    def test_assign_invalid_method_raises(self):
        """`assign` levanta ValueError com a lista de métodos válidos."""
        od_pairs = [(self.nA, self.nB, 400.0)]

        with self.assertRaises(ValueError) as ctx:
            assign(self.graph, od_pairs=od_pairs, method='bogus')

        for metodo in VALID_METHODS:
            self.assertIn(metodo, str(ctx.exception))

    def test_assign_bpr_beta_per_arc_shifts_equilibrium(self):
        """Duas rotas idênticas exceto params['bpr_beta'] em uma alteram o equilíbrio (D4).

        Arco com params={} recorre aos coeficientes globais.
        """
        nA = (0.0, 0.0)
        nB = (10.0, 0.0)
        # 1. Caso base global: 2 rotas idênticas com params={}
        # Capacidade=1000.0, t0=10.0, demanda=3000.0
        arc1_glob = Arc("a1", "L1", nA, nB, 10.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        arc2_glob = Arc("a2", "L2", nA, nB, 10.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        graph_glob = build_graph([arc1_glob, arc2_glob])
        od_pairs = [(nA, nB, 3000.0)]

        flows_glob_fw, _, _ = assign_fw(graph_glob, od_pairs=od_pairs, max_iter=30)
        # Por simetria, no equilíbrio global de Frank-Wolfe cada rota recebe exatamente metade (1500)
        self.assertAlmostEqual(flows_glob_fw[0], 1500.0, delta=1.0)
        self.assertAlmostEqual(flows_glob_fw[1], 1500.0, delta=1.0)

        # 2. Rota 1 com bpr_beta=2.0 e Rota 2 com params={} (usa global beta=4.0)
        arc1_custom = Arc("a1", "L1", nA, nB, 10.0, 10.0, 1000.0, "rodoviario", {'bpr_beta': 2.0}, {}, [])
        arc2_default = Arc("a2", "L2", nA, nB, 10.0, 10.0, 1000.0, "rodoviario", {}, {}, [])
        graph_custom = build_graph([arc1_custom, arc2_default])

        flows_cust_fw, _, _ = assign_fw(graph_custom, od_pairs=od_pairs, max_iter=50)
        flows_cust_msa, _, _ = assign_msa(graph_custom, od_pairs=od_pairs, max_iter=50)

        # O equilíbrio muda significativamente em relação ao global:
        # Rota 1 penaliza menos o congestionamento (beta=2 < 4), logo atrai mais fluxo (> 1500)
        self.assertGreater(flows_cust_fw[0], flows_glob_fw[0] + 150.0)
        self.assertLess(flows_cust_fw[1], flows_glob_fw[1] - 150.0)
        self.assertGreater(flows_cust_msa[0], 1600.0)
        self.assertLess(flows_cust_msa[1], 1400.0)

        # Solução analítica com beta1=2 e beta2=4: v1* ≈ 1697.2, v2* ≈ 1302.8
        v1_analitico = 1697.225
        v2_analitico = 1302.775
        self.assertAlmostEqual(flows_cust_fw[0], v1_analitico, delta=15.0)
        self.assertAlmostEqual(flows_cust_fw[1], v2_analitico, delta=15.0)

        # 3. Arco com params={} usa o global:
        # Se passarmos beta=2.0 globalmente, arc2_default (params={}) adota beta=2.0.
        # Agora ambas as rotas têm beta efetivo 2.0 -> rede volta a ser simétrica -> 1500 cada!
        flows_same_beta, _, _ = assign_fw(
            graph_custom, od_pairs=od_pairs, beta=2.0, max_iter=30
        )
        self.assertAlmostEqual(flows_same_beta[0], 1500.0, delta=1.0)
        self.assertAlmostEqual(flows_same_beta[1], 1500.0, delta=1.0)


class TestBprCoeffs(unittest.TestCase):
    """Testes unitários para a função helper _bpr_coeffs (D4)."""

    def test_bpr_coeffs_empty_params_uses_global(self):
        """Arco com params={} ou sem a chave usa o valor global."""
        arc_empty = Arc("a1", "L1", (0, 0), (1, 0), 10.0, 5.0, 1000.0, "rodoviario", {}, {}, [])
        alphas, betas = _bpr_coeffs([arc_empty], alpha=0.15, beta=4.0)
        self.assertEqual(alphas, [0.15])
        self.assertEqual(betas, [4.0])

        # Com globais customizados
        alphas_cust, betas_cust = _bpr_coeffs([arc_empty], alpha=0.20, beta=6.0)
        self.assertEqual(alphas_cust, [0.20])
        self.assertEqual(betas_cust, [6.0])

    def test_bpr_coeffs_custom_params_overrides_global(self):
        """Arco com params definidos sobrescreve os coeficientes globais."""
        arc1 = Arc(
            "a1", "L1", (0, 0), (1, 0), 10.0, 5.0, 1000.0, "rodoviario",
            {'bpr_alpha': 0.25, 'bpr_beta': 2.0}, {}, []
        )
        arc2 = Arc(
            "a2", "L2", (0, 0), (1, 0), 10.0, 5.0, 1000.0, "rodoviario",
            {'bpr_beta': 5.0}, {}, []
        )
        arc3 = Arc("a3", "L3", (0, 0), (1, 0), 10.0, 5.0, 1000.0, "rodoviario", {}, {}, [])

        alphas, betas = _bpr_coeffs([arc1, arc2, arc3], alpha=0.15, beta=4.0)
        self.assertEqual(alphas, [0.25, 0.15, 0.15])
        self.assertEqual(betas, [2.0, 5.0, 4.0])


if __name__ == '__main__':
    unittest.main()
