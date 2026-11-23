# coding=utf-8
"""Testes da junção das malhas do GISBR (malha_gisbr.py, D3 e passo 5).

Geometrias sintéticas em metros: a "BR" de referência vai de (0, 0) a
(10000, 0); as "estaduais" são as geometrias novas.
"""

import unittest
from unittest.mock import MagicMock, patch
from test.utilities import get_qgis_app

QGIS_APP = get_qgis_app()

from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsFeature, QgsGeometry, QgsPointXY, QgsProject,
                       QgsVectorLayer)

from desire_lines.traffic import gisbr_bridge
from desire_lines.traffic.malha_gisbr import baixar_malha, subtrai_sobreposicao
from desire_lines.traffic.network import build_network
from desire_lines.traffic.outputs import _create_field

BR = QgsGeometry.fromWkt('LINESTRING(0 0, 10000 0)')
# Referência extra, longe de tudo: não deve interferir.
LONGE = QgsGeometry.fromWkt('LINESTRING(0 50000, 10000 50000)')


def _sub(wkt):
    res = subtrai_sobreposicao([BR, LONGE], [QgsGeometry.fromWkt(wkt)],
                               tol_m=20.0, min_sobrep_m=100.0,
                               min_pedaco_m=50.0)
    assert len(res) == 1
    return res[0]


class TestSubtraiSobreposicao(unittest.TestCase):

    def test_colinear_2km_some(self):
        r = _sub('LINESTRING(1000 5, 3000 5)')
        self.assertEqual(r['pedacos'], [])
        self.assertTrue(r['aparada'])
        self.assertAlmostEqual(r['metros_removidos'], 2000.0, delta=0.01)

    def test_segue_500m_e_diverge_3km_fica_so_divergente(self):
        r = _sub('LINESTRING(2000 3, 2500 3, 2500 3003)')
        self.assertTrue(r['aparada'])
        self.assertEqual(len(r['pedacos']), 1)
        pedaco = r['pedacos'][0]
        # Sai do buffer em y = 20: sobra 3003 - 20 = 2983 m.
        self.assertAlmostEqual(pedaco.length(), 2983.0, delta=0.01)
        self.assertGreaterEqual(pedaco.distance(BR), 20.0 - 0.01)
        self.assertAlmostEqual(r['metros_removidos'], 3500.0 - 2983.0,
                               delta=0.01)

    def test_toque_no_entroncamento_intacta(self):
        for wkt in ('LINESTRING(5000 0, 5000 3000)',       # em T, 20 m no buffer
                    'LINESTRING(4000 -1000, 6000 1000)'):  # cruza, ~57 m no buffer
            r = _sub(wkt)
            self.assertFalse(r['aparada'], wkt)
            self.assertEqual(r['metros_removidos'], 0.0)
            self.assertEqual(len(r['pedacos']), 1)
            self.assertTrue(r['pedacos'][0].equals(QgsGeometry.fromWkt(wkt)))

    def test_paralela_a_60m_intacta(self):
        r = _sub('LINESTRING(0 60, 10000 60)')
        self.assertFalse(r['aparada'])
        self.assertEqual(r['metros_removidos'], 0.0)
        self.assertEqual(len(r['pedacos']), 1)
        self.assertAlmostEqual(r['pedacos'][0].length(), 10000.0)

    def test_sobra_menor_que_50m_descartada(self):
        # Passa da ponta da BR (x=10000): fora do buffer só ~20 m.
        r = _sub('LINESTRING(8000 5, 10040 5)')
        self.assertTrue(r['aparada'])
        self.assertEqual(r['pedacos'], [])
        self.assertAlmostEqual(r['metros_removidos'], 2040.0, delta=0.01)

    def test_sobra_maior_que_50m_fica(self):
        r = _sub('LINESTRING(8000 5, 10100 5)')
        self.assertTrue(r['aparada'])
        self.assertEqual(len(r['pedacos']), 1)
        self.assertGreater(r['pedacos'][0].length(), 50.0)

    def test_uma_entrada_por_geometria_nova_na_ordem(self):
        novas = [QgsGeometry.fromWkt('LINESTRING(1000 5, 3000 5)'),
                 QgsGeometry.fromWkt('LINESTRING(0 60, 10000 60)')]
        res = subtrai_sobreposicao([BR], novas, 20.0, 100.0, 50.0)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['pedacos'], [])
        self.assertEqual(len(res[1]['pedacos']), 1)

    def test_referencia_vazia_tudo_intacto(self):
        res = subtrai_sobreposicao(
            [], [QgsGeometry.fromWkt('LINESTRING(1000 5, 3000 5)')],
            20.0, 100.0, 50.0)
        self.assertFalse(res[0]['aparada'])
        self.assertEqual(len(res[0]['pedacos']), 1)


