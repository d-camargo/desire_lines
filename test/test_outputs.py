# coding=utf-8
"""Testes unitários para o módulo de saídas (outputs.py)."""

import unittest
from test.utilities import get_qgis_app

# Inicializa ambiente QGIS
QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRuleBasedRenderer,
    QgsRenderContext,
    QgsExpression,
    QgsExpressionContext,
)
from desire_lines.traffic.network import Arc, CONNECTOR_LINK_ID
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
            'arc_id', 'link_id', 'tipo', 'sentido', 'faixas', 'comp_m', 'vel_livre',
            'capacidade', 'volume', 'vc', 'los', 'tempo_h', 'atraso_h',
            'metodo', 'escopo', 'src_terreno', 'src_vel_livre'
        ]
        for ef in expected_fields:
            self.assertIn(ef, field_names)

        # Validação das feições
        feats = list(layer.getFeatures())
        f1 = feats[0]
        self.assertEqual(f1['arc_id'], "(10, 'fw')")
        self.assertEqual(f1['tipo'], 'link')
        self.assertEqual(f1['volume'], 500.0)
        self.assertEqual(f1['capacidade'], 1000.0)
        self.assertAlmostEqual(f1['vc'], 0.5)
        self.assertEqual(f1['los'], 'B')
        self.assertEqual(f1['metodo'], 'aon')
        self.assertEqual(f1['escopo'], 'rodoviario')

        f2 = feats[1]
        self.assertEqual(f2['tipo'], 'link')
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
        self.assertEqual(f1['tipo'], 'link')
        self.assertEqual(f1['volume'], 1200.0)
        self.assertAlmostEqual(f1['vc'], 1.2)
        self.assertEqual(f1['los'], 'F')
        self.assertEqual(f1['metodo'], 'msa')

    def test_tipo_values(self):
        """Testa os três valores possíveis do campo tipo: link, link_dividido e conector."""
        arc_normal = Arc(
            arc_id=(10, 'fw'),
            link_id=10,
            from_node=(0.0, 0.0),
            to_node=(1000.0, 0.0),
            length=1000.0,
            t0=0.6,
            capacity=1000.0,
            scope='rodoviario',
            params={},
            sources={},
            geometry=[(0.0, 0.0), (1000.0, 0.0)],
        )
        arc_split = Arc(
            arc_id=(10, 'fw', 0),
            link_id=10,
            from_node=(0.0, 0.0),
            to_node=(500.0, 0.0),
            length=500.0,
            t0=0.3,
            capacity=1000.0,
            scope='rodoviario',
            params={},
            sources={},
            geometry=[(0.0, 0.0), (500.0, 0.0)],
        )
        arc_conn = Arc(
            arc_id=('conector-Z1', 'fw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=(0.0, 0.0),
            to_node=(100.0, 0.0),
            length=100.0,
            t0=0.03,
            capacity=99999.0,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[(0.0, 0.0), (100.0, 0.0)],
        )
        layer = flows_to_layer([arc_normal, arc_split, arc_conn], [100.0, 50.0, 0.0], crs=self.crs)
        feats = list(layer.getFeatures())
        self.assertEqual(feats[0]['tipo'], 'link')
        self.assertEqual(feats[1]['tipo'], 'link_dividido')
        self.assertEqual(feats[2]['tipo'], 'conector')

    def test_apply_vc_style(self):
        """Testa aplicação da simbologia baseada em regras por classes de v/c e conector."""
        fluxos = [500.0, 1200.0]
        stats = {'metodo': 'msa'}
        layer = flows_to_layer(self.arcs, fluxos, stats=stats, crs=self.crs)

        apply_vc_style(layer)
        renderer = layer.renderer()

        self.assertIsInstance(renderer, QgsRuleBasedRenderer)
        root_rule = renderer.rootRule()
        children = root_rule.children()
        # 1 conector + 6 faixas v/c = 7 regras
        self.assertEqual(len(children), 7)

        # Regra do conector: casa tipo='conector' com símbolo tracejado cinza (#808080, largura 0.3)
        conn_rules = [r for r in children if r.filterExpression() == "\"tipo\" = 'conector'"]
        self.assertEqual(len(conn_rules), 1)
        conn_rule = conn_rules[0]
        self.assertEqual(conn_rule.label(), 'Connector')

        conn_sym = conn_rule.symbol()
        self.assertEqual(conn_sym.color().name().lower(), '#808080')
        self.assertAlmostEqual(conn_sym.width(), 0.3, places=2)
        sl = conn_sym.symbolLayer(0)
        self.assertEqual(sl.properties().get('line_style'), 'dash')

        # Regras de v/c excluem conector
        vc_rules = [r for r in children if r is not conn_rule]
        self.assertEqual(len(vc_rules), 6)
        for r in vc_rules:
            self.assertIn("\"tipo\" <> 'conector'", r.filterExpression())

        labels = [r.label() for r in vc_rules]
        self.assertIn('A (<= 0.35)', labels[0])
        self.assertIn('F (> 1.00)', labels[-1])

    def test_connector_feature_does_not_match_class_a(self):
        """Testa que uma feição de conector com vc=0 não cai na regra da classe A."""
        arc_conn = Arc(
            arc_id=('conector-Z1', 'fw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=(0.0, 0.0),
            to_node=(100.0, 0.0),
            length=100.0,
            t0=0.03,
            capacity=99999.0,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[(0.0, 0.0), (100.0, 0.0)],
        )
        layer = flows_to_layer([arc_conn], [0.0], stats={'metodo': 'aon'}, crs=self.crs)
        apply_vc_style(layer)

        feat_conn = next(layer.getFeatures())
        self.assertEqual(feat_conn['tipo'], 'conector')
        self.assertEqual(feat_conn['vc'], 0.0)

        renderer = layer.renderer()
        root_rule = renderer.rootRule()

        render_ctx = QgsRenderContext()
        render_ctx.expressionContext().setFields(layer.fields())

        renderer.startRender(render_ctx, layer.fields())
        matching_rules = [
            r.label() for r in root_rule.children()
            if r.willRenderFeature(feat_conn, render_ctx)
        ]
        renderer.stopRender(render_ctx)

        self.assertIn('Connector', matching_rules)
        self.assertNotIn('A (<= 0.35)', matching_rules)

        # Verificação direta via QgsExpression da regra A
        rule_a = [r for r in root_rule.children() if 'A' in r.label()][0]
        ctx = QgsExpressionContext()
        ctx.setFields(layer.fields())
        ctx.setFeature(feat_conn)
        exp_a = QgsExpression(rule_a.filterExpression())
        self.assertFalse(bool(exp_a.evaluate(ctx)))


if __name__ == '__main__':
    unittest.main()
