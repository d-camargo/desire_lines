# -*- coding: utf-8 -*-
"""
Common UI mixin for Desire Lines QGIS plugin.
"""
import os

from qgis.PyQt.QtWidgets import QApplication, QProgressBar
from qgis.core import (
    Qgis,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsVectorFileWriter,
)
from qgis.utils import iface


def write_layer_to_gpkg_file(layer, path, table, transform_context=None):
    """Write a vector layer into a GeoPackage file as a table.

    Uses CreateOrOverwriteLayer so the new table is added alongside the
    existing ones (matrix, centroids, Desire_Lines) instead of replacing
    the whole file.

    Does not touch project or GUI objects (thread-safe for worker tasks).

    :param layer: QgsVectorLayer to write.
    :param path: Destination GeoPackage file path.
    :param table: Table name in the GeoPackage.
    :param transform_context: QgsCoordinateTransformContext (optional).
    :return: Layer URI formatted as ``"<path>|layername=<table_name>"``.
    :raises ValueError: If ``table`` is empty.
    :raises RuntimeError: If the writer fails.
    """
    if not table:
        raise ValueError('table name is required')
    if transform_context is None:
        transform_context = QgsCoordinateTransformContext()

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = 'GPKG'
    options.layerName = table
    if os.path.exists(path):
        options.actionOnExistingFile = (
            QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
        )

    res = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, transform_context, options
    )
    if isinstance(res, tuple) and len(res) >= 2:
        err_code, err_msg = res[0], res[1]
    else:
        err_code, err_msg = res, ''

    if err_code != QgsVectorFileWriter.WriterError.NoError:
        raise RuntimeError(
            f"Failed to write layer to GPKG '{path}' (table '{table}'): {err_msg}"
        )

    return f"{path}|layername={table}"


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
        out_path = self._output_path()
        uri = write_layer_to_gpkg_file(
            layer, out_path, table, QgsProject.instance().transformContext()
        )
        if iface is not None:
            return iface.addVectorLayer(uri, table, 'ogr')
        return None

    def _push_message(self, text, level='warning'):
        """Push a translated message to the QGIS message bar.

        Also records it in ``self.last_message`` so the edge-case tests can
        assert *which* message the user would have seen without needing a live
        message bar. Levels: 'critical', 'warning', 'success', 'info'.
        """
        self.last_message = (level, text)
        mb = iface.messageBar() if iface is not None else None
        if mb is None:
            return
        if level == 'critical':
            mb.pushCritical('Desire Lines', text)
        elif level == 'success':
            mb.pushSuccess('Desire Lines', text)
        elif level == 'info':
            mb.pushInfo('Desire Lines', text)
        else:
            mb.pushWarning('Desire Lines', text)