# --- baixar_malha (passo 5) --------------------------------------------------
# Geometrias desenhadas em metros (UTM 23S, origem E=500000 N=7800000) e
# gravadas em EPSG:4674, como viriam do GISBR.

UTM = QgsCoordinateReferenceSystem('EPSG:32723')
SIRGAS = QgsCoordinateReferenceSystem('EPSG:4674')
E0, N0 = 500000.0, 7800000.0

FONTE_DNIT = {'id': 'dnit_snv', 'nome': 'DNIT — SNV (rodovias federais)',
              'protocolo': 'wfs',
              'rede': {'tipo': 'rodoviaria',
                       'excluir': {'campo': 'ds_superfi', 'valores': ['PLA']}}}
FONTE_DER = {'id': 'der_mg_rodovias', 'nome': 'DER-MG — Rodovias estaduais',
             'protocolo': 'wfs', 'ufs': ['MG'],
             'rede': {'tipo': 'rodoviaria'}}


def _camada_4674(campos, feicoes, nome):
    """Camada de memória em EPSG:4674 a partir de linhas em metros (UTM)."""
    camada = QgsVectorLayer('LineString?crs=EPSG:4674', nome, 'memory')
    camada.dataProvider().addAttributes(
        [_create_field(n, t) for n, t in campos])
    camada.updateFields()
    para_4674 = QgsCoordinateTransform(UTM, SIRGAS, QgsProject.instance())
    feats = []
    for pts, valores in feicoes:
        geom = QgsGeometry.fromPolylineXY(
            [QgsPointXY(E0 + x, N0 + y) for x, y in pts])
        geom.transform(para_4674)
        feat = QgsFeature(camada.fields())
        feat.setGeometry(geom)
        feat.setAttributes(valores)
        feats.append(feat)
    camada.dataProvider().addFeatures(feats)
    camada.updateExtents()
    return camada


def _dnit():
    return _camada_4674(
        [('vl_br', 'string'), ('ds_superfi', 'string')],
        [([(0, 0), (10000, 0)], ['040', 'PAV']),
         ([(0, 4000), (8000, 4000)], ['262', 'PLA'])],    # planejado
        'dnit')


def _der():
    return _camada_4674(
        [('codigo', 'string'), ('vl_br', 'int')],
        [([(2000, 0), (6000, 0)], ['MG-DUP', 40]),         # duplicata da BR
         ([(5000, 15), (5000, 3000)], ['MG-T', None])],    # T com folga 15 m
        'der')


def _componentes(camada):
    """Número de componentes conexos do grafo de `network.build_network`."""
    arcs = build_network(list(camada.getFeatures()))
    pai = {}

    def raiz(n):
        pai.setdefault(n, n)
        while pai[n] != n:
            pai[n] = pai[pai[n]]
            n = pai[n]
        return n

    for arc in arcs:
        pai[raiz(arc.from_node)] = raiz(arc.to_node)
    return len({raiz(n) for n in list(pai)})


BBOX_UTM = (E0 - 1000, N0 - 1000, E0 + 11000, N0 + 6000)


