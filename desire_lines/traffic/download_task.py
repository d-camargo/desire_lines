# coding=utf-8
"""`MalhaDownloadTask`: baixa a malha rodoviária do GISBR em segundo plano (D1).

Mesmo molde do `OsmNetworkTask` do GISBR. Tudo que toca o projeto ou a UI
(UF, bbox/CRS, polígono do limite, contexto de transformação, caminho do
GPKG, ids das fontes) é resolvido pelo painel na thread principal e chega
aqui como valor. `run()` (thread de trabalho) chama `baixar_malha` e grava a
tabela no GPKG sem `QgsProject`/`iface`; não guarda nenhuma `QgsVectorLayer`.
Quem carrega a camada no projeto é o painel, ao receber `concluida`.
"""
from qgis.core import QgsProcessingFeedback, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from . import malha_gisbr
from ..ui_common import write_layer_to_gpkg_file


class _TaskFeedback(QgsProcessingFeedback):
    """Adapta a task à interface de feedback que `baixar_malha` espera.

    `setProgress` vira `task.setProgress` (barra do gerenciador de tarefas)
    e `isCanceled` repassa para `task.isCanceled` (o "×" do gerenciador).
    """

    def __init__(self, task):
        super().__init__()
        self._task = task

    def setProgress(self, pct):
        super().setProgress(pct)
        self._task.setProgress(pct)

    def isCanceled(self):
        return self._task.isCanceled()


class MalhaDownloadTask(QgsTask):
    """Roda `malha_gisbr.baixar_malha` + escrita no GPKG fora da thread principal.

    Resultado, para o painel ler no `concluida`:
    `tabela`, `uri` e `relatorio` (sucesso); `erro` (str) em falha;
    `cancelado` (bool) quando o usuário cancelou.
    """

    concluida = pyqtSignal(object)

    def __init__(self, descricao, uf, bbox, bbox_crs, ids_fontes, limite,
                 transform_context, out_path, tabela):
        super().__init__(descricao, QgsTask.Flag.CanCancel)
        self.uf = uf
        self.bbox = bbox
        self.bbox_crs = bbox_crs
        self.ids_fontes = ids_fontes
        self.limite = limite
        self.transform_context = transform_context
        self.out_path = out_path
        self.tabela = tabela
        self.uri = None
        self.relatorio = None
        self.erro = None
        self.cancelado = False

    def run(self):
        try:
            if self.isCanceled():
                raise malha_gisbr.DownloadCancelado('cancelado antes de começar')
            layer, relatorio = malha_gisbr.baixar_malha(
                self.uf, bbox=self.bbox, bbox_crs=self.bbox_crs,
                ids_fontes=self.ids_fontes, feedback=_TaskFeedback(self),
                limite=self.limite, transform_context=self.transform_context)
            if self.isCanceled():
                raise malha_gisbr.DownloadCancelado('cancelado antes de gravar')
            self.uri = write_layer_to_gpkg_file(
                layer, self.out_path, self.tabela, self.transform_context)
            self.relatorio = relatorio
            return True
        except malha_gisbr.DownloadCancelado:
            self.cancelado = True
            return False
        except Exception as err:
            self.erro = str(err) or type(err).__name__
            return False

    def finished(self, ok):
        # Thread principal. Cancelada ainda na fila, `run()` nem rodou.
        if not ok and self.erro is None and self.isCanceled():
            self.cancelado = True
        self.concluida.emit(self)
