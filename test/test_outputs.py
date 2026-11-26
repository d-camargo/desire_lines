# coding=utf-8
"""Testes unitários para o módulo de saídas (outputs.py)."""

import unittest
from test.utilities import get_qgis_app

# Inicializa ambiente QGIS
QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsRuleBasedRenderer,
    QgsCategorizedSymbolRenderer,
    QgsGeometry,
    QgsPointXY,
    NULL,
)
from qgis.PyQt.QtCore import QVariant
try:
    from qgis.PyQt.QtCore import QMetaType
except ImportError:
    QMetaType = None

from desire_lines.traffic.network import Arc, CONNECTOR_LINK_ID
from desire_lines.traffic.outputs import (
    flows_to_layer,
    apply_vc_style,
    calibration_to_layer,
    apply_geh_style,
)


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
        """Testa que conectores não são publicados e que a ordem de fluxos é preservada."""
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
        layer = flows_to_layer([arc_normal, arc_conn, arc_split], [100.0, 0.0, 50.0], crs=self.crs)
        feats = list(layer.getFeatures())
        self.assertEqual(len(feats), 2)
        for f in feats:
            self.assertNotEqual(f['tipo'], 'conector')
            self.assertNotEqual(f['escopo'], 'conector')
            self.assertNotEqual(f['link_id'], 'conector')
        self.assertEqual(feats[0]['tipo'], 'link')
        self.assertEqual(feats[0]['volume'], 100.0)
        self.assertEqual(feats[1]['tipo'], 'link_dividido')
        self.assertEqual(feats[1]['volume'], 50.0)

    def test_link_id_integer(self):
        """Testa que link_id numérico gera campo de inteiro 64 bits e valor int."""
        arc = Arc(
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
        layer = flows_to_layer([arc], [100.0], crs=self.crs)
        field = layer.fields().field('link_id')

        expected_types = [QVariant.LongLong]
        if hasattr(QMetaType, 'Type') and hasattr(QMetaType.Type, 'LongLong'):
            expected_types.append(QMetaType.Type.LongLong)
        self.assertIn(field.type(), expected_types)

        feat = next(layer.getFeatures())
        self.assertEqual(feat['link_id'], 10)
        self.assertIsInstance(feat['link_id'], int)
        self.assertNotIsInstance(feat['link_id'], bool)

    def test_link_id_string_fallback(self):
        """Testa que link_id não-numérico mantém campo String e valor original."""
        arc = Arc(
            arc_id=('L1', 'fw'),
            link_id='L1',
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
        layer = flows_to_layer([arc], [100.0], crs=self.crs)
        field = layer.fields().field('link_id')

        expected_types = [QVariant.String]
        if hasattr(QMetaType, 'Type') and hasattr(QMetaType.Type, 'QString'):
            expected_types.append(QMetaType.Type.QString)
        self.assertIn(field.type(), expected_types)

        feat = next(layer.getFeatures())
        self.assertEqual(feat['link_id'], 'L1')
        self.assertIsInstance(feat['link_id'], str)

    def test_apply_vc_style(self):
        """Testa aplicação da simbologia baseada em regras por classes de v/c (D2)."""
        fluxos = [500.0, 1200.0]
        stats = {'metodo': 'msa'}
        layer = flows_to_layer(self.arcs, fluxos, stats=stats, crs=self.crs)

        apply_vc_style(layer)
        renderer = layer.renderer()

        self.assertIsInstance(renderer, QgsRuleBasedRenderer)
        root_rule = renderer.rootRule()
        children = root_rule.children()
        # 6 faixas v/c (sem regra de conector, D2)
        self.assertEqual(len(children), 6)

        for r in children:
            self.assertNotIn('conector', r.filterExpression())

        labels = [r.label() for r in children]
        expected_prefixes = ['A', 'B', 'C', 'D', 'E', 'F']
        for prefix, label in zip(expected_prefixes, labels):
            self.assertTrue(label.startswith(prefix))
        self.assertIn('A (<= 0.35)', labels[0])
        self.assertIn('F (> 1.00)', labels[-1])

    def test_calibration_to_layer_three_results(self):
        """(a) 3 resultados viram 3 feições com os campos e valores certos, e geh nulo no sem_link."""
        resultados = [
            {
                'posto': 'P01',
                'contagem': 500.0,
                'modelado': 520.0,
                'fator': 1.0,
                'dif': 20.0,
                'dif_pct': 4.0,
                'geh': 0.88,
                'faixa': 'A',
                'link_id': '101',
                'dist_m': 15.0,
                'geometry': QgsGeometry.fromPointXY(QgsPointXY(100.0, 200.0)),
            },
            {
                'posto': 'P02',
                'contagem': 1000.0,
                'modelado': 700.0,
                'fator': 1.0,
                'dif': -300.0,
                'dif_pct': -30.0,
                'geh': 10.29,
                'faixa': 'C',
                'link_id': '102',
                'dist_m': 25.0,
                'geometry': QgsGeometry.fromPointXY(QgsPointXY(300.0, 400.0)),
            },
            {
                'posto': 'P03',
                'contagem': 800.0,
                'modelado': 0.0,
                'fator': 1.0,
                'dif': -800.0,
                'dif_pct': -100.0,
                'geh': None,
                'faixa': 'sem_link',
                'link_id': None,
                'dist_m': None,
                'geometry': QgsGeometry.fromPointXY(QgsPointXY(500.0, 600.0)),
            },
        ]
        layer = calibration_to_layer(resultados, crs=self.crs)

        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), 'calibracao_geh')
        self.assertEqual(layer.featureCount(), 3)

        field_names = [f.name() for f in layer.fields()]
        expected_fields = [
            'posto', 'contagem', 'modelado', 'fator', 'dif', 'dif_pct',
            'geh', 'faixa', 'link_id', 'dist_m'
        ]
        for ef in expected_fields:
            self.assertIn(ef, field_names)

        feats = list(layer.getFeatures())
        self.assertEqual(len(feats), 3)

        f1, f2, f3 = feats[0], feats[1], feats[2]

        self.assertEqual(f1['posto'], 'P01')
        self.assertAlmostEqual(f1['contagem'], 500.0)
        self.assertAlmostEqual(f1['modelado'], 520.0)
        self.assertAlmostEqual(f1['fator'], 1.0)
        self.assertAlmostEqual(f1['dif'], 20.0)
        self.assertAlmostEqual(f1['dif_pct'], 4.0)
        self.assertAlmostEqual(f1['geh'], 0.88, places=2)
        self.assertEqual(f1['faixa'], 'A')
        self.assertEqual(f1['link_id'], '101')
        self.assertAlmostEqual(f1['dist_m'], 15.0)

        self.assertEqual(f2['posto'], 'P02')
        self.assertEqual(f2['faixa'], 'C')
        self.assertAlmostEqual(f2['geh'], 10.29, places=2)

        self.assertEqual(f3['posto'], 'P03')
        self.assertEqual(f3['faixa'], 'sem_link')
        self.assertEqual(f3['geh'], NULL)
        self.assertEqual(f3['link_id'], NULL)
        self.assertEqual(f3['dist_m'], NULL)

    def test_apply_geh_style_five_categories(self):
        """(b) o renderer tem 5 categorias com os valores A, B, C, D e sem_link."""
        layer = calibration_to_layer([], crs=self.crs)
        apply_geh_style(layer)

        renderer = layer.renderer()
        self.assertIsInstance(renderer, QgsCategorizedSymbolRenderer)
        self.assertEqual(renderer.classAttribute(), 'faixa')

        categories = renderer.categories()
        self.assertEqual(len(categories), 5)
        cat_values = [c.value() for c in categories]
        self.assertEqual(cat_values, ['A', 'B', 'C', 'D', 'sem_link'])

    def test_calibration_to_layer_empty_is_valid(self):
        """(c) a camada vazia é válida."""
        layer = calibration_to_layer([], crs=self.crs)
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.featureCount(), 0)

        field_names = [f.name() for f in layer.fields()]
        expected_fields = [
            'posto', 'contagem', 'modelado', 'fator', 'dif', 'dif_pct',
            'geh', 'faixa', 'link_id', 'dist_m'
        ]
        for ef in expected_fields:
            self.assertIn(ef, field_names)


if __name__ == '__main__':
    unittest.main()
