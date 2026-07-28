# coding=utf-8
import unittest
from desire_lines.traffic.network import Arc
from desire_lines.traffic.graph import build_graph
from desire_lines.traffic.assignment import (
    bpr_time,
    aon_load,
    assign_aon,
    assign_msa,
    assign,
    VALID_METHODS,
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
        """`assign` despacha corretamente entre métodos 'aon' e 'msa' (D10)."""
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

        # Mesmas chaves de stats nos dois métodos
        self.assertEqual(set(stats_aon.keys()), set(stats_msa.keys()))

    def test_assign_invalid_method_raises(self):
        """`assign` levanta ValueError com a lista de métodos válidos."""
        od_pairs = [(self.nA, self.nB, 400.0)]

        with self.assertRaises(ValueError) as ctx:
            assign(self.graph, od_pairs=od_pairs, method='bogus')

        for metodo in VALID_METHODS:
            self.assertIn(metodo, str(ctx.exception))


if __name__ == '__main__':
    unittest.main()



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


if __name__ == '__main__':
    unittest.main()
