# coding=utf-8
"""Testes unitários para o módulo ui_common.py (D3)."""

import inspect
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from test.utilities import get_qgis_app

QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)

from desire_lines.ui_common import PluginUiMixin, write_layer_to_gpkg_file


def _create_memory_layer(name, num_features=1):
    """Cria uma camada vetorial de pontos em memória com feições de teste."""
    layer = QgsVectorLayer("Point?crs=EPSG:4326", name, "memory")
    dp = layer.dataProvider()
    features = []
    for i in range(num_features):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(i), float(i))))
        features.append(feat)
    dp.addFeatures(features)
    layer.updateExtents()
    return layer


class TestWriteLayerToGpkgFile(unittest.TestCase):
    """Testes da função write_layer_to_gpkg_file (D3)."""

    def test_grava_camada_memoria_no_gpkg(self):
        """Grava camada de memória num GPKG em tempfile e URI devolvida abre válida com contagem certa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = os.path.join(tmpdir, "test_output.gpkg")
            layer = _create_memory_layer("pontos", num_features=3)
            ctx = QgsCoordinateTransformContext()

            uri = write_layer_to_gpkg_file(layer, gpkg_path, "pontos", ctx)
            expected_uri = f"{gpkg_path}|layername=pontos"
            self.assertEqual(uri, expected_uri)

            loaded_layer = QgsVectorLayer(uri, "pontos", "ogr")
            self.assertTrue(loaded_layer.isValid())
            self.assertEqual(loaded_layer.featureCount(), 3)

    def test_segunda_tabela_no_mesmo_arquivo_nao_apaga_primeira(self):
        """Uma segunda tabela no mesmo arquivo não apaga a primeira."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = os.path.join(tmpdir, "multi_table.gpkg")
            ctx = QgsCoordinateTransformContext()

            layer1 = _create_memory_layer("tabela_a", num_features=2)
            uri1 = write_layer_to_gpkg_file(layer1, gpkg_path, "tabela_a", ctx)

            layer2 = _create_memory_layer("tabela_b", num_features=4)
            uri2 = write_layer_to_gpkg_file(layer2, gpkg_path, "tabela_b", ctx)

            loaded_a = QgsVectorLayer(uri1, "tabela_a", "ogr")
            loaded_b = QgsVectorLayer(uri2, "tabela_b", "ogr")

            self.assertTrue(loaded_a.isValid())
            self.assertTrue(loaded_b.isValid())
            self.assertEqual(loaded_a.featureCount(), 2)
            self.assertEqual(loaded_b.featureCount(), 4)

    def test_erro_writer_diretorio_inexistente_levanta_runtime_error(self):
        """Erro do writer (caminho num diretório inexistente) levanta RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "nao_existe_dir", "output.gpkg")
            layer = _create_memory_layer("falha", num_features=1)
            ctx = QgsCoordinateTransformContext()

            with self.assertRaises(RuntimeError) as cm:
                write_layer_to_gpkg_file(layer, bad_path, "falha", ctx)
            self.assertIn("Failed to write layer to GPKG", str(cm.exception))

    def test_tabela_vazia_levanta_value_error(self):
        """Nome de tabela vazio ou nulo levanta ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gpkg_path = os.path.join(tmpdir, "test_empty_table.gpkg")
            layer = _create_memory_layer("vazia", num_features=1)
            ctx = QgsCoordinateTransformContext()

            with self.assertRaises(ValueError):
                write_layer_to_gpkg_file(layer, gpkg_path, "", ctx)
            with self.assertRaises(ValueError):
                write_layer_to_gpkg_file(layer, gpkg_path, None, ctx)

    def test_sem_qgs_project_nem_iface_no_corpo_de_write_layer_to_gpkg_file(self):
        """Garante que QgsProject e iface não aparecem no corpo de write_layer_to_gpkg_file."""
        import desire_lines.ui_common as mod
        src = inspect.getsource(mod.write_layer_to_gpkg_file)
        self.assertNotIn("QgsProject", src)
        self.assertNotIn("iface", src)


class DummyDialog(PluginUiMixin):
    """Classe simples para testar PluginUiMixin."""

    def __init__(self, output_path):
        self.out_path = output_path
        self.last_message = None

    def _output_path(self):
        return self.out_path


class TestPluginUiMixin(unittest.TestCase):
    """Testes do PluginUiMixin e delegação para write_layer_to_gpkg_file."""

    def test_write_layer_to_gpkg_delega_para_write_layer_to_gpkg_file(self):
        """_write_layer_to_gpkg delega para write_layer_to_gpkg_file e iface.addVectorLayer."""
        dlg = DummyDialog("/tmp/dummy_output.gpkg")
        mock_layer = MagicMock()

        with patch("desire_lines.ui_common.write_layer_to_gpkg_file") as mock_write, \
             patch("desire_lines.ui_common.iface") as mock_iface:
            mock_write.return_value = "/tmp/dummy_output.gpkg|layername=centroids"
            mock_iface.addVectorLayer.return_value = MagicMock()

            result = dlg._write_layer_to_gpkg(mock_layer, "centroids")

            mock_write.assert_called_once_with(
                mock_layer,
                "/tmp/dummy_output.gpkg",
                "centroids",
                QgsProject.instance().transformContext(),
            )
            mock_iface.addVectorLayer.assert_called_once_with(
                "/tmp/dummy_output.gpkg|layername=centroids",
                "centroids",
                "ogr",
            )
            self.assertEqual(result, mock_iface.addVectorLayer.return_value)

    def test_zone_key_normalizacao(self):
        """Normalização de zone key lida com None, int, float e strings."""
        self.assertIsNone(PluginUiMixin._zone_key(None))
        self.assertEqual(PluginUiMixin._zone_key(42), 42)
        self.assertEqual(PluginUiMixin._zone_key("42"), 42)
        self.assertEqual(PluginUiMixin._zone_key(42.0), 42)
        self.assertEqual(PluginUiMixin._zone_key("42.0"), 42)
        self.assertEqual(PluginUiMixin._zone_key(" zona_1 "), "zona_1")


if __name__ == "__main__":
    unittest.main()
