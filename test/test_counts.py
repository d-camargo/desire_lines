# coding=utf-8
"""Testes unitários para o módulo de casamento espacial de postos (counts.py)."""

import ast
import unittest
from test.utilities import get_qgis_app

# Inicializa o ambiente QGIS
QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
    NULL,
)
from qgis.PyQt.QtCore import QVariant

from desire_lines.traffic import counts
from desire_lines.traffic.counts import casar_postos


def _create_assign_layer(crs_auth='EPSG:31983', with_volume=True, with_link_id=True):
    """Cria uma camada de alocação de memória para testes."""
    fields_def = []
    if with_link_id:
        fields_def.append('field=link_id:string')
    if with_volume:
        fields_def.append('field=volume:double')

    uri = f"LineString?crs={crs_auth}"
    if fields_def:
        uri += "&" + "&".join(fields_def)
    layer = QgsVectorLayer(uri, 'assign_test', 'memory')
    return layer


def _create_posts_layer(crs_auth='EPSG:31983', with_id_field=False):
    """Cria uma camada de postos de contagem de memória para testes."""
    uri = f"Point?crs={crs_auth}&field=contagem:double"
    if with_id_field:
        uri += "&field=codigo:string"
    layer = QgsVectorLayer(uri, 'posts_test', 'memory')
    return layer


