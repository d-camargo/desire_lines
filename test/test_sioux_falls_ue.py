# coding=utf-8
"""Testes de regressão do motor de alocação contra a referência Sioux Falls (D7).

Módulo em Python puro: sem import qgis.
Carrega a rede Sioux Falls diretamente de links.csv, viagens de trips.csv
e fluxos de equilíbrio do usuário (UE) de referência de flow_ue.csv.
Compara as alocações Frank-Wolfe e MSA contra a referência bstabler/TransportationNetworks.
"""

import csv
import os
import unittest

from desire_lines.traffic.network import Arc
from desire_lines.traffic.graph import build_graph
from desire_lines.traffic.assignment import assign, bpr_time

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'sioux_falls')


def load_trips(path=None):
    """Carrega os 528 pares OD de Sioux Falls com demanda > 0 a partir de trips.csv (D6)."""
    if path is None:
        path = os.path.join(DATA_DIR, 'trips.csv')
    trips = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append((int(row['origin']), int(row['destination']), float(row['demand'])))
    return trips


def load_reference_flow(path=None):
    """Carrega os 76 fluxos de equilíbrio do usuário (UE) de referência a partir de flow_ue.csv (D6).

    Returns:
        dict: Mapeamento {(init_node, term_node): (volume, cost)}.
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'flow_ue.csv')
    flows = {}
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = int(row['init_node'])
            v = int(row['term_node'])
            vol = float(row['volume'])
            cost = float(row['cost'])
            flows[(u, v)] = (vol, cost)
    return flows


def load_links_as_arcs(path=None):
    """Monta arcos network.Arc direto de links.csv (um por linha, t0=free_flow_time, capacity=capacity).

    Returns:
        list of Arc: 76 arcos direcionados de Sioux Falls.
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'links.csv')
    arcs = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            init_node = int(row['init_node'])
            term_node = int(row['term_node'])
            cap = float(row['capacity'])
            t0 = float(row['free_flow_time'])
            length = float(row.get('length', 0.0))
            arc = Arc(
                arc_id=(init_node, term_node),
                link_id=(init_node, term_node),
                from_node=init_node,
                to_node=term_node,
                length=length,
                t0=t0,
                capacity=cap,
                scope='rodoviario',
                params={},
                sources={},
                geometry=[],
                forward=True,
            )
            arcs.append(arc)
    return arcs


class TestSiouxFallsUERegression(unittest.TestCase):
    """Regressão do motor de alocação contra a referência Sioux Falls (D7)."""

    @classmethod
    def setUpClass(cls):
        cls.arcs = load_links_as_arcs()
        cls.trips = load_trips()
        cls.ref_flows = load_reference_flow()
        cls.tstt_ref = sum(vol * cost for vol, cost in cls.ref_flows.values())

    def test_fixture_integrity(self):
        """Verifica a integridade dos dados de entrada montados."""
        self.assertEqual(len(self.arcs), 76)
        self.assertEqual(len(self.trips), 528)
        self.assertEqual(len(self.ref_flows), 76)
        total_demand = sum(dem for _, _, dem in self.trips)
        self.assertAlmostEqual(total_demand, 360600.0, places=4)
        # TSTT de referência calculado no teste a partir de flow_ue.csv (D7)
        self.assertAlmostEqual(self.tstt_ref, 7480225.34, places=1)

    def test_frank_wolfe_300_iterations(self):
        """Frank-Wolfe 300 iterações (gap_tol=1e-9): erro máx <= 2%, médio <= 0.5%, TSTT <= 0.5% (D7)."""
        graph = build_graph(self.arcs)
        flows, historico, stats = assign(
            graph,
            arcs=self.arcs,
            od_pairs=self.trips,
            method='fw',
            max_iter=300,
            gap_tol=1e-9,
        )

        self.assertEqual(len(flows), 76)
        self.assertEqual(stats['method'], 'fw')
        self.assertEqual(stats['allocated'], 528)
        self.assertEqual(stats['unreachable'], 0)

        errors = []
        tstt_fw = 0.0
        for i, arc in enumerate(self.arcs):
            pair = (arc.from_node, arc.to_node)
            vol_ref, _ = self.ref_flows[pair]
            v = flows[i]
            t = bpr_time(arc.t0, v, arc.capacity, alpha=0.15, beta=4.0)
            tstt_fw += v * t
            err = abs(v - vol_ref) / vol_ref
            errors.append(err)

        max_err = max(errors)
        mean_err = sum(errors) / len(errors)
        tstt_diff = abs(tstt_fw - self.tstt_ref) / self.tstt_ref

        # Asserções de D7 para FW 300 it:
        # erro máx. <= 2 %, médio <= 0,5 %, TSTT a <= 0,5 % de 7 480 225
        self.assertLessEqual(max_err, 0.02, f"Erro máx FW ({max_err*100:.3f}%) excedeu 2.0%")
        self.assertLessEqual(mean_err, 0.005, f"Erro médio FW ({mean_err*100:.3f}%) excedeu 0.5%")
        self.assertLessEqual(tstt_diff, 0.005, f"Diferença TSTT FW ({tstt_diff*100:.3f}%) excedeu 0.5%")

    def test_msa_500_iterations(self):
        """MSA 500 iterações (gap_tol=1e-9): erro máx <= 3% (D7)."""
        graph = build_graph(self.arcs)
        flows, historico, stats = assign(
            graph,
            arcs=self.arcs,
            od_pairs=self.trips,
            method='msa',
            max_iter=500,
            gap_tol=1e-9,
        )

        self.assertEqual(len(flows), 76)
        self.assertEqual(stats['method'], 'msa')
        self.assertEqual(stats['allocated'], 528)
        self.assertEqual(stats['unreachable'], 0)

        errors = []
        for i, arc in enumerate(self.arcs):
            pair = (arc.from_node, arc.to_node)
            vol_ref, _ = self.ref_flows[pair]
            v = flows[i]
            err = abs(v - vol_ref) / vol_ref
            errors.append(err)

        max_err = max(errors)

        # Asserções de D7 para MSA 500 it:
        # erro máx. <= 3 %
        self.assertLessEqual(max_err, 0.03, f"Erro máx MSA ({max_err*100:.3f}%) excedeu 3.0%")


if __name__ == '__main__':
    unittest.main()
