# coding=utf-8
"""Testes unitários para o adaptador fino GisBR (gisbr_bridge.py)."""

import types
import unittest
from unittest.mock import MagicMock, patch

from desire_lines.traffic import gisbr_bridge

SOURCES = [
    {
        "id": "der_mg_rodovias",
        "nome": "DER-MG — Rodovias estaduais",
        "protocolo": "wfs",
        "endpoint": "https://geoserver.meioambiente.mg.gov.br/IDE/wfs",
        "type_name": "IDE:ide_0401_mg_rodovias_lin",
        "srs": "EPSG:4674",
        "ufs": ["MG"],
        "rede": {"tipo": "rodoviaria"},
    },
    {
        "id": "go_malha_viaria",
        "nome": "Siga-GO — Malha viária (2024)",
        "protocolo": "wfs",
        "endpoint": "https://siga.meioambiente.go.gov.br/geoserver/ows",
        "type_name": "geonode:malha_viaria_2024",
        "srs": "EPSG:4674",
        "ufs": ["GO"],
        "rede": {"tipo": "rodoviaria"},
    },
    {
        "id": "pr_rodovias_der",
        "nome": "DER-PR — Rodovias estaduais (IAT GeoPR)",
        "protocolo": "arcgis",
        "endpoint": "https://geopr.iat.pr.gov.br/server/rest/services/00_PUBLICACOES/rodovias_der/FeatureServer",
        "ufs": ["PR"],
        "rede": {"tipo": "rodoviaria"},
    },
    {
        "id": "dnit_snv",
        "nome": "DNIT — SNV (rodovias federais)",
        "protocolo": "wfs",
        "endpoint": "https://services.dnit.gov.br/geoserver/wfs",
        "type_name": "dnit:snv_2024",
        "srs": "EPSG:4674",
    },
]


def _mock_gisbr_wfs(sources=None):
    if sources is None:
        sources = SOURCES
    sources_mod = types.ModuleType("gisbr.core.sources")
    sources_mod.SOURCES = sources
    wfs_mod = types.ModuleType("gisbr.core.connectors.wfs")
    mock_fetch = MagicMock()
    mock_layer = MagicMock()
    mock_layer.isValid.return_value = True
    mock_fetch.return_value = mock_layer
    wfs_mod.fetch_layer = mock_fetch

    modules = {
        "gisbr": types.ModuleType("gisbr"),
        "gisbr.core": types.ModuleType("gisbr.core"),
        "gisbr.core.sources": sources_mod,
        "gisbr.core.connectors": types.ModuleType("gisbr.core.connectors"),
        "gisbr.core.connectors.wfs": wfs_mod,
    }
    return patch.dict("sys.modules", modules), mock_fetch


