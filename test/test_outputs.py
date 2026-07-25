# coding=utf-8
"""Testes unitários para o módulo de saídas (outputs.py)."""

import unittest
from test.utilities import get_qgis_app

# Inicializa ambiente QGIS
QGIS_APP = get_qgis_app()

from qgis.core import QgsCoordinateReferenceSystem, QgsGraduatedSymbolRenderer
from desire_lines.traffic.network import Arc
from desire_lines.traffic.outputs import flows_to_layer, apply_vc_style


class TestOutputsModule(unittest.TestCase):
    """Testes unitários do módulo outputs.py."""

    def setUp(self):
        """Prepara arcos fictícios para os testes."""
        self.arc1 = Arc(
            arc_id=(10, 'fw'),
            link_id=10,
            from_node=(0.0, 0.0),
            to_node=(1000.0, 0.0),
            length=1000.0,
            t0=0.6,  # 0.6 minutos = 0.01h (1 km a 100 km/h)
            capacity=1000.0,
            scope='rodoviario',
            params={'lanes': 1, 'vel_livre': 100.0},
            sources={'terreno': 'oficial', 'vel_livre': 'usuario'},
            geometry=[(0.0, 0.0), (1000.0, 0.0)],
            forward=True,
        )
        self.arc2 = Arc(
            arc_id=(10, 'bw'),
            link_id=10,
            from_node=(1000.0, 0.0),
            to_node=(0.0, 0.0),
            length=1000.0,
            t0=0.6,
            capacity=1000.0,
            scope='urbano',
            params={'lanes': 1, 'vel_livre': 100.0},
            sources={'terreno': 'padrao'},
            geometry=[(1000.0, 0.0), (0.0, 0.0)],
            forward=False,
        )
        self.arcs = [self.arc1, self.arc2]
        self.crs = QgsCoordinateReferenceSystem.fromEpsgId(31983)

    def test_flows_to_layer_aon(self):
        """Testa criação de camada para alocação AoN."""
        fluxos = [500.0, 0.0]
        stats = {'metodo': 'aon'}
        layer = flows_to_layer(self.arcs, fluxos, stats=stats, crs=self.crs)

        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), 'alocacao_aon')
        self.assertEqual(layer.featureCount(), 2)

        # Campos esperados
        field_names = [f.name() for f in layer.fields()]
        expected_fields = [
            'arc_id', 'link_id', 'sentido', 'faixas', 'comp_m', 'vel_livre',
            'capacidade', 'volume', 'vc', 'los', 'tempo_h', 'atraso_h',
            'metodo', 'escopo', 'src_terreno', 'src_vel_livre'
        ]
        for ef in expected_fields:
            self.assertIn(ef, field_names)

        # Validação das feições
        feats = list(layer.getFeatures())
        f1 = feats[0]
        self.assertEqual(f1['arc_id'], "(10, 'fw')")
        self.assertEqual(f1['volume'], 500.0)
        self.assertEqual(f1['capacidade'], 1000.0)
        self.assertAlmostEqual(f1['vc'], 0.5)
        self.assertEqual(f1['los'], 'B')
        self.assertEqual(f1['metodo'], 'aon')
        self.assertEqual(f1['escopo'], 'rodoviario')

        f2 = feats[1]
        self.assertEqual(f2['volume'], 0.0)
        self.assertAlmostEqual(f2['vc'], 0.0)
        self.assertEqual(f2['los'], 'A')

    def test_flows_to_layer_msa(self):
        """Testa criação de camada para alocação MSA."""
        fluxos = [1200.0, 800.0]
        stats = {'metodo': 'msa'}
        layer = flows_to_layer(self.arcs, fluxos, stats=stats, crs=self.crs)

        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), 'alocacao_msa')

        feats = list(layer.getFeatures())
        f1 = feats[0]
        self.assertEqual(f1['volume'], 1200.0)
        self.assertAlmostEqual(f1['vc'], 1.2)
        self.assertEqual(f1['los'], 'F')
        self.assertEqual(f1['metodo'], 'msa')

    def test_apply_vc_style(self):
        """Testa aplicação da simbologia por classes de v/c."""
        fluxos = [500.0, 1200.0]
        stats = {'metodo': 'msa'}
        layer = flows_to_layer(self.arcs, fluxos, stats=stats, crs=self.crs)

        apply_vc_style(layer)
        renderer = layer.renderer()

        self.assertIsInstance(renderer, QgsGraduatedSymbolRenderer)
        self.assertEqual(renderer.classAttribute(), 'vc')
        self.assertEqual(len(renderer.ranges()), 6)

        labels = [r.label() for r in renderer.ranges()]
        self.assertIn('A (<= 0.35)', labels[0])
        self.assertIn('F (> 1.00)', labels[-1])


if __name__ == '__main__':
    unittest.main()
