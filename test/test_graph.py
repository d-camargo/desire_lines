# coding=utf-8
"""Tests for the routing graph (traffic/graph.py).

Pure Python: the module deliberately imports nothing from QGIS (D4/D8), so
these run without a QGIS application.
"""
import unittest

from desire_lines.traffic import graph, network


def arc(arc_id, from_node, to_node, t0, capacity=1000.0):
    """Minimal Arc for topology tests (geometry is irrelevant here)."""
    return network.Arc(
        arc_id=arc_id, link_id=arc_id, from_node=from_node, to_node=to_node,
        length=t0 * 1000.0, t0=t0, capacity=capacity, scope='rodoviario',
        params={}, sources={}, geometry=[from_node, to_node])


def diamond():
    """A -> (B | C) -> D, where the B leg costs 2 and the C leg costs 10."""
    a, b, c, d = (0.0, 0.0), (1.0, 1.0), (1.0, -1.0), (2.0, 0.0)
    return graph.build_graph([
        arc('ab', a, b, 1.0),
        arc('bd', b, d, 1.0),
        arc('ac', a, c, 5.0),
        arc('cd', c, d, 5.0),
    ]), (a, b, c, d)


class GraphBuildTest(unittest.TestCase):
    """Topology and cost bookkeeping."""

    def test_costs_start_at_free_flow_time(self):
        g, _nodes = diamond()
        self.assertEqual(g.costs, [1.0, 1.0, 5.0, 5.0])
        self.assertEqual(len(g), 4)

    def test_arrival_only_node_still_exists(self):
        """A node with no outgoing arc must be reachable as a destination."""
        g, (_a, _b, _c, d) = diamond()
        self.assertTrue(g.has_node(d))
        self.assertEqual(g.adjacency[d], [])

    def test_duplicate_arc_id_is_rejected(self):
        node_a, node_b = (0.0, 0.0), (1.0, 0.0)
        with self.assertRaises(ValueError):
            graph.build_graph([
                arc('same', node_a, node_b, 1.0),
                arc('same', node_b, node_a, 1.0),
            ])

    def test_update_costs_rejects_wrong_length_and_negatives(self):
        g, _nodes = diamond()
        with self.assertRaises(ValueError):
            g.update_costs([1.0, 2.0])
        with self.assertRaises(ValueError):
            g.update_costs([1.0, 1.0, 1.0, -1.0])

    def test_reset_costs_returns_to_t0(self):
        g, _nodes = diamond()
        g.update_costs([9.0, 9.0, 9.0, 9.0])
        g.reset_costs()
        self.assertEqual(g.costs, [1.0, 1.0, 5.0, 5.0])


class DijkstraTest(unittest.TestCase):
    """Shortest path, path reconstruction and the unreachable case."""

    def test_picks_the_cheap_leg_of_the_diamond(self):
        g, (a, b, _c, d) = diamond()
        _dist, pred = g.shortest_paths(a, targets=[d])
        path = g.path_arcs(pred, d, origin=a)
        self.assertEqual([x.arc_id for x in path], ['ab', 'bd'])
        self.assertTrue(any(x.to_node == b for x in path))

    def test_cost_update_flips_the_chosen_leg(self):
        """The same graph re-routes after costs change — no rebuild (D4)."""
        g, (a, _b, c, d) = diamond()
        g.update_costs({'ab': 20.0, 'bd': 20.0, 'ac': 1.0, 'cd': 1.0})
        path, cost = g.path_to(a, d)
        self.assertEqual([x.arc_id for x in path], ['ac', 'cd'])
        self.assertEqual(cost, 2.0)
        self.assertTrue(any(x.to_node == c for x in path))

    def test_unreachable_destination_returns_none(self):
        g = graph.build_graph([
            arc('ab', (0.0, 0.0), (1.0, 0.0), 1.0),
            arc('cd', (9.0, 9.0), (9.0, 8.0), 1.0),
        ])
        _dist, pred = g.shortest_paths((0.0, 0.0))
        self.assertIsNone(g.path_arcs(pred, (9.0, 8.0)))
        path, cost = g.path_to((0.0, 0.0), (9.0, 8.0))
        self.assertIsNone(path)
        self.assertEqual(cost, graph.INFINITY)

    def test_self_pair_is_an_empty_path_not_unreachable(self):
        g, (a, _b, _c, _d) = diamond()
        _dist, pred = g.shortest_paths(a)
        self.assertEqual(g.path_arcs(pred, a, origin=a), [])
        self.assertEqual(g.path_to(a, a), ([], 0.0))

    def test_origin_outside_the_graph_raises(self):
        g, _nodes = diamond()
        with self.assertRaises(KeyError):
            g.shortest_paths((99.0, 99.0))


class SnapToleranceTest(unittest.TestCase):
    """Endpoints within the snap tolerance must land on the same node."""

    def test_endpoints_within_one_centimetre_share_a_node(self):
        # precision=2 in a metric CRS == 1 cm; 100.004 and 100.0 round together.
        first = network.build_directed_arcs(
            'l1', [(0.0, 0.0), (100.004, 0.0)], precision=2)[0]
        second = network.build_directed_arcs(
            'l2', [(100.0, 0.0), (200.0, 0.0)], precision=2)[0]
        g = graph.build_graph([first, second])
        path, _cost = g.path_to((0.0, 0.0), (200.0, 0.0))
        self.assertEqual([a.arc_id for a in path], [('l1', 'fw'), ('l2', 'fw')])

    def test_endpoints_beyond_the_tolerance_stay_apart(self):
        first = network.build_directed_arcs(
            'l1', [(0.0, 0.0), (100.5, 0.0)], precision=2)[0]
        second = network.build_directed_arcs(
            'l2', [(100.0, 0.0), (200.0, 0.0)], precision=2)[0]
        g = graph.build_graph([first, second])
        path, _cost = g.path_to((0.0, 0.0), (200.0, 0.0))
        self.assertIsNone(path)


if __name__ == '__main__':
    unittest.main()
