# -*- coding: utf-8 -*-
"""
Common UI mixin for Desire Lines QGIS plugin.
"""
import os

from qgis.PyQt.QtWidgets import QApplication, QProgressBar
from qgis.core import Qgis, QgsProject, QgsVectorFileWriter
from qgis.utils import iface


class PluginUiMixin:
    """Mixin for common UI operations in Desire Lines dialogs.

    Subclasses must provide ``_output_path()``.
    """

    def _push_progress(self, text):
        """Show an indeterminate (pulsing) progress bar in the QGIS message bar."""
        mb = iface.messageBar()
        widget = mb.createMessage('Desire Lines', text)
        pbar = QProgressBar()
        pbar.setMinimum(0)
        pbar.setMaximum(0)
        pbar.setTextVisible(False)
        widget.layout().addWidget(pbar)
        mb.pushWidget(widget, Qgis.MessageLevel.Info)
        QApplication.processEvents()
        return widget

    @staticmethod
    def _zone_key(value):
        """Normalise a zone id so matrix and centroid ids compare equal.

        Ids are usually integers but may arrive as floats ("12.0") or strings
        depending on the provider; coerce to int when possible, else fall back
        to the stripped string.
        """
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return str(value).strip()

    def _write_layer_to_gpkg(self, layer, table):
        """Write a memory layer as a table into the output GeoPackage.

        Uses CreateOrOverwriteLayer so the new table is added alongside the
        existing ones (matrix, centroids, Desire_Lines) instead of replacing
        the whole file.
        """
        if not table:
            raise ValueError('table name is required')
        out_path = self._output_path()
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.layerName = table
        if os.path.exists(out_path):
            options.actionOnExistingFile = \
                QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, out_path, QgsProject.instance().transformContext(), options)
        add_table = out_path + '|layername={}'.format(table)
        return iface.addVectorLayer(add_table, table, 'ogr')

    def _push_message(self, text, level='warning'):
        """Push a translated message to the QGIS message bar.

        Also records it in ``self.last_message`` so the edge-case tests can
        assert *which* message the user would have seen without needing a live
        message bar. Levels: 'critical', 'warning', 'success'.
        """
        self.last_message = (level, text)
        mb = iface.messageBar() if iface is not None else None
        if mb is None:
            return
        if level == 'critical':
            mb.pushCritical('Desire Lines', text)
        elif level == 'success':
            mb.pushSuccess('Desire Lines', text)
        else:
            mb.pushWarning('Desire Lines', text)