def _mock_gisbr_recortes():
    rm_mod = types.ModuleType("gisbr.core.regioes_metropolitanas")
    div_mod = types.ModuleType("gisbr.core.divisao_regional")
    macro_mod = types.ModuleType("gisbr.core.macro_saude")
    recorte_mod = types.ModuleType("gisbr.core.recorte")

    rm_mod.listar_por_uf = MagicMock(return_value=[{"id": "04501", "nome": "RMBH"}])
    rm_mod.codes = MagicMock(return_value=["3105004", "3106200"])

    div_mod.listar = MagicMock(return_value=[("31001", "Micro Sete Lagoas")])
    div_mod.municipios = MagicMock(return_value=[("3100101", "Muni A")])

    macro_mod.listar = MagicMock(return_value=[("3101", "Macro Centro")])
    macro_mod.municipios = MagicMock(return_value=[("3106200", "Belo Horizonte")])

    mock_recorte_cls = MagicMock()
    mock_recorte_obj = MagicMock()
    mock_recorte_cls.de_rm.return_value = mock_recorte_obj
    mock_recorte_cls.de_agregado.return_value = mock_recorte_obj
    recorte_mod.Recorte = mock_recorte_cls

    mock_layer = MagicMock()
    mock_extent = MagicMock()
    mock_extent.xMinimum.return_value = -44.0
    mock_extent.yMinimum.return_value = -20.0
    mock_extent.xMaximum.return_value = -43.0
    mock_extent.yMaximum.return_value = -19.0
    mock_layer.extent.return_value = mock_extent
    recorte_mod.camada_do_recorte = MagicMock(return_value=mock_layer)

    modules = {
        "gisbr": types.ModuleType("gisbr"),
        "gisbr.core": types.ModuleType("gisbr.core"),
        "gisbr.core.regioes_metropolitanas": rm_mod,
        "gisbr.core.divisao_regional": div_mod,
        "gisbr.core.macro_saude": macro_mod,
        "gisbr.core.recorte": recorte_mod,
    }
    mocks = {
        "rm": rm_mod,
        "div": div_mod,
        "macro": macro_mod,
        "recorte": recorte_mod,
        "recorte_cls": mock_recorte_cls,
        "layer": mock_layer,
        "extent": mock_extent,
    }
    return patch.dict("sys.modules", modules), mocks


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

    def test_wfs_connector_chooses_go_source(self):
        """uf='GO' escolhe a fonte GO."""
        p, mock_fetch = _mock_gisbr_wfs()
        with p:
            layer = gisbr_bridge._try_wfs_connector(None, None, uf="GO")
            self.assertIsNotNone(layer)
            mock_fetch.assert_called_once()
            _, kwargs = mock_fetch.call_args
            self.assertEqual(kwargs["type_name"], "geonode:malha_viaria_2024")
            self.assertEqual(kwargs["endpoint"], "https://siga.meioambiente.go.gov.br/geoserver/ows")

    def test_wfs_connector_falls_back_to_dnit_for_pr_arcgis(self):
        """uf='PR' com fonte PR protocolo: 'arcgis' cai em dnit_snv."""
        p, mock_fetch = _mock_gisbr_wfs()
        with p:
            layer = gisbr_bridge._try_wfs_connector(None, None, uf="PR")
            self.assertIsNotNone(layer)
            mock_fetch.assert_called_once()
            _, kwargs = mock_fetch.call_args
            self.assertEqual(kwargs["type_name"], "dnit:snv_2024")
            self.assertEqual(kwargs["endpoint"], "https://services.dnit.gov.br/geoserver/wfs")

    def test_wfs_connector_chooses_mg_source_regression(self):
        """uf='MG' continua escolhendo der_mg_rodovias (regressão)."""
        p, mock_fetch = _mock_gisbr_wfs()
        with p:
            layer = gisbr_bridge._try_wfs_connector(None, None, uf="MG")
            self.assertIsNotNone(layer)
            mock_fetch.assert_called_once()
            _, kwargs = mock_fetch.call_args
            self.assertEqual(kwargs["type_name"], "IDE:ide_0401_mg_rodovias_lin")
            self.assertEqual(kwargs["endpoint"], "https://geoserver.meioambiente.mg.gov.br/IDE/wfs")

    def test_listar_recortes_rm(self):
        """listar_recortes normaliza saída de dicts de regioes_metropolitanas para tuplas (id, nome)."""
        p, mocks = _mock_gisbr_recortes()
        mocks["rm"].listar_por_uf.return_value = [
            {"id": "04501", "nome": "Região Metropolitana de Belo Horizonte", "uf": "MG"}
        ]
        with p:
            resultado = gisbr_bridge.listar_recortes("rm", "MG")
            self.assertEqual(resultado, [("04501", "Região Metropolitana de Belo Horizonte")])
            mocks["rm"].listar_por_uf.assert_called_once_with("MG")

    def test_listar_recortes_micro(self):
        """listar_recortes com tipo 'micro' despacha para divisao_regional.listar."""
        p, mocks = _mock_gisbr_recortes()
        mocks["div"].listar.return_value = [("31001", "Micro Sete Lagoas")]
        with p:
            resultado = gisbr_bridge.listar_recortes("micro", "MG")
            self.assertEqual(resultado, [("31001", "Micro Sete Lagoas")])
            mocks["div"].listar.assert_called_once_with("micro", "MG")

    def test_listar_recortes_meso(self):
        """listar_recortes com tipo 'meso' despacha para divisao_regional.listar."""
        p, mocks = _mock_gisbr_recortes()
        mocks["div"].listar.return_value = [("3101", "Meso Central")]
        with p:
            resultado = gisbr_bridge.listar_recortes("meso", "MG")
            self.assertEqual(resultado, [("3101", "Meso Central")])
            mocks["div"].listar.assert_called_once_with("meso", "MG")

    def test_listar_recortes_macsaud(self):
        """listar_recortes com tipo 'macsaud' despacha para macro_saude.listar."""
        p, mocks = _mock_gisbr_recortes()
        mocks["macro"].listar.return_value = [("3101", "Macro Centro")]
        with p:
            resultado = gisbr_bridge.listar_recortes("macsaud", "MG")
            self.assertEqual(resultado, [("3101", "Macro Centro")])
            mocks["macro"].listar.assert_called_once_with("MG")

    def test_listar_recortes_import_error(self):
        """listar_recortes devolve [] se ocorrer ImportError (ex.: GisBR ausente/antigo)."""
        with patch.dict(
            "sys.modules",
            {
                "gisbr": None,
                "gisbr.core": None,
                "gisbr.core.regioes_metropolitanas": None,
            },
        ):
            resultado = gisbr_bridge.listar_recortes("rm", "MG")
            self.assertEqual(resultado, [])

    def test_listar_recortes_tipo_invalido(self):
        """listar_recortes devolve [] se tipo não for de TIPOS_RECORTE."""
        resultado = gisbr_bridge.listar_recortes("tipo_invalido", "MG")
        self.assertEqual(resultado, [])

    def test_extensao_recorte_tipo_invalido(self):
        """extensao_recorte levanta ValueError para tipo fora de TIPOS_RECORTE."""
        with self.assertRaises(ValueError):
            gisbr_bridge.extensao_recorte("tipo_invalido", "04501")

    def test_extensao_recorte_rm_sucesso(self):
        """extensao_recorte('rm', '04501') monta o Recorte com os códigos certos e devolve extensão."""
        p, mocks = _mock_gisbr_recortes()
        mocks["rm"].codes.return_value = ["3105004", "3106200"]
        with p:
            ext = gisbr_bridge.extensao_recorte("rm", "04501")
            mocks["rm"].codes.assert_called_once_with("04501")
            mocks["recorte_cls"].de_rm.assert_called_once()
            call_args = mocks["recorte_cls"].de_rm.call_args[0]
            self.assertEqual(call_args[0], "04501")
            self.assertEqual(call_args[2], ["3105004", "3106200"])
            mocks["recorte"].camada_do_recorte.assert_called_once_with(
                mocks["recorte_cls"].de_rm.return_value
            )
            self.assertEqual(ext, (-44.0, -20.0, -43.0, -19.0))

    def test_extensao_recorte_camada_none(self):
        """extensao_recorte levanta RuntimeError (com tipo e id) quando camada_do_recorte devolve None."""
        p, mocks = _mock_gisbr_recortes()
        mocks["recorte"].camada_do_recorte.return_value = None
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.extensao_recorte("rm", "04501")
            msg = str(ctx.exception)
            self.assertIn("rm", msg)
            self.assertIn("04501", msg)

    def test_extensao_recorte_sem_municipio(self):
        """extensao_recorte levanta RuntimeError (com tipo e id) quando não há municípios."""
        p, mocks = _mock_gisbr_recortes()
        mocks["rm"].codes.return_value = []
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.extensao_recorte("rm", "04501")
            msg = str(ctx.exception)
            self.assertIn("rm", msg)
            self.assertIn("04501", msg)

    def test_extensao_recorte_micro_sucesso(self):
        """extensao_recorte para micro monta Recorte.de_agregado e devolve extensão."""
        p, mocks = _mock_gisbr_recortes()
        mocks["div"].municipios.return_value = [("3100101", "Muni A"), ("3100102", "Muni B")]
        with p:
            ext = gisbr_bridge.extensao_recorte("micro", "31001")
            mocks["div"].municipios.assert_called_once_with("micro", "31001")
            mocks["recorte_cls"].de_agregado.assert_called_once()
            call_args = mocks["recorte_cls"].de_agregado.call_args[0]
            self.assertEqual(call_args[0], "micro")
            self.assertEqual(call_args[1], "31001")
            self.assertEqual(call_args[3], ["3100101", "3100102"])
            self.assertEqual(ext, (-44.0, -20.0, -43.0, -19.0))


if __name__ == "__main__":
    unittest.main()
