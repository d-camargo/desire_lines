# coding=utf-8
"""Testes unitários para o casamento espacial de camada complementar (D6)."""

import ast
import unittest
from pathlib import Path
from test.utilities import get_qgis_app

# Inicializa o ambiente QGIS
QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
    NULL,
)

from desire_lines.traffic.complemento import atributos_por_proximidade


def _create_road_layer(crs_auth="EPSG:31983"):
    """Cria camada de rodovias de memória com um link padrão."""
    uri = f"LineString?crs={crs_auth}&field=id:int"
    layer = QgsVectorLayer(uri, "road_test", "memory")
    pr = layer.dataProvider()

    # Linha horizontal de (500000, 7400000) a (501000, 7400000), ponto médio (500500, 7400000)
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry.fromPolylineXY([
        QgsPointXY(500000.0, 7400000.0),
        QgsPointXY(501000.0, 7400000.0),
    ]))
    feat["id"] = 1
    pr.addFeatures([feat])
    layer.updateExtents()
    return layer


class TestComplementoProximidade(unittest.TestCase):
    """Testes unitários da função atributos_por_proximidade (D6)."""

    def setUp(self):
        """Configura a malha rodoviária padrão em EPSG:31983."""
        self.road_layer = _create_road_layer("EPSG:31983")
        self.road_feat = next(self.road_layer.getFeatures())
        self.road_fid = self.road_feat.id()

    def test_linha_osm_10m_recebe(self):
        """(a) Linha OSM a 10 m com lanes=3, oneway=yes → recebe."""
        uri = "LineString?crs=EPSG:31983&field=lanes:int&field=oneway:string"
        compl_layer = QgsVectorLayer(uri, "compl_osm", "memory")
        pr = compl_layer.dataProvider()

        # Linha a 10 m ao norte (y = 7400010)
        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 7400010.0),
            QgsPointXY(501000.0, 7400010.0),
        ]))
        feat["lanes"] = 3
        feat["oneway"] = "yes"
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid]["lanes"], 3)
        self.assertEqual(res[self.road_fid]["oneway"], "yes")

    def test_linha_100m_max_dist_30_fica_fora(self):
        """(b) Linha a 100 m com max_dist=30 → fica fora."""
        uri = "LineString?crs=EPSG:31983&field=lanes:int&field=oneway:string"
        compl_layer = QgsVectorLayer(uri, "compl_osm", "memory")
        pr = compl_layer.dataProvider()

        # Linha a 100 m ao norte (y = 7400100)
        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 7400100.0),
            QgsPointXY(501000.0, 7400100.0),
        ]))
        feat["lanes"] = 3
        feat["oneway"] = "yes"
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertNotIn(self.road_fid, res)
        self.assertEqual(len(res), 0)

    def test_ponto_20m_recebe(self):
        """(c) Ponto com pct_veic_pesados=32 a 20 m → recebe."""
        uri = "Point?crs=EPSG:31983&field=pct_veic_pesados:int"
        compl_layer = QgsVectorLayer(uri, "compl_point", "memory")
        pr = compl_layer.dataProvider()

        # Ponto a 20 m ao norte do ponto médio (500500, 7400020)
        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400020.0)))
        feat["pct_veic_pesados"] = 32
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid]["pct_veic_pesados"], 32)

    def test_poligono_contendo_ponto_medio_recebe(self):
        """(d) Polígono contendo o ponto médio, urbano=1 → recebe."""
        uri = "Polygon?crs=EPSG:31983&field=urbano:int"
        compl_layer = QgsVectorLayer(uri, "compl_poly", "memory")
        pr = compl_layer.dataProvider()

        # Polígono cobrindo o ponto médio (500500, 7400000)
        poly_geom = QgsGeometry.fromPolygonXY([[
            QgsPointXY(500400.0, 7399900.0),
            QgsPointXY(500600.0, 7399900.0),
            QgsPointXY(500600.0, 7400100.0),
            QgsPointXY(500400.0, 7400100.0),
        ]])
        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(poly_geom)
        feat["urbano"] = 1
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid]["urbano"], 1)

    def test_complemento_em_4674_casa_igual(self):
        """(e) Complemento em 4674 casa igual."""
        uri = "LineString?crs=EPSG:4674&field=lanes:int&field=oneway:string"
        compl_layer = QgsVectorLayer(uri, "compl_4674", "memory")
        pr = compl_layer.dataProvider()

        ctx = QgsCoordinateTransformContext()
        ct = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:31983"),
            QgsCoordinateReferenceSystem("EPSG:4674"),
            ctx,
        )

        p1_geo = ct.transform(QgsPointXY(500000.0, 7400010.0))
        p2_geo = ct.transform(QgsPointXY(501000.0, 7400010.0))

        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(QgsGeometry.fromPolylineXY([p1_geo, p2_geo]))
        feat["lanes"] = 3
        feat["oneway"] = "yes"
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(
            self.road_layer,
            compl_layer,
            max_dist_m=30.0,
            transform_context=ctx,
        )

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid]["lanes"], 3)
        self.assertEqual(res[self.road_fid]["oneway"], "yes")

    def test_rodoviaria_em_4326_levanta_runtime_error(self):
        """(f) Rodoviária em 4326 → RuntimeError."""
        road_geo = _create_road_layer("EPSG:4326")
        compl_layer = _create_road_layer("EPSG:4326")

        with self.assertRaises(RuntimeError) as cm:
            atributos_por_proximidade(road_geo, compl_layer)

        self.assertIn("geográfico", str(cm.exception).lower())

    def test_de_duas_candidatas_vence_a_mais_proxima(self):
        """(g) De duas candidatas, vence a mais próxima."""
        uri = "LineString?crs=EPSG:31983&field=lanes:int"
        compl_layer = QgsVectorLayer(uri, "compl_osm", "memory")
        pr = compl_layer.dataProvider()

        # Candidata mais próxima (a 10 m ao norte): lanes=2
        f1 = QgsFeature(compl_layer.fields())
        f1.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 7400010.0),
            QgsPointXY(501000.0, 7400010.0),
        ]))
        f1["lanes"] = 2

        # Candidata mais distante (a 25 m ao norte): lanes=4
        f2 = QgsFeature(compl_layer.fields())
        f2.setGeometry(QgsGeometry.fromPolylineXY([
            QgsPointXY(500000.0, 7400025.0),
            QgsPointXY(501000.0, 7400025.0),
        ]))
        f2["lanes"] = 4

        # Adiciona na ordem inversa para garantir que o resultado não depende da ordem de inserção
        pr.addFeatures([f2, f1])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid]["lanes"], 2)

    def test_ignora_campos_nulos(self):
        """Garante que atributos NULL ou vazios não entram no dicionário retornado."""
        uri = "Point?crs=EPSG:31983&field=lanes:int&field=oneway:string&field=extra:string"
        compl_layer = QgsVectorLayer(uri, "compl_nulls", "memory")
        pr = compl_layer.dataProvider()

        feat = QgsFeature(compl_layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500500.0, 7400010.0)))
        feat["lanes"] = 2
        feat["oneway"] = NULL
        feat["extra"] = ""
        pr.addFeatures([feat])
        compl_layer.updateExtents()

        res = atributos_por_proximidade(self.road_layer, compl_layer, max_dist_m=30.0)

        self.assertIn(self.road_fid, res)
        self.assertEqual(res[self.road_fid], {"lanes": 2})

    def test_sem_camada_ou_camada_vazia(self):
        """Retorna dicionário vazio se uma das camadas for None ou vazia."""
        self.assertEqual(atributos_por_proximidade(None, None), {})
        self.assertEqual(atributos_por_proximidade(self.road_layer, None), {})

        empty_compl = QgsVectorLayer("Point?crs=EPSG:31983&field=val:int", "empty", "memory")
        self.assertEqual(atributos_por_proximidade(self.road_layer, empty_compl), {})

    def test_sem_qgis_project_ou_iface(self):
        """Garante que complemento.py não importa nem referencia QgsProject ou iface."""
        mod_path = Path(__file__).resolve().parent.parent / "desire_lines" / "traffic" / "complemento.py"
        with open(mod_path, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code, filename=str(mod_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in ("QgsProject", "iface"):
                self.fail(f"Uso proibido de '{node.id}' em complemento.py na linha {node.lineno}")
            if isinstance(node, ast.Attribute) and node.attr in ("QgsProject", "iface"):
                self.fail(f"Uso proibido de '{node.attr}' em complemento.py na linha {node.lineno}")
