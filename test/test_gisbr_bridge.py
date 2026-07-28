# coding=utf-8
"""Testes unitários para o adaptador fino GisBR (gisbr_bridge.py)."""

import unittest
from unittest.mock import MagicMock, patch

from desire_lines.traffic import gisbr_bridge


class TestGisbrBridge(unittest.TestCase):
    """Testes com dublês para os 3 caminhos do GisBR bridge."""

    def test_missing_message(self):
        """missing_message deve retornar texto explicativo contendo a URL de referência."""
        msg = gisbr_bridge.missing_message()
        self.assertIn("https://github.com/d-camargo/gisbr", msg)

    @patch("desire_lines.traffic.gisbr_bridge.is_available", return_value=False)
    def test_gisbr_absent(self, mock_is_avail):
        """Caminho 1: quando GisBR está ausente, fetch_road_network levanta RuntimeError com a mensagem."""
        with self.assertRaises(RuntimeError) as ctx:
            gisbr_bridge.fetch_road_network(bbox=(0, 0, 1, 1), crs="EPSG:4674")
        self.assertIn("https://github.com/d-camargo/gisbr", str(ctx.exception))

    @patch("desire_lines.traffic.gisbr_bridge.is_available", return_value=True)
    @patch("desire_lines.traffic.gisbr_bridge._try_processing_algorithm")
    def test_algorithm_present(self, mock_try_alg, mock_is_avail):
        """Caminho 2: quando o algoritmo no Processing está presente, ele deve ser chamado e retornado."""
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = True
        mock_try_alg.return_value = mock_layer

        layer = gisbr_bridge.fetch_road_network(bbox=(0, 0, 1, 1), crs="EPSG:4674")

        mock_try_alg.assert_called_once_with((0, 0, 1, 1), "EPSG:4674", None)
        self.assertEqual(layer, mock_layer)

    @patch("desire_lines.traffic.gisbr_bridge.is_available", return_value=True)
    @patch("desire_lines.traffic.gisbr_bridge._try_processing_algorithm", return_value=None)
    @patch("desire_lines.traffic.gisbr_bridge._try_wfs_connector")
    def test_only_connector_present(self, mock_try_wfs, mock_try_alg, mock_is_avail):
        """Caminho 3: quando o algoritmo não existe mas o conector WFS funciona, retorna o layer do conector."""
        mock_layer = MagicMock()
        mock_layer.isValid.return_value = True
        mock_try_wfs.return_value = mock_layer

        layer = gisbr_bridge.fetch_road_network(bbox=(0, 0, 1, 1), crs="EPSG:4674", uf="MG")

        mock_try_alg.assert_called_once_with((0, 0, 1, 1), "EPSG:4674", "MG")
        mock_try_wfs.assert_called_once_with((0, 0, 1, 1), "EPSG:4674", "MG")
        self.assertEqual(layer, mock_layer)

    @patch("desire_lines.traffic.gisbr_bridge.is_available", return_value=True)
    @patch("desire_lines.traffic.gisbr_bridge._try_processing_algorithm", return_value=None)
    @patch("desire_lines.traffic.gisbr_bridge._try_wfs_connector", return_value=None)
    def test_gisbr_available_but_all_methods_fail(self, mock_try_wfs, mock_try_alg, mock_is_avail):
        """Quando o GisBR é considerado disponível mas nenhum método obtém a malha, levanta exceção."""
        with self.assertRaises(RuntimeError) as ctx:
            gisbr_bridge.fetch_road_network(bbox=(0, 0, 1, 1), crs="EPSG:4674")
        self.assertIn("GisBR está disponível mas não foi possível", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