class TestBaixarMalha(unittest.TestCase):

    def _baixar(self, camadas, **kwargs):
        with patch.object(gisbr_bridge, 'fontes_rodoviarias',
                          return_value=[FONTE_DNIT, FONTE_DER]), \
                patch.object(gisbr_bridge, 'baixar_fonte',
                             side_effect=camadas) as mock_baixar:
            kwargs.setdefault('bbox', BBOX_UTM)
            kwargs.setdefault('bbox_crs', 'EPSG:32723')
            camada, rel = baixar_malha('MG', **kwargs)
        return camada, rel, mock_baixar

    def test_juncao_dnit_der(self):
        camada, rel, mock_baixar = self._baixar([_dnit(), _der()])
        self.assertTrue(camada.isValid())
        self.assertTrue(camada.crs().isValid())
        self.assertFalse(camada.crs().isGeographic())
        nomes = camada.fields().names()
        self.assertEqual(nomes[:2], ['fonte', 'ajuste'])
        for campo in ('vl_br', 'ds_superfi', 'codigo'):
            self.assertIn(campo, nomes)
        feats = list(camada.getFeatures())
        # Sem o PLA e sem a duplicata.
        self.assertNotIn('PLA', [f['ds_superfi'] for f in feats])
        self.assertNotIn('MG-DUP', [f['codigo'] for f in feats])
        # A BR foi dividida no T: 2 pedaços DNIT + o ramo DER.
        fontes = sorted(f['fonte'] for f in feats)
        self.assertEqual(fontes, ['der_mg_rodovias', 'dnit_snv', 'dnit_snv'])
        for f in feats:
            self.assertEqual(f['ajuste'], 'costurada')
        # Conflito de tipo (String × Integer) vira String.
        self.assertEqual(camada.fields().field('vl_br').type(),
                         camada.fields().field('fonte').type())
        # Junção em T vira nó compartilhado: um único componente conexo.
        self.assertEqual(_componentes(camada), 1)
        # bbox pedido em EPSG:4674 (D7).
        bbox_4674 = mock_baixar.call_args_list[0][0][1]
        self.assertTrue(-46 < bbox_4674[0] < bbox_4674[2] < -44)
        self.assertTrue(-21 < bbox_4674[1] < bbox_4674[3] < -19)
        # Relatório por fonte.
        dnit, der = rel['fontes']
        self.assertEqual(dnit['limpeza']['excluir'], 1)
        self.assertEqual(der['removidas_inteiras'], 1)
        self.assertGreater(der['metros_removidos'], 3900.0)
        self.assertEqual(rel['costura']['t'], 1)
        self.assertEqual(rel['feicoes'], 3)

    def test_falha_na_segunda_fonte_aborta_com_nome(self):
        erro = RuntimeError(f"{FONTE_DER['nome']}: Timeout 504")
        with self.assertRaises(RuntimeError) as ctx:
            self._baixar([_dnit(), erro])
        self.assertIn(FONTE_DER['nome'], str(ctx.exception))

    def test_erro_generico_ganha_nome_da_fonte(self):
        with self.assertRaises(RuntimeError) as ctx:
            self._baixar([_dnit(), ValueError('boom')])
        self.assertTrue(str(ctx.exception).startswith(FONTE_DER['nome'] + ':'))

    def test_ids_fontes_so_dnit(self):
        camada, rel, mock_baixar = self._baixar([_dnit()],
                                                ids_fontes=['dnit_snv'])
        self.assertEqual(mock_baixar.call_count, 1)
        self.assertEqual(mock_baixar.call_args[0][0]['id'], 'dnit_snv')
        self.assertEqual({f['fonte'] for f in camada.getFeatures()}, {'dnit_snv'})
        self.assertEqual([r['id'] for r in rel['fontes']], ['dnit_snv'])

    def test_sem_bbox_usa_extensao_da_uf(self):
        _, rel, mock_baixar = self._baixar([_dnit()], bbox=None, bbox_crs=None,
                                           ids_fontes=['dnit_snv'])
        self.assertEqual(mock_baixar.call_args[0][1],
                         gisbr_bridge.BBOX_UF['MG'])

    def test_fetch_road_network_delega(self):
        camada = MagicMock()
        with patch.object(gisbr_bridge, 'is_available', return_value=True), \
                patch('desire_lines.traffic.malha_gisbr.baixar_malha',
                      return_value=(camada, {})) as mock_malha:
            res = gisbr_bridge.fetch_road_network(
                bbox=(0, 0, 1, 1), crs='EPSG:4674', uf='MG')
        self.assertIs(res, camada)
        mock_malha.assert_called_once_with('MG', bbox=(0, 0, 1, 1),
                                           bbox_crs='EPSG:4674')


if __name__ == '__main__':
    unittest.main()
