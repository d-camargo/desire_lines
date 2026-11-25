# coding=utf-8
"""Testes de `traffic/download_task.py` — `MalhaDownloadTask` (D1).

`run()` é chamado direto, sem gerenciador de tarefas, com `baixar_malha`
mockado.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from test.utilities import get_qgis_app

QGIS_APP = get_qgis_app()

from qgis.core import (
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)

from desire_lines.traffic import malha_gisbr
from desire_lines.traffic.download_task import MalhaDownloadTask

RELATORIO = {'uf': 'MG', 'fontes': [], 'costura': {}, 'feicoes': 2}


def _line_layer():
    layer = QgsVectorLayer('LineString?crs=EPSG:31983', 'malha', 'memory')
    feats = []
    for pts in ([(0, 0), (100, 0)], [(100, 0), (100, 100)]):
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolylineXY(
            [QgsPointXY(x, y) for x, y in pts]))
        feats.append(feat)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    return layer


class MalhaDownloadTaskTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out_path = os.path.join(self.tmp.name, 'out.gpkg')
        self.limite = QgsGeometry.fromWkt('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')
        self.ctx = QgsCoordinateTransformContext()
        self.task = MalhaDownloadTask(
            'download MG', 'MG', None, None, ['dnit_snv'], self.limite,
            self.ctx, self.out_path, 'malha_gisbr_mg')

    def test_run_writes_table_to_gpkg_and_returns_true(self):
        """Sucesso: grava a tabela no GPKG e guarda tabela/uri/relatorio, sem camada."""
        with patch('desire_lines.traffic.malha_gisbr.baixar_malha',
                   return_value=(_line_layer(), dict(RELATORIO))) as mock_baixar:
            self.assertTrue(self.task.run())

        args, kwargs = mock_baixar.call_args
        self.assertEqual(args, ('MG',))
        self.assertIsNone(kwargs['bbox'])
        self.assertIsNone(kwargs['bbox_crs'])
        self.assertEqual(kwargs['ids_fontes'], ['dnit_snv'])
        self.assertIs(kwargs['limite'], self.limite)
        self.assertIs(kwargs['transform_context'], self.ctx)

        self.assertEqual(self.task.tabela, 'malha_gisbr_mg')
        self.assertEqual(self.task.uri,
                         self.out_path + '|layername=malha_gisbr_mg')
        self.assertEqual(self.task.relatorio, RELATORIO)
        self.assertIsNone(self.task.erro)
        self.assertFalse(self.task.cancelado)
        written = QgsVectorLayer(self.task.uri, 'w', 'ogr')
        self.assertTrue(written.isValid())
        self.assertEqual(written.featureCount(), 2)
        # A task não guarda QgsVectorLayer para a thread principal (D1).
        self.assertFalse(any(isinstance(v, QgsVectorLayer)
                             for v in vars(self.task).values()))

    def test_feedback_forwards_progress_and_cancel_to_the_task(self):
        """O feedback adaptador repassa setProgress e isCanceled à task."""
        seen = {}

        def _baixar(uf, **kwargs):
            feedback = kwargs['feedback']
            feedback.setProgress(42)
            seen['progress'] = self.task.progress()
            seen['canceled_before'] = feedback.isCanceled()
            with patch.object(self.task, 'isCanceled', return_value=True):
                seen['canceled_after'] = feedback.isCanceled()
            return _line_layer(), dict(RELATORIO)

        with patch('desire_lines.traffic.malha_gisbr.baixar_malha',
                   side_effect=_baixar):
            self.assertTrue(self.task.run())
        self.assertAlmostEqual(seen['progress'], 42.0)
        self.assertFalse(seen['canceled_before'])
        self.assertTrue(seen['canceled_after'])

    def test_exception_fills_erro_and_returns_false(self):
        """Outra exceção vira `erro` e `False`, sem escapar do run()."""
        with patch('desire_lines.traffic.malha_gisbr.baixar_malha',
                   side_effect=RuntimeError('Malha DNIT: falhou')):
            self.assertFalse(self.task.run())
        self.assertEqual(self.task.erro, 'Malha DNIT: falhou')
        self.assertFalse(self.task.cancelado)
        self.assertIsNone(self.task.uri)
        self.assertFalse(os.path.exists(self.out_path))

    def test_download_cancelado_marks_cancelado(self):
        """`DownloadCancelado` marca `cancelado`, não `erro`, e devolve `False`."""
        with patch('desire_lines.traffic.malha_gisbr.baixar_malha',
                   side_effect=malha_gisbr.DownloadCancelado('cancelado')):
            self.assertFalse(self.task.run())
        self.assertTrue(self.task.cancelado)
        self.assertIsNone(self.task.erro)
        self.assertIsNone(self.task.uri)

    def test_finished_emits_concluida_with_the_task(self):
        """`finished(ok)` emite `concluida(self)`."""
        received = []
        self.task.concluida.connect(received.append)
        self.task.finished(False)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0], self.task)


if __name__ == '__main__':
    unittest.main()
