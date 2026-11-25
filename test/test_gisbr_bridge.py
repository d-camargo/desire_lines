# coding=utf-8
"""Testes unitários para o adaptador fino GisBR (gisbr_bridge.py)."""

import os
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

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
        "layer_id": "0",
        "ufs": ["PR"],
        "rede": {"tipo": "rodoviaria"},
    },
    {
        "id": "der_sp_rodovias",
        "nome": "DER-SP — Rodovias estaduais",
        "protocolo": "zip_remoto",
        "endpoint": "https://dersp.der.sp.gov.br/malha.zip",
        "cache_id": "der_sp.zip",
        "srs": "EPSG:4674",
        "ufs": ["SP"],
        "rede": {"tipo": "rodoviaria"},
    },
    {
        "id": "ibge_bc250_rodovias",
        "nome": "IBGE — BC250 Rodovias",
        "protocolo": "wfs",
        "endpoint": "https://geoservicos.ibge.gov.br/geoserver/wfs",
        "type_name": "bc250:rodovia",
        "srs": "EPSG:4674",
        "ufs": ["MG", "BA"],
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

CAPITAIS = {
    "AC": (-67.8243, -9.97499),
    "AL": (-35.735, -9.66599),
    "AP": (-51.0594, 0.0389),
    "AM": (-60.0212, -3.11866),
    "BA": (-38.5024, -12.9747),
    "CE": (-38.527, -3.71664),
    "DF": (-47.8825, -15.7939),
    "ES": (-40.3378, -20.3197),
    "GO": (-49.2563, -16.6864),
    "MA": (-44.2825, -2.53874),
    "MT": (-56.0974, -15.5989),
    "MS": (-54.6464, -20.4486),
    "MG": (-43.9386, -19.9173),
    "PA": (-48.4878, -1.4554),
    "PB": (-34.8641, -7.11509),
    "PR": (-49.2731, -25.4277),
    "PE": (-34.8811, -8.05389),
    "PI": (-42.8034, -5.09194),
    "RJ": (-43.2096, -22.9035),
    "RN": (-35.2081, -5.79357),
    "RS": (-51.2304, -30.0331),
    "RO": (-63.8999, -8.76183),
    "RR": (-60.6713, 2.82384),
    "SC": (-48.5496, -27.5949),
    "SP": (-46.6361, -23.5475),
    "SE": (-37.0717, -10.9167),
    "TO": (-48.3336, -10.1844),
}


def _mock_gisbr_connectors(sources=None):
    if sources is None:
        sources = SOURCES
    sources_mod = types.ModuleType("gisbr.core.sources")
    sources_mod.SOURCES = sources

    wfs_mod = types.ModuleType("gisbr.core.connectors.wfs")
    mock_wfs = MagicMock()
    mock_layer_wfs = MagicMock()
    mock_layer_wfs.isValid.return_value = True
    mock_wfs.return_value = mock_layer_wfs
    wfs_mod.fetch_layer = mock_wfs

    arcgis_mod = types.ModuleType("gisbr.core.connectors.arcgis_rest")
    mock_arcgis = MagicMock()
    mock_layer_arcgis = MagicMock()
    mock_layer_arcgis.isValid.return_value = True
    mock_arcgis.return_value = mock_layer_arcgis
    arcgis_mod.fetch_layer = mock_arcgis

    zip_mod = types.ModuleType("gisbr.core.connectors.zip_remoto")
    mock_zip = MagicMock()
    mock_layer_zip = MagicMock()
    mock_layer_zip.isValid.return_value = True
    mock_zip.return_value = mock_layer_zip
    zip_mod.fetch_layer = mock_zip

    modules = {
        "gisbr": types.ModuleType("gisbr"),
        "gisbr.core": types.ModuleType("gisbr.core"),
        "gisbr.core.sources": sources_mod,
        "gisbr.core.connectors": types.ModuleType("gisbr.core.connectors"),
        "gisbr.core.connectors.wfs": wfs_mod,
        "gisbr.core.connectors.arcgis_rest": arcgis_mod,
        "gisbr.core.connectors.zip_remoto": zip_mod,
    }
    mocks = {
        "wfs": mock_wfs,
        "arcgis": mock_arcgis,
        "zip": mock_zip,
        "layer_wfs": mock_layer_wfs,
        "layer_arcgis": mock_layer_arcgis,
        "layer_zip": mock_layer_zip,
    }
    return patch.dict("sys.modules", modules), mocks


def _mock_gisbr_wfs(sources=None):
    p, mocks = _mock_gisbr_connectors(sources)
    return p, mocks["wfs"]


def _mock_processing(run_return=None, run_side_effect=None):
    mock_proc = types.ModuleType("processing")
    mock_run = MagicMock()
    if run_side_effect is not None:
        mock_run.side_effect = run_side_effect
    elif run_return is not None:
        mock_run.return_value = run_return
    mock_proc.run = mock_run
    return patch.dict("sys.modules", {"processing": mock_proc}), mock_run


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

    mock_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "recorte", "memory")
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromRect(QgsRectangle(-44.0, -20.0, -43.0, -19.0)))
    mock_layer.dataProvider().addFeatures([feat])
    mock_layer.updateExtents()
    mock_extent = mock_layer.extent()
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

    def test_fontes_rodoviarias_mg(self):
        """MG devolve ['dnit_snv', 'der_mg_rodovias'] na ordem de precedência de D2."""
        p, _ = _mock_gisbr_wfs()
        with p:
            fontes = gisbr_bridge.fontes_rodoviarias("MG")
            ids = [f["id"] for f in fontes]
            self.assertEqual(ids, ["dnit_snv", "der_mg_rodovias"])

    def test_fontes_rodoviarias_ba(self):
        """BA não possui fonte estadual no catálogo mockado, devolve apenas dnit_snv."""
        p, _ = _mock_gisbr_wfs()
        with p:
            fontes = gisbr_bridge.fontes_rodoviarias("BA")
            ids = [f["id"] for f in fontes]
            self.assertEqual(ids, ["dnit_snv"])

    def test_fontes_rodoviarias_ignora_ibge_bc250(self):
        """ibge_bc250_rodovias nunca aparece pois não possui rede.tipo == 'rodoviaria'."""
        p, _ = _mock_gisbr_wfs()
        with p:
            fontes = gisbr_bridge.fontes_rodoviarias("MG")
            ids = [f["id"] for f in fontes]
            self.assertNotIn("ibge_bc250_rodovias", ids)

    def test_fontes_rodoviarias_gisbr_ausente(self):
        """Devolve [] se o GisBR não importar."""
        with patch.dict("sys.modules", {"gisbr": None, "gisbr.core.sources": None}):
            self.assertEqual(gisbr_bridge.fontes_rodoviarias("MG"), [])
            self.assertEqual(gisbr_bridge.fontes_rodoviarias(""), [])

    def test_baixar_fonte_despacho_protocolos(self):
        """Cada protocolo chama o conector certo (wfs, arcgis_rest, zip_remoto)."""
        p, mocks = _mock_gisbr_connectors()
        with p:
            # WFS: dnit_snv
            fonte_wfs = next(s for s in SOURCES if s["id"] == "dnit_snv")
            layer_wfs = gisbr_bridge.baixar_fonte(fonte_wfs, bbox_4674=(-44, -20, -43, -19))
            self.assertEqual(layer_wfs, mocks["layer_wfs"])
            mocks["wfs"].assert_called_once()
            _, kwargs_wfs = mocks["wfs"].call_args
            self.assertEqual(kwargs_wfs["endpoint"], fonte_wfs["endpoint"])
            self.assertEqual(kwargs_wfs["type_name"], fonte_wfs["type_name"])
            self.assertEqual(kwargs_wfs["bbox"], (-44, -20, -43, -19))

            # ArcGIS: pr_rodovias_der
            fonte_arcgis = next(s for s in SOURCES if s["id"] == "pr_rodovias_der")
            layer_arcgis = gisbr_bridge.baixar_fonte(fonte_arcgis, bbox_4674=(-50, -25, -49, -24))
            self.assertEqual(layer_arcgis, mocks["layer_arcgis"])
            mocks["arcgis"].assert_called_once()
            _, kwargs_arcgis = mocks["arcgis"].call_args
            self.assertEqual(kwargs_arcgis["endpoint"], fonte_arcgis["endpoint"])
            self.assertEqual(kwargs_arcgis["layer_id"], "0")
            self.assertEqual(kwargs_arcgis["bbox"], (-50, -25, -49, -24))

            # ZIP remoto: der_sp_rodovias
            fonte_zip = next(s for s in SOURCES if s["id"] == "der_sp_rodovias")
            layer_zip = gisbr_bridge.baixar_fonte(fonte_zip, bbox_4674=(-47, -23, -46, -22))
            self.assertEqual(layer_zip, mocks["layer_zip"])
            mocks["zip"].assert_called_once()
            _, kwargs_zip = mocks["zip"].call_args
            self.assertEqual(kwargs_zip["url"], fonte_zip["endpoint"])
            self.assertEqual(kwargs_zip["cache_id"], fonte_zip["cache_id"])

    def test_baixar_fonte_wfs_substitui_uf(self):
        """baixar_fonte substitui {uf} no type_name para conectores WFS."""
        p, mocks = _mock_gisbr_connectors()
        fonte_template = {
            "id": "teste_uf",
            "nome": "Camada Teste UF",
            "protocolo": "wfs",
            "endpoint": "https://example.com/wfs",
            "type_name": "sicar:imoveis_{uf}",
            "ufs": ["MG"],
        }
        with p:
            gisbr_bridge.baixar_fonte(fonte_template, bbox_4674=None)
            _, kwargs = mocks["wfs"].call_args
            self.assertEqual(kwargs["type_name"], "sicar:imoveis_mg")

    def test_baixar_fonte_camada_invalida_levanta_com_nome_da_fonte(self):
        """Camada inválida levanta RuntimeError com o nome da fonte."""
        p, mocks = _mock_gisbr_connectors()
        mocks["layer_wfs"].isValid.return_value = False
        mocks["layer_wfs"].error_msg = "Timeout 504 no servidor WFS"
        fonte = next(s for s in SOURCES if s["id"] == "dnit_snv")
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.baixar_fonte(fonte, bbox_4674=None)
            msg = str(ctx.exception)
            self.assertIn(fonte["nome"], msg)
            self.assertIn("Timeout 504 no servidor WFS", msg)

    def test_bbox_uf_27_ufs_e_contem_capitais(self):
        """BBOX_UF possui exatamente as 27 UFs brasileiras e cada bbox contém a respectiva capital."""
        self.assertEqual(len(gisbr_bridge.BBOX_UF), 27)
        self.assertEqual(set(gisbr_bridge.BBOX_UF.keys()), set(CAPITAIS.keys()))
        for uf, (cx, cy) in CAPITAIS.items():
            minx, miny, maxx, maxy = gisbr_bridge.BBOX_UF[uf]
            self.assertLessEqual(minx, cx, f"minx ({minx}) > capital lon ({cx}) em {uf}")
            self.assertGreaterEqual(maxx, cx, f"maxx ({maxx}) < capital lon ({cx}) em {uf}")
            self.assertLessEqual(miny, cy, f"miny ({miny}) > capital lat ({cy}) em {uf}")
            self.assertGreaterEqual(maxy, cy, f"maxy ({maxy}) < capital lat ({cy}) em {uf}")

    def test_limite_uf_sp_valido_4674(self):
        """(a) limite_uf('SP') devolve polígono válido em EPSG:4674."""
        layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "uf_sp", "memory")
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromRect(QgsRectangle(-53.0, -25.0, -44.0, -20.0)))
        layer.dataProvider().addFeatures([feat])

        p, mock_run = _mock_processing(run_return={"OUTPUT": layer})
        with p:
            geom = gisbr_bridge.limite_uf("SP")
            mock_run.assert_called_once_with(
                "gisbr:read_state",
                {"CODE": "SP", "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT"},
            )
            self.assertIsInstance(geom, QgsGeometry)
            self.assertTrue(geom.isGeosValid())
            self.assertFalse(geom.isEmpty())
            bbox = geom.boundingBox()
            self.assertAlmostEqual(bbox.xMinimum(), -53.0)
            self.assertAlmostEqual(bbox.yMinimum(), -25.0)
            self.assertAlmostEqual(bbox.xMaximum(), -44.0)
            self.assertAlmostEqual(bbox.yMaximum(), -20.0)

    def test_limite_uf_duas_feicoes_viram_uma_geometria(self):
        """(b) duas feições viram uma geometria unida."""
        layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "uf_sp", "memory")
        feat1 = QgsFeature()
        feat1.setGeometry(QgsGeometry.fromRect(QgsRectangle(-50.0, -24.0, -48.0, -22.0)))
        feat2 = QgsFeature()
        feat2.setGeometry(QgsGeometry.fromRect(QgsRectangle(-48.0, -24.0, -46.0, -22.0)))
        layer.dataProvider().addFeatures([feat1, feat2])

        p, _ = _mock_processing(run_return={"OUTPUT": layer})
        with p:
            geom = gisbr_bridge.limite_uf("SP")
            self.assertIsInstance(geom, QgsGeometry)
            self.assertTrue(geom.isGeosValid())
            bbox = geom.boundingBox()
            self.assertAlmostEqual(bbox.xMinimum(), -50.0)
            self.assertAlmostEqual(bbox.yMinimum(), -24.0)
            self.assertAlmostEqual(bbox.xMaximum(), -46.0)
            self.assertAlmostEqual(bbox.yMaximum(), -22.0)

    def test_limite_uf_erros_com_sp_na_mensagem(self):
        """(c) None, camada vazia e exceção levantam RuntimeError com 'SP' na mensagem."""
        # 1. Retorno None
        p_none, _ = _mock_processing(run_return=None)
        with p_none:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_uf("SP")
            self.assertIn("SP", str(ctx.exception))

        # 2. OUTPUT None
        p_out_none, _ = _mock_processing(run_return={"OUTPUT": None})
        with p_out_none:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_uf("SP")
            self.assertIn("SP", str(ctx.exception))

        # 3. Camada vazia
        empty_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "empty", "memory")
        p_empty, _ = _mock_processing(run_return={"OUTPUT": empty_layer})
        with p_empty:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_uf("SP")
            self.assertIn("SP", str(ctx.exception))

        # 4. Exceção levantada pelo processing.run
        p_exc, _ = _mock_processing(run_side_effect=RuntimeError("Falha de conexão"))
        with p_exc:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_uf("SP")
            self.assertIn("SP", str(ctx.exception))

    def test_limite_uf_caminho_arquivo(self):
        """limite_uf aceita caminho em disco retornado pelo Processing."""
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            mem_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "sp", "memory")
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromRect(QgsRectangle(-47.0, -24.0, -46.0, -23.0)))
            mem_layer.dataProvider().addFeatures([feat])
            QgsVectorFileWriter.writeAsVectorFormatV3(
                mem_layer,
                tmp_path,
                mem_layer.transformContext(),
                QgsVectorFileWriter.SaveVectorOptions(),
            )

            p, _ = _mock_processing(run_return={"OUTPUT": tmp_path})
            with p:
                geom = gisbr_bridge.limite_uf("SP")
                self.assertIsInstance(geom, QgsGeometry)
                self.assertTrue(geom.isGeosValid())
                bbox = geom.boundingBox()
                self.assertAlmostEqual(bbox.xMinimum(), -47.0)
                self.assertAlmostEqual(bbox.xMaximum(), -46.0)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_limite_uf_reprojecao_crs_diferente(self):
        """limite_uf transforma geometria para EPSG:4674 quando o CRS da camada diferir."""
        # EPSG:31983 (SIRGAS 2000 / UTM zone 23S)
        layer = QgsVectorLayer("Polygon?crs=EPSG:31983", "sp_utm", "memory")
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromRect(QgsRectangle(500000, 7400000, 510000, 7410000)))
        layer.dataProvider().addFeatures([feat])

        p, _ = _mock_processing(run_return={"OUTPUT": layer})
        with p:
            geom = gisbr_bridge.limite_uf("SP")
            self.assertTrue(geom.isGeosValid())
            bbox = geom.boundingBox()
            self.assertLess(bbox.xMinimum(), 0.0)
            self.assertGreater(bbox.xMinimum(), -60.0)
            self.assertLess(bbox.yMinimum(), 0.0)
            self.assertGreater(bbox.yMinimum(), -40.0)

    def test_limite_recorte_sucesso(self):
        """limite_recorte devolve QgsGeometry unida em EPSG:4674 a partir de camada_do_recorte."""
        p, mocks = _mock_gisbr_recortes()
        with p:
            geom = gisbr_bridge.limite_recorte("rm", "04501")
            self.assertIsInstance(geom, QgsGeometry)
            self.assertTrue(geom.isGeosValid())
            bbox = geom.boundingBox()
            self.assertAlmostEqual(bbox.xMinimum(), -44.0)
            self.assertAlmostEqual(bbox.yMinimum(), -20.0)
            self.assertAlmostEqual(bbox.xMaximum(), -43.0)
            self.assertAlmostEqual(bbox.yMaximum(), -19.0)

    def test_limite_recorte_duas_feicoes(self):
        """limite_recorte une múltiplas feições retornadas por camada_do_recorte."""
        p, mocks = _mock_gisbr_recortes()
        layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "duas", "memory")
        feat1 = QgsFeature()
        feat1.setGeometry(QgsGeometry.fromRect(QgsRectangle(-45.0, -20.0, -44.0, -19.0)))
        feat2 = QgsFeature()
        feat2.setGeometry(QgsGeometry.fromRect(QgsRectangle(-44.0, -20.0, -43.0, -19.0)))
        layer.dataProvider().addFeatures([feat1, feat2])
        mocks["recorte"].camada_do_recorte.return_value = layer

        with p:
            geom = gisbr_bridge.limite_recorte("micro", "31001")
            self.assertIsInstance(geom, QgsGeometry)
            self.assertTrue(geom.isGeosValid())
            bbox = geom.boundingBox()
            self.assertAlmostEqual(bbox.xMinimum(), -45.0)
            self.assertAlmostEqual(bbox.xMaximum(), -43.0)

    def test_limite_recorte_erros(self):
        """limite_recorte levanta RuntimeError com tipo e id quando None, vazia ou exceção."""
        p, mocks = _mock_gisbr_recortes()

        # 1. camada_do_recorte devolve None
        mocks["recorte"].camada_do_recorte.return_value = None
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_recorte("rm", "04501")
            msg = str(ctx.exception)
            self.assertIn("rm", msg)
            self.assertIn("04501", msg)

        # 2. camada_do_recorte devolve camada vazia
        empty_layer = QgsVectorLayer("Polygon?crs=EPSG:4674", "empty", "memory")
        mocks["recorte"].camada_do_recorte.return_value = empty_layer
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_recorte("rm", "04501")
            msg = str(ctx.exception)
            self.assertIn("rm", msg)
            self.assertIn("04501", msg)

        # 3. camada_do_recorte levanta exceção
        mocks["recorte"].camada_do_recorte.side_effect = RuntimeError("Falha interna")
        with p:
            with self.assertRaises(RuntimeError) as ctx:
                gisbr_bridge.limite_recorte("rm", "04501")
            msg = str(ctx.exception)
            self.assertIn("rm", msg)
            self.assertIn("04501", msg)


if __name__ == "__main__":
    unittest.main()