class TestCasamentoPostos(unittest.TestCase):
    """Testes unitários da função casar_postos."""

    def setUp(self):
        """Configura camadas padrão em EPSG:31983."""
        # Linha horizontal de (500000, 7400000) a (501000, 7400000)
        self.geom_line = QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 7400000.0),
            QgsPointXY(501000.0, 7400000.0),
        ])

        self.assign_layer = _create_assign_layer('EPSG:31983')
        pr = self.assign_layer.dataProvider()

        # Duas feições para o mesmo link: fw (300) e bw (200)
        f_fw = QgsFeature(self.assign_layer.fields())
        f_fw.setGeometry(self.geom_line)
        f_fw['link_id'] = 'L1'
        f_fw['volume'] = 300.0

        f_bw = QgsFeature(self.assign_layer.fields())
        f_bw.setGeometry(self.geom_line)
        f_bw['link_id'] = 'L1'
        f_bw['volume'] = 200.0

        pr.addFeatures([f_fw, f_bw])
        self.assign_layer.updateExtents()

    def test_casamento_basico_fw_bw_geh_faixa_a(self):
        """(a) um link com feições fw/bw de volume 300/200 e um posto a 50 m
        com contagem 520 → modelado=500, GEH ≈ 0,884, faixa A."""
        posts_layer = _create_posts_layer('EPSG:31983')
        pr = posts_layer.dataProvider()

        # Posto a 50 m ao norte da linha (x=500500, y=7400050)
        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p['contagem'] = 520.0
        pr.addFeatures([p])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(
            self.assign_layer,
            posts_layer,
            count_field='contagem',
        )

        self.assertEqual(n_invalidos, 0)
        self.assertEqual(len(resultados), 1)

        r = resultados[0]
        self.assertEqual(r['modelado'], 500.0)
        self.assertEqual(r['contagem'], 520.0)
        self.assertEqual(r['fator'], 1.0)
        self.assertEqual(r['dif'], -20.0)
        self.assertAlmostEqual(r['dif_pct'], 100.0 * (-20.0) / 520.0, places=4)
        self.assertAlmostEqual(r['dist_m'], 50.0, places=3)
        self.assertEqual(r['link_id'], 'L1')
        self.assertEqual(r['faixa'], 'A')
        self.assertAlmostEqual(r['geh'], 0.8856, places=3)
        self.assertFalse(r['geometry'].isNull())
        self.assertAlmostEqual(r['geometry'].asPoint().x(), 500500.0, places=1)
        self.assertAlmostEqual(r['geometry'].asPoint().y(), 7400050.0, places=1)

    def test_fator_multiplicador(self):
        """(b) fator=2.0 → modelado=1000."""
        posts_layer = _create_posts_layer('EPSG:31983')
        pr = posts_layer.dataProvider()

        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p['contagem'] = 520.0
        pr.addFeatures([p])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(
            self.assign_layer,
            posts_layer,
            count_field='contagem',
            fator=2.0,
        )

        self.assertEqual(n_invalidos, 0)
        self.assertEqual(len(resultados), 1)
        r = resultados[0]
        self.assertEqual(r['modelado'], 1000.0)
        self.assertEqual(r['fator'], 2.0)
        self.assertEqual(r['dif'], 480.0)

    def test_posto_alem_da_distancia_maxima_sem_link(self):
        """(c) posto a 500 m com max_dist_m=200 → faixa='sem_link' e geh=None."""
        posts_layer = _create_posts_layer('EPSG:31983')
        pr = posts_layer.dataProvider()

        # Posto a 500 m ao norte da linha (x=500500, y=7400500)
        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400500.0)))
        p['contagem'] = 520.0
        pr.addFeatures([p])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(
            self.assign_layer,
            posts_layer,
            count_field='contagem',
            max_dist_m=200.0,
        )

        self.assertEqual(n_invalidos, 0)
        self.assertEqual(len(resultados), 1)
        r = resultados[0]
        self.assertEqual(r['faixa'], 'sem_link')
        self.assertIsNone(r['geh'])
        self.assertEqual(r['modelado'], 0.0)
        self.assertIsNone(r['link_id'])
        self.assertIsNone(r['dist_m'])
        self.assertEqual(r['dif'], -520.0)
        self.assertEqual(r['dif_pct'], -100.0)

    def test_contagem_invalida_nula_e_negativa(self):
        """(d) contagem nula e negativa → contadas em n_invalidos, fora de resultados."""
        posts_layer = _create_posts_layer('EPSG:31983')
        pr = posts_layer.dataProvider()

        # Posto 1: válido
        p1 = QgsFeature(posts_layer.fields())
        p1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p1['contagem'] = 100.0

        # Posto 2: contagem None
        p2 = QgsFeature(posts_layer.fields())
        p2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p2['contagem'] = None

        # Posto 3: contagem negativa (-50)
        p3 = QgsFeature(posts_layer.fields())
        p3.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p3['contagem'] = -50.0

        # Posto 4: contagem NULL
        p4 = QgsFeature(posts_layer.fields())
        p4.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p4['contagem'] = NULL

        # Posto 5: sem geometria
        p5 = QgsFeature(posts_layer.fields())
        p5['contagem'] = 200.0

        pr.addFeatures([p1, p2, p3, p4, p5])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(
            self.assign_layer,
            posts_layer,
            count_field='contagem',
        )

        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0]['contagem'], 100.0)
        self.assertEqual(n_invalidos, 4)

    def test_postos_em_epsg_4674_transformados(self):
        """(e) postos em EPSG:4674 são transformados e casam igual."""
        posts_layer = _create_posts_layer('EPSG:4674')
        pr = posts_layer.dataProvider()

        # Converte ponto UTM (500500, 7400050) para SIRGAS 2000 geográfico (EPSG:4674)
        crs_utm = QgsCoordinateReferenceSystem('EPSG:31983')
        crs_geo = QgsCoordinateReferenceSystem('EPSG:4674')
        ct = QgsCoordinateTransform(crs_utm, crs_geo, QgsCoordinateTransformContext())
        pt_geo = ct.transform(QgsPointXY(500500.0, 7400050.0))

        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(pt_geo))
        p['contagem'] = 520.0
        pr.addFeatures([p])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(
            self.assign_layer,
            posts_layer,
            count_field='contagem',
        )

        self.assertEqual(n_invalidos, 0)
        self.assertEqual(len(resultados), 1)
        r = resultados[0]
        self.assertEqual(r['modelado'], 500.0)
        self.assertEqual(r['faixa'], 'A')
        self.assertAlmostEqual(r['dist_m'], 50.0, places=2)
        # Geometria do resultado deve estar no CRS da alocação (31983)
        self.assertAlmostEqual(r['geometry'].asPoint().x(), 500500.0, places=1)
        self.assertAlmostEqual(r['geometry'].asPoint().y(), 7400050.0, places=1)

    def test_camada_sem_volume_levanta_value_error(self):
        """(f) camada sem volume → ValueError."""
        assign_sem_vol = _create_assign_layer('EPSG:31983', with_volume=False, with_link_id=True)
        posts_layer = _create_posts_layer('EPSG:31983')

        with self.assertRaises(ValueError) as ctx:
            casar_postos(assign_sem_vol, posts_layer, count_field='contagem')

        self.assertIn('volume', str(ctx.exception))

    def test_camada_sem_link_id_levanta_value_error(self):
        """Camada de alocação sem link_id → ValueError com 'link_id'."""
        assign_sem_link_id = _create_assign_layer('EPSG:31983', with_volume=True, with_link_id=False)
        posts_layer = _create_posts_layer('EPSG:31983')

        with self.assertRaises(ValueError) as ctx:
            casar_postos(assign_sem_link_id, posts_layer, count_field='contagem')

        self.assertIn('link_id', str(ctx.exception))

    def test_camada_de_alocacao_em_4326_levanta_runtime_error(self):
        """(g) camada de alocação em 4326 → RuntimeError."""
        assign_4326 = _create_assign_layer('EPSG:4326')
        posts_layer = _create_posts_layer('EPSG:4326')

        with self.assertRaises(RuntimeError) as ctx:
            casar_postos(assign_4326, posts_layer, count_field='contagem')

        self.assertIn('geográfico', str(ctx.exception).lower())

    def test_id_field_vazio_usa_fid(self):
        """(h) id_field vazio usa o FID como posto."""
        posts_layer = _create_posts_layer('EPSG:31983', with_id_field=True)
        pr = posts_layer.dataProvider()

        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p['contagem'] = 520.0
        p['codigo'] = 'POSTO-XYZ'
        pr.addFeatures([p])
        posts_layer.updateExtents()

        feat_id = list(posts_layer.getFeatures())[0].id()

        # Com id_field=None
        res_none, _ = casar_postos(self.assign_layer, posts_layer, 'contagem', id_field=None)
        self.assertEqual(res_none[0]['posto'], feat_id)

        # Com id_field=''
        res_empty, _ = casar_postos(self.assign_layer, posts_layer, 'contagem', id_field='')
        self.assertEqual(res_empty[0]['posto'], feat_id)

        # Com id_field='codigo'
        res_code, _ = casar_postos(self.assign_layer, posts_layer, 'contagem', id_field='codigo')
        self.assertEqual(res_code[0]['posto'], 'POSTO-XYZ')

    def test_contagem_zero_dif_pct_is_none(self):
        """Posto com contagem == 0 deve gerar dif_pct=None sem erro de divisão por zero."""
        posts_layer = _create_posts_layer('EPSG:31983')
        pr = posts_layer.dataProvider()

        p = QgsFeature(posts_layer.fields())
        p.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400050.0)))
        p['contagem'] = 0.0
        pr.addFeatures([p])
        posts_layer.updateExtents()

        resultados, n_invalidos = casar_postos(self.assign_layer, posts_layer, 'contagem')
        self.assertEqual(n_invalidos, 0)
        self.assertEqual(len(resultados), 1)
        r = resultados[0]
        self.assertEqual(r['contagem'], 0.0)
        self.assertIsNone(r['dif_pct'])
        self.assertEqual(r['dif'], 500.0)

    def test_counts_sem_qgis_project_nem_iface(self):
        """counts.py não importa nem referencia QgsProject ou iface (D6)."""
        with open(counts.__file__, 'r', encoding='utf-8') as f:
            conteudo = f.read()

        self.assertNotIn('QgsProject', conteudo)
        self.assertNotIn('iface', conteudo)

        tree = ast.parse(conteudo)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn('iface', alias.name)
                    self.assertNotIn('QgsProject', alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self.assertNotEqual(alias.name, 'QgsProject')
                    self.assertNotEqual(alias.name, 'iface')
