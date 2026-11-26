import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateTransform,
    QgsFieldProxyModel,
    QgsMapLayerProxyModel,
    QgsMessageLog,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
)
from qgis.gui import QgsFieldComboBox, QgsFileWidget, QgsDockWidget
from qgis.utils import iface

try:
    from . import aon, ui_common
    from .traffic import (
        params,
        network,
        graph,
        outputs,
        assignment,
        gisbr_bridge,
        download_task,
        counts,
        calibration,
    )
except ImportError:
    import aon, ui_common
    from traffic import (
        params,
        network,
        graph,
        outputs,
        assignment,
        gisbr_bridge,
        download_task,
        counts,
        calibration,
    )

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'traffic_panel_base.ui'))

class TrafficAssignmentPanel(ui_common.PluginUiMixin, QgsDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # D1: running download task; kept so Python does not collect it, and
        # the download button stays disabled while it exists.
        self._download_task = None

        self._build_traffic_params_ui()
        # QGIS 4/Qt6 can emit layerChanged before currentLayer() reflects the
        # new layer (or not at all when the model auto-selects it): the same
        # handlers are also bound to currentIndexChanged, which always fires
        # with the combo already settled. Handlers are idempotent setLayer
        # calls, so the double firing on Qt5 is harmless.
        self.taNetworkCombo.layerChanged.connect(self._traffic_network_changed)
        self.taNetworkCombo.currentIndexChanged.connect(self._traffic_network_changed)
        self.taMatrixCombo.layerChanged.connect(self._traffic_matrix_changed)
        self.taMatrixCombo.currentIndexChanged.connect(self._traffic_matrix_changed)
        self.taCentroidsCombo.layerChanged.connect(self._traffic_centroids_changed)
        self.taCentroidsCombo.currentIndexChanged.connect(self._traffic_centroids_changed)
        self.taCountsCombo.layerChanged.connect(self._traffic_counts_changed)
        self.taCountsCombo.currentIndexChanged.connect(self._traffic_counts_changed)
        self.taRunCapacity.clicked.connect(self.run_capacity)
        self.taRunAssign.clicked.connect(self.run_assignment)
        self.taRunCalibration.clicked.connect(self.run_calibration)
        self.taDownloadNetwork.clicked.connect(self.run_download)
        for radio in (self.taNetFromLayer, self.taNetFromGisbr):
            radio.toggled.connect(self._update_traffic_tab_state)
        self.taUf.textChanged.connect(self._reload_sources)
        self.taUf.textChanged.connect(self._reload_recortes)
        self.taUf.textChanged.connect(self._update_traffic_tab_state)
        self.taSources.itemChanged.connect(self._update_traffic_tab_state)
        self.taRecorteTipo.currentIndexChanged.connect(self._reload_recortes)
        self.taRecorteTipo.currentIndexChanged.connect(self._update_traffic_tab_state)
        self.taRecorte.currentIndexChanged.connect(self._update_traffic_tab_state)
        self.taMethod.currentIndexChanged.connect(self._update_traffic_tab_state)
        for combo in (self.taNetworkCombo, self.taMatrixCombo,
                      self.taCentroidsCombo, self.taCountsCombo,
                      self.taCalibAssignCombo):
            combo.layerChanged.connect(self._update_traffic_tab_state)
            combo.currentIndexChanged.connect(self._update_traffic_tab_state)
        for combo in (self.taOriginField, self.taDestField, self.taValueField,
                      self.taZoneIdField, self.taCountField):
            combo.fieldChanged.connect(self._update_traffic_tab_state)
        
        for text, data in (
            (self.tr('Centroid extent (+ radius)'), 'centroides'),
            (self.tr('Whole state'), 'uf'),
            (self.tr('Metropolitan area'), 'rm'),
            (self.tr('Micro-region'), 'micro'),
            (self.tr('Meso-region'), 'meso'),
            (self.tr('Health macro-region'), 'macsaud'),
        ):
            self.taRecorteTipo.addItem(text, data)

        self.taMatrixCombo.setFilters(QgsMapLayerProxyModel.NoGeometry)
        self.taCentroidsCombo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.taCentroidsCombo.setShowCrs(True)
        self.taNetworkCombo.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.taCountsCombo.setFilters(
            QgsMapLayerProxyModel.Filter.PointLayer
            if hasattr(QgsMapLayerProxyModel, 'Filter')
            else QgsMapLayerProxyModel.PointLayer
        )
        self.taCalibAssignCombo.setFilters(
            QgsMapLayerProxyModel.Filter.LineLayer
            if hasattr(QgsMapLayerProxyModel, 'Filter')
            else QgsMapLayerProxyModel.LineLayer
        )
        
        self.taOriginField.setFilters(QgsFieldProxyModel.Int)
        self.taDestField.setFilters(QgsFieldProxyModel.Int)
        self.taZoneIdField.setFilters(QgsFieldProxyModel.Int)
        self.taValueField.setFilters(QgsFieldProxyModel.Double)
        self.taCountField.setFilters(
            QgsFieldProxyModel.Filter.Numeric
            if hasattr(QgsFieldProxyModel, 'Filter')
            else QgsFieldProxyModel.Numeric
        )
        self.taPostIdField.setAllowEmptyFieldName(True)

        self.taOutputFile.setStorageMode(QgsFileWidget.SaveFile)
        self.taOutputFile.setFilter('GeoPackage (*.gpkg)')

        self._traffic_network_changed()
        self._traffic_matrix_changed()
        self._traffic_centroids_changed()
        self._traffic_counts_changed()
        self._update_traffic_tab_state()

    def _output_path(self):
        """Return the user-chosen output GPKG path, or a sensible fallback."""
        path = (self.taOutputFile.filePath() or '').strip()
        path = path.split('|', 1)[0].strip()
        if path:
            if not path.lower().endswith('.gpkg'):
                path = path + '.gpkg'
            return os.path.abspath(path)
        return os.path.join(os.path.expanduser('~'), 'output.gpkg')

    # taMethod combo order must match: index 0 = AoN, index 1 = MSA, index 2 = FW (D5, D10).
    TRAFFIC_METHODS = ('aon', 'msa', 'fw')

    def _build_traffic_params_ui(self):
        """Fill taParamsGroup with one row per parameter of the D7 catalogue.

        Built from ``params.PARAMS`` instead of hand-written in the .ui: the
        catalogue is the single source of truth, so a parameter added there
        cannot silently miss its override widgets. Each row gives the user both
        ways out of D7(c): a global value and an optional field of the highway
        layer that wins over it.
        """
        grid = self.taParamsGrid
        self._traffic_param_widgets = {}
        for row, (key, spec) in enumerate(params.PARAMS.items()):
            label = QtWidgets.QLabel(
                '{} ({})'.format(spec['rotulo'], spec['unidade'])
                if spec['unidade'] else spec['rotulo'])
            if spec['tipo'] is bool:
                editor = QtWidgets.QComboBox()
                editor.addItems([self.tr('no'), self.tr('yes')])
                editor.setCurrentIndex(1 if spec['default'] else 0)
            elif spec['tipo'] is int:
                editor = QtWidgets.QSpinBox()
                editor.setRange(0, 99)
                editor.setValue(int(spec['default']))
            elif spec['tipo'] is float:
                editor = QtWidgets.QDoubleSpinBox()
                editor.setDecimals(2)
                editor.setRange(0.0, 100000.0)
                editor.setValue(float(spec['default']))
            else:
                editor = QtWidgets.QLineEdit(str(spec['default']))
            field_combo = QgsFieldComboBox()
            field_combo.setAllowEmptyFieldName(True)
            grid.addWidget(label, row, 0)
            grid.addWidget(editor, row, 1)
            grid.addWidget(QtWidgets.QLabel(self.tr('field:')), row, 2)
            grid.addWidget(field_combo, row, 3)
            self._traffic_param_widgets[key] = (editor, field_combo)

    def _traffic_overrides(self):
        """Read the parameter rows into the ``overrides`` dict of ``params.resolve``.

        A parameter mapped to a layer field is left out of the overrides so the
        official value read from the feature wins (D7 b/c); only the globally
        typed values are returned, tagged 'usuario' by ``params.resolve``.
        """
        overrides = {}
        for key, (editor, field_combo) in getattr(
                self, '_traffic_param_widgets', {}).items():
            if field_combo.currentField():
                continue
            spec = params.PARAMS[key]
            if spec['tipo'] is bool:
                overrides[key] = bool(editor.currentIndex())
            elif isinstance(editor, QtWidgets.QLineEdit):
                overrides[key] = editor.text().strip()
            else:
                overrides[key] = editor.value()
        return overrides

    def _traffic_field_map(self):
        """Read the mapped field combos into the ``field_map`` of ``params.resolve`` (D2).

        Only parameters with a field picked are returned, as
        ``{param_id: field_name}``.
        """
        return {
            key: field_combo.currentField()
            for key, (_editor, field_combo) in getattr(
                self, '_traffic_param_widgets', {}).items()
            if field_combo.currentField()
        }

    def _traffic_method(self):
        """Return the selected assignment method id ('aon', 'msa' or 'fw')."""
        return self.TRAFFIC_METHODS[self.taMethod.currentIndex()]

    def _traffic_network_changed(self):
        """Point the highway-layer field combos at the selected network layer."""
        layer = self.taNetworkCombo.currentLayer()
        self.taIdField.setLayer(layer)
        for _editor, field_combo in getattr(
                self, '_traffic_param_widgets', {}).values():
            field_combo.setLayer(layer)

    def _traffic_matrix_changed(self):
        """Point the OD field combos at the selected matrix layer."""
        layer = self.taMatrixCombo.currentLayer()
        for combo in (self.taOriginField, self.taDestField, self.taValueField):
            combo.setLayer(layer)

    def _traffic_centroids_changed(self):
        """Point the traffic-id field combo at the selected centroids layer."""
        self.taZoneIdField.setLayer(self.taCentroidsCombo.currentLayer())

    def _traffic_counts_changed(self):
        """Point the count-post field combos at the selected counts layer."""
        layer = self.taCountsCombo.currentLayer()
        self.taCountField.setLayer(layer)
        self.taPostIdField.setLayer(layer)

    def _reload_recortes(self):
        """Populate the region combo from GisBR when a regional type is chosen (D5)."""
        self.taRecorte.clear()
        tipo = self.taRecorteTipo.currentData()
        uf = self.taUf.text().strip()
        if tipo in gisbr_bridge.TIPOS_RECORTE and len(uf) == 2:
            for item_id, nome in gisbr_bridge.listar_recortes(tipo, uf):
                self.taRecorte.addItem(nome, item_id)

    def _reload_sources(self):
        """Populate the source list for the current UF, all checked (D2).

        The source id goes in ``Qt.ItemDataRole.UserRole`` so the checked
        ids can be passed to ``malha_gisbr.baixar_malha`` as ``ids_fontes``.
        """
        uf = self.taUf.text().strip().upper()
        self.taSources.blockSignals(True)
        self.taSources.clear()
        if len(uf) == 2:
            for fonte in gisbr_bridge.fontes_rodoviarias(uf):
                item = QtWidgets.QListWidgetItem(
                    fonte.get('nome') or fonte.get('id'))
                item.setData(Qt.ItemDataRole.UserRole, fonte.get('id'))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.taSources.addItem(item)
        self.taSources.blockSignals(False)

    def _checked_source_ids(self):
        """Ids of the sources checked in taSources, in list order (D2)."""
        ids = []
        for row in range(self.taSources.count()):
            item = self.taSources.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def _update_traffic_tab_state(self):
        """Enable/disable the highway tab and its buttons (steps 17, D1, D6).

        GisBR is needed only to download the network: capacity and
        assignment always run on the selected layer (D1). The warning label
        stays visible while GisBR is missing so the reason is never hidden
        in a tooltip. Iterations and gap tolerance only apply to
        equilibrium methods (MSA and FW), so AoN greys them out (D5, D10).
        The source list follows the UF widgets; the download button further
        needs a resolved UF, recorte and at least one checked source (D2).
        """
        available = gisbr_bridge.is_available()
        self.taGisbrWarning.setVisible(not available)
        self.taGisbrWarning.setText(gisbr_bridge.missing_message())
        self.taNetFromGisbr.setEnabled(available)
        if not available and self.taNetFromGisbr.isChecked():
            self.taNetFromLayer.setChecked(True)

        from_gisbr = self.taNetFromGisbr.isChecked()
        for widget in (self.taNetworkCombo, self.taIdField, self.taLabelNetwork,
                       self.taLabelIdField):
            widget.setEnabled(not from_gisbr)
        for widget in (self.taUf, self.taLabelUf, self.taRecorteTipo,
                       self.taLabelRecorteTipo, self.taLabelSources,
                       self.taSources):
            widget.setEnabled(from_gisbr)

        is_regional = self.taRecorteTipo.currentData() in gisbr_bridge.TIPOS_RECORTE
        for widget in (self.taRecorte, self.taLabelRecorte):
            widget.setEnabled(from_gisbr and is_regional)

        is_equilibrium = self._traffic_method() in ('msa', 'fw')
        for widget in (self.taMaxIter, self.taGapTol,
                       self.taLabelMaxIter, self.taLabelGapTol):
            widget.setEnabled(is_equilibrium)

        uf_ok = len(self.taUf.text().strip()) == 2
        regional_ok = (not is_regional) or bool(self.taRecorte.currentData())
        self.taDownloadNetwork.setEnabled(
            from_gisbr and available and uf_ok and regional_ok
            and bool(self._checked_source_ids())
            and self._download_task is None)

        # D1: the runs work on the selected layer only — no layer, no run.
        network_ready = bool(self.taNetworkCombo.currentLayer())
        self.taRunCapacity.setEnabled(network_ready)
        self.taRunAssign.setEnabled(network_ready and bool(
            self.taMatrixCombo.currentLayer()
            and self.taCentroidsCombo.currentLayer()
            and self.taOriginField.currentField()
            and self.taDestField.currentField()
            and self.taValueField.currentField()
            and self.taZoneIdField.currentField()
        ))
        self.taRunCalibration.setEnabled(bool(
            self.taCalibAssignCombo.currentLayer()
            and self.taCountsCombo.currentLayer()
            and self.taCountField.currentField()
        ))

    def _traffic_centroid_points(self, layer, zone_id_field):
        """Read centroids as (zone key, (x, y)) pairs in the layer's own CRS."""
        points, zone_keys = [], []
        for feat in layer.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            key = self._zone_key(feat[zone_id_field]) if zone_id_field else len(points)
            if key is None or key in zone_keys:
                continue
            pt = geom.centroid().asPoint()
            zone_keys.append(key)
            points.append((pt.x(), pt.y()))
        return points, zone_keys

    @staticmethod
    def _format_zone_ids(zone_ids, max_items=10):
        """Format a list of zone identifiers, truncating with '…' after max_items."""
        items = [str(z) for z in zone_ids]
        if len(items) > max_items:
            return ', '.join(items[:max_items]) + ', …'
        return ', '.join(items)

    def build_traffic_network(
        self,
        road_layer=None,
        centroids=None,
        zone_keys=None,
        overrides=None,
        max_dist_m=5000.0,
        id_field=None,
        precision=3,
        fetch_gisbr=False,
        bbox=None,
        crs=None,
        uf=None,
        centroids_crs=None,
        clip_buffer_m=None,
        field_map=None,
    ):
        """Turn a highway layer into directed arcs plus a routable graph (steps 18-19).

        Reports every edge case as a translated message instead of raising:
        GisBR download failure, empty network after clipping, non-positive
        capacity and centroids that reach no highway link or node within ``max_dist_m``.

        Centroids within reach are anchored by orthogonal projection onto the
        nearest highway link (or at a link end / nearest node when ambiguous or
        near ends). Links with interior anchors are split so trips enter and
        leave the mesh at the projection point.

        Connector arcs link each centroid from its virtual zone node
        ``(CONNECTOR_LINK_ID, zone_id)`` to its anchor on the highway network.
        The coordinate of each anchor is stored in ``self.traffic_anchors``
        (mapping zone id -> ``(x, y)``).

        A layer with a ``crs()`` is first moved to a metric working CRS (D1):
        ``aon.pick_metric_crs`` keeps a projected CRS as is, and turns a
        geographic one into its UTM zone (or SIRGAS 2000 / Brazil Albers). All
        snap, length, connector and clipping tolerances are in metres, so in
        degrees they would glue links to the wrong nodes. Centroids and the
        clipping box are brought to that same CRS (D4), and
        ``self.traffic_crs`` is set to it so the output is labelled right.
        Inputs without ``crs()`` (lists of dicts in the tests) are used as is.

        Args:
            road_layer: QgsVectorLayer, iterable of QgsFeature, or list of
                dicts with a 'geometry' key (used by the tests). None with
                ``fetch_gisbr`` asks GisBR for the official network.
            centroids (list | None): Zone centroids as (x, y) tuples, in
                ``centroids_crs``.
            zone_keys (list | None): Zone ids parallel to ``centroids``. When
                None, the list index is the zone id.
            overrides (dict | None): Global parameter overrides (D7).
            max_dist_m (float): Longest accepted centroid connector, in metres.
            id_field (str | None): Link id field of the highway layer.
            precision (int): Decimal places of the node snap.
            fetch_gisbr (bool): Download the network via GisBR instead.
            bbox, crs, uf: Passed through to ``gisbr_bridge.fetch_road_network``.
                Without ``clip_buffer_m``, ``bbox`` (in the CRS the network
                came in) is also the clipping box, transformed to the working
                CRS.
            centroids_crs: CRS of ``centroids``. None means the CRS the network
                came in.
            clip_buffer_m (float | None): When given with centroids, clip the
                network to the centroids' bounding box (in the working CRS)
                expanded by this many metres, instead of ``bbox``.
            field_map (dict | None): Parameter -> highway-layer field mapped in
                the panel (D2), read by ``params.resolve`` before the candidates.

        Returns:
            tuple: ``(graph, arcs, zone_node, unconnected)``. ``graph`` is None
                and ``arcs`` empty when the network could not be built at all;
                ``zone_node`` maps zone id -> virtual graph node and
                ``unconnected`` lists the zone ids left out.
        """
        self.traffic_anchors = {}
        if fetch_gisbr or (road_layer is None and (bbox or uf)):
            try:
                road_layer = gisbr_bridge.fetch_road_network(
                    bbox=bbox, crs=crs, uf=uf)
            except Exception as err:
                self._push_message(
                    self.tr('Could not fetch the highway network from GisBR: {}')
                    .format(err), level='critical')
                return None, [], {}, []

        # D1: CRS of the mesh the arcs actually came from — with the GisBR path
        # the caller cannot know it in advance — and the metric CRS everything
        # is computed (and the output labelled) in.
        crs_getter = getattr(road_layer, 'crs', None)
        src_crs = crs_getter() if callable(crs_getter) else None
        work_crs = src_crs

        def _check_crs_mismatch(layer_name, crs_obj, extent_box):
            mismatch = network.coords_crs_mismatch(extent_box, crs_obj.isGeographic())
            if mismatch == 'degrees_in_projected':
                self._push_message(
                    self.tr('The {} layer is labelled {} (projected, metres) but its '
                            'coordinates look like degrees. Set the layer CRS to the '
                            'geographic one (e.g. EPSG:4326 or EPSG:4674) and run again.')
                    .format(layer_name, crs_obj.authid() or crs_obj.description()),
                    level='critical')
                return True
            if mismatch == 'out_of_geographic_range':
                self._push_message(
                    self.tr('The {} layer is labelled {} (geographic, degrees) but its '
                            'coordinates are out of the longitude/latitude range. Set the '
                            'layer CRS to the projected one the coordinates are in and run again.')
                    .format(layer_name, crs_obj.authid() or crs_obj.description()),
                    level='critical')
                return True
            return False

        # D8: Guarda de rótulo de CRS × coordenadas (antes do pick_metric_crs)
        if (src_crs is not None and src_crs.isValid()
                and hasattr(road_layer, 'extent')):
            ext = road_layer.extent()
            if not (hasattr(ext, 'isNull') and ext.isNull()):
                ext_box = (ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum())
                if _check_crs_mismatch(self.tr('highway network'), src_crs, ext_box):
                    return None, [], {}, []

        cent_crs = centroids_crs if centroids_crs is not None else src_crs
        centroids = list(centroids or [])
        if centroids and cent_crs is not None and cent_crs.isValid():
            c_pts = [
                (p.x(), p.y()) if hasattr(p, 'x') and callable(p.x) else (p[0], p[1])
                for p in centroids
            ]
            if c_pts:
                xs = [pt[0] for pt in c_pts]
                ys = [pt[1] for pt in c_pts]
                c_ext = (min(xs), min(ys), max(xs), max(ys))
                if _check_crs_mismatch(self.tr('centroids'), cent_crs, c_ext):
                    return None, [], {}, []

        if (src_crs is not None and src_crs.isValid()
                and hasattr(road_layer, 'extent')):
            ext = road_layer.extent()
            picked, _reason = aon.pick_metric_crs(src_crs, (
                ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()))
            if picked is not None and picked != src_crs:
                try:
                    road_layer = network.reproject_layer(road_layer, picked)
                except Exception as err:
                    self._push_message(
                        self.tr('Could not reproject the highway network to a '
                                'metric CRS: {}').format(err), level='critical')
                    return None, [], {}, []
                work_crs = picked
                self._push_message(
                    self.tr('Highway network reprojected from {} to {} for '
                            'metric computations.').format(
                                src_crs.authid(), work_crs.authid()),
                    level='info')
        self.traffic_crs = work_crs if src_crs is not None else crs

        # D4: centroids in the working CRS, so connectors are measured in metres.
        centroids = list(centroids or [])
        cent_crs = centroids_crs if centroids_crs is not None else src_crs
        if (centroids and work_crs is not None and cent_crs is not None
                and cent_crs != work_crs):
            xform = QgsCoordinateTransform(cent_crs, work_crs, QgsProject.instance())
            centroids = [(p.x(), p.y()) for p in (
                xform.transform(QgsPointXY(x, y)) for x, y in centroids)]

        # D4: clip to the study area before building the graph. A failure here
        # is not fatal — it only means the graph is bigger (and slower) than it
        # had to be, so warn and carry on with the full mesh.
        if hasattr(road_layer, 'getFeatures') and (
                bbox is not None or (clip_buffer_m is not None and centroids)):
            try:
                if clip_buffer_m is not None and centroids:
                    clip_bbox = self._traffic_bbox(centroids, clip_buffer_m)
                elif work_crs is not None and work_crs != src_crs:
                    rect = QgsCoordinateTransform(
                        src_crs, work_crs, QgsProject.instance()
                    ).transformBoundingBox(QgsRectangle(*bbox))
                    clip_bbox = (rect.xMinimum(), rect.yMinimum(),
                                 rect.xMaximum(), rect.yMaximum())
                else:
                    clip_bbox = bbox
                road_layer = network.clip_and_clean(road_layer, clip_bbox)
            except Exception as err:
                self._push_message(
                    self.tr('Could not clip the network to the study area ({}); '
                            'using the full mesh.').format(err))

        if road_layer is None:
            features = []
        elif hasattr(road_layer, 'getFeatures'):
            features = list(road_layer.getFeatures())
        else:
            features = list(road_layer)

        arcs = network.build_network(
            features, overrides=overrides, precision=precision,
            id_field=id_field, field_map=field_map) if features else []

        if not arcs:
            self._push_message(
                self.tr('The highway network is empty after clipping.'),
                level='critical')
            return None, [], {}, []

        # Capacity comes from the HCM procedure, so a non-positive value means
        # the inputs of that arc are unusable. Drop those arcs and say how
        # many: keeping them would divide by zero in v/c and report LOS F on
        # what is really missing data.
        usable = [a for a in arcs if a.capacity > 0.0]
        if len(usable) != len(arcs):
            self._push_message(
                self.tr('{} of {} arcs dropped for null or invalid capacity.')
                .format(len(arcs) - len(usable), len(arcs)))
            arcs = usable
        if not arcs:
            self._push_message(
                self.tr('No arc has a valid capacity; check the HCM parameters.'),
                level='critical')
            return None, [], {}, []

        if not centroids:
            return graph.build_graph(arcs), arcs, {}, []

        keys = list(zone_keys) if zone_keys else list(range(len(centroids)))
        net_arcs, connectors, node_by_index, anchor_report = (
            network.anchor_centroids(arcs, centroids, max_dist_m=max_dist_m))
        all_arcs = net_arcs + connectors
        zone_node = {keys[i]: node for i, node in node_by_index.items()}
        unconnected = [keys[i] for i, _dist in anchor_report['unconnected']]
        self.traffic_anchors = {
            keys[i]: anchor_xy for i, anchor_xy in anchor_report['anchors'].items()}

        if unconnected and not zone_node:
            self._push_message(
                self.tr('No centroid could be connected to the highway network '
                        '(nearest node farther than {:.0f} m).').format(max_dist_m),
                level='critical')
        elif unconnected:
            self._push_message(
                self.tr('{} centroid(s) not connected to the highway network '
                        '(nothing within {:.0f} m): zones {}.').format(
                            len(unconnected), max_dist_m,
                            self._format_zone_ids(unconnected)))

        if anchor_report['far']:
            far_keys = [keys[i] for i, _d in anchor_report['far']]
            self._push_message(
                self.tr('{} connector(s) longer than {:.0f} m: zones {}. '
                        'Check the centroids or the network clip.').format(
                            len(anchor_report['far']), network.CONNECTOR_WARN_M,
                            self._format_zone_ids(far_keys)))

        for group in anchor_report['shared_node'][:5]:
            group_keys = [keys[i] for i in group]
            self._push_message(
                self.tr('Zones {} are anchored to the same network node; '
                        'trips between them use only the connectors.').format(
                            self._format_zone_ids(group_keys)))

        for link_id in sorted(anchor_report['shared_link'], key=str):
            link_keys = [keys[i] for i in anchor_report['shared_link'][link_id]]
            self._push_message(
                self.tr('Zones {} are anchored to the same highway link ({}).').format(
                    self._format_zone_ids(link_keys), link_id),
                level='info')

        if anchor_report['fallback']:
            fallback_keys = [keys[i] for i in anchor_report['fallback']]
            self._push_message(
                self.tr('{} centroid(s) anchored to the nearest node because '
                        'the nearest link was ambiguous: zones {}.').format(
                            len(anchor_report['fallback']),
                            self._format_zone_ids(fallback_keys)))

        return graph.build_graph(all_arcs), all_arcs, zone_node, unconnected

    def read_od_pairs(self, od_matrix, zone_node,
                      origin_field=None, dest_field=None, value_field=None):
        """Read the OD matrix into ``(origin node, dest node, demand)`` triples.

        Rows whose zone ids have no connected centroid, or whose demand is not
        a number, are counted as unmatched instead of aborting the run.

        Returns:
            tuple: ``(od_pairs, unmatched)``.
        """
        if od_matrix is None:
            return [], 0
        rows = (od_matrix.getFeatures() if hasattr(od_matrix, 'getFeatures')
                else od_matrix)

        od_pairs, unmatched = [], 0
        for row in rows:
            o_node = zone_node.get(self._zone_key(row[origin_field]))
            d_node = zone_node.get(self._zone_key(row[dest_field]))
            if o_node is None or d_node is None:
                unmatched += 1
                continue
            try:
                demand = float(row[value_field])
            except (TypeError, ValueError):
                unmatched += 1
                continue
            od_pairs.append((o_node, d_node, demand))
        return od_pairs, unmatched

    def _traffic_bbox(self, centroids, buffer_m):
        """Bounding box of the centroids expanded by ``buffer_m`` (D4 clipping)."""
        if not centroids:
            return None
        xs = [p[0] for p in centroids]
        ys = [p[1] for p in centroids]
        return (min(xs) - buffer_m, min(ys) - buffer_m,
                max(xs) + buffer_m, max(ys) + buffer_m)

    def _gisbr_bbox(self, centroids, max_dist_m, centroids_crs=None):
        """Decide the download bounding box and its CRS per taRecorteTipo (D5, D7).

        Returns:
            tuple: ``(bbox, crs)`` — ``(None, None)`` for 'uf' (state
            extent); the centroids' box in ``centroids_crs`` for
            'centroides'; the region extent in EPSG:4674 for regional
            recortes.
        """
        tipo = self.taRecorteTipo.currentData()
        if tipo == 'uf':
            return None, None
        if tipo == 'centroides':
            return self._traffic_bbox(centroids, max_dist_m), centroids_crs
        return gisbr_bridge.extensao_recorte(
            tipo, self.taRecorte.currentData()), 'EPSG:4674'

    def _publish_traffic_layer(self, arcs, flows, stats, crs, table):
        """Write the arcs+flows layer to the output GeoPackage and style it by v/c."""
        mem = outputs.flows_to_layer(
            arcs, flows, stats=stats, crs=crs, layer_name=table)
        out_layer = self._write_layer_to_gpkg(mem, table or mem.name())
        if out_layer:
            outputs.apply_vc_style(out_layer)
        return out_layer

    def _provenance_note(self, arcs):
        """Translated 'official/default/user' summary plus the urban-arc warning."""
        summary = outputs.provenance_summary(arcs)
        note = self.tr(
            'parameters: {} official, {} default, {} set by the user').format(
                summary['oficial'], summary['padrao'], summary['usuario'])
        urban = outputs.urban_arc_count(arcs)
        if urban:
            note += '; ' + self.tr(
                '{} urban arc(s): HCM highway capacity does not apply to urban '
                'crossings — read those with care').format(urban)
        return note

    def run_download(self):
        """Download the official highway mesh via GisBR in a QgsTask (D1, D2).

        Everything that touches the project or the UI is resolved here, on
        the main thread: boundary polygon (D2) — or the bbox/CRS when there
        is none (centroid mode) —, transform context, output path and source
        ids. The download and the GPKG write run in
        ``download_task.MalhaDownloadTask``; progress and cancel are the QGIS
        task manager's. ``_on_download_concluido`` publishes the result.
        """
        uf = self.taUf.text().strip().upper()
        tipo = self.taRecorteTipo.currentData()
        centroids, centroids_crs = None, None
        cent_layer = self.taCentroidsCombo.currentLayer()
        if tipo == 'centroides' and cent_layer is not None:
            centroids, _keys = self._traffic_centroid_points(
                cent_layer, self.taZoneIdField.currentField())
            centroids_crs = cent_layer.crs()

        # D2: com limite (UF ou recorte regional) o bbox do pedido sai do
        # próprio limite em `baixar_malha`; a extensão regional não é
        # resolvida (nem baixada) uma segunda vez só para ser ignorada.
        try:
            if tipo == 'uf':
                limite = gisbr_bridge.limite_uf(uf)
            elif tipo in gisbr_bridge.TIPOS_RECORTE:
                limite = gisbr_bridge.limite_recorte(
                    tipo, self.taRecorte.currentData())
            else:
                limite = None
        except Exception as err:
            self._push_message(
                self.tr('Could not obtain the boundary of the area: {}')
                .format(err), level='critical')
            return

        if limite is not None:
            bbox, bbox_crs = None, None
        else:
            try:
                bbox, bbox_crs = self._gisbr_bbox(
                    centroids, self.taMaxDist.value(), centroids_crs)
            except RuntimeError as err:
                self._push_message(
                    self.tr('Could not obtain region extent: {}').format(err),
                    level='critical')
                return

        task = download_task.MalhaDownloadTask(
            self.tr('Desire Lines — downloading the highway network ({})')
            .format(uf),
            uf, bbox, bbox_crs, self._checked_source_ids(), limite,
            QgsProject.instance().transformContext(), self._output_path(),
            'malha_gisbr_{}'.format(uf.lower()))
        task.concluida.connect(self._on_download_concluido)
        self._download_task = task
        self._update_traffic_tab_state()
        QgsApplication.taskManager().addTask(task)
        self._push_message(
            self.tr('Downloading the highway network in the background…'),
            level='info')

    def _on_download_concluido(self, task):
        """Publish the finished download task on the main thread (D1).

        Success: load ``malha_gisbr_<uf>`` from the GPKG, select it in
        ``taNetworkCombo``, mark ``taNetFromLayer`` and report. Error is a
        critical message with its text; cancel is an info, nothing published.
        """
        self._download_task = None
        self._update_traffic_tab_state()
        if task.cancelado:
            self._push_message(self.tr('Download cancelled'), level='info')
            return
        if task.erro is not None or not task.uri:
            self._push_message(
                self.tr('Could not download the highway network: {}')
                .format(task.erro), level='critical')
            return

        out_layer = (iface.addVectorLayer(task.uri, task.tabela, 'ogr')
                     if iface is not None else None)
        if out_layer is None:
            self._push_message(
                self.tr('Could not load the downloaded network from {}')
                .format(task.uri), level='critical')
            return
        self.taNetworkCombo.setLayer(out_layer)
        self.taNetFromLayer.setChecked(True)
        self._report_download(task.relatorio, task.tabela)

    def _report_download(self, relatorio, table):
        """Push the D5 download report: message bar + per-source, stitching and timing log lines."""
        fontes = relatorio.get('fontes') or []
        removidas = sum(f.get('removidas_inteiras', 0) for f in fontes)
        aparadas = sum(f.get('aparadas', 0) for f in fontes)
        costuradas = (relatorio.get('costura') or {}).get('costuradas', 0)
        note = self.tr(
            'Highway network downloaded: {} segment(s) from {} source(s) '
            'into {}').format(relatorio.get('feicoes', 0), len(fontes), table)
        if removidas or aparadas or costuradas:
            note += self.tr(
                ' — {} removed as duplicates, {} trimmed, {} stitched').format(
                    removidas, aparadas, costuradas)
        note += self.tr(' — per-source report in the Message Log')
        self._push_message(
            note, level='warning' if (removidas or aparadas or costuradas) else 'success')

        for fonte in fontes:
            QgsMessageLog.logMessage(
                self.tr('{}: {} segment(s) kept ({} downloaded, {} outside '
                        'the area, {} removed whole, {} trimmed, {:.0f} m '
                        'removed)').format(
                            fonte.get('nome') or fonte.get('id'),
                            fonte.get('linhas', 0), fonte.get('baixadas', 0),
                            fonte.get('fora_do_recorte', 0),
                            fonte.get('removidas_inteiras', 0),
                            fonte.get('aparadas', 0),
                            fonte.get('metros_removidos', 0.0)),
                'Desire Lines', Qgis.MessageLevel.Info)

        if relatorio.get('costura') is not None:
            c = relatorio.get('costura') or {}
            no_no = c.get('no_no', 0)
            t = c.get('t', 0)
            QgsMessageLog.logMessage(
                self.tr('Stitching: {} node-to-node, {} T').format(no_no, t),
                'Desire Lines', Qgis.MessageLevel.Info)

        if relatorio.get('tempos_s'):
            tempos = relatorio['tempos_s']
            dl = tempos.get('download')
            if isinstance(dl, dict):
                dl_parts = ['{}: {:.1f}s'.format(k, v) for k, v in dl.items()]
                dl_str = '{:.1f}s ({})'.format(sum(dl.values()), ', '.join(dl_parts)) if dl_parts else '{:.1f}s'.format(sum(dl.values()))
            elif isinstance(dl, (int, float)):
                dl_str = '{:.1f}s'.format(dl)
            else:
                dl_str = '0.0s'
            juncao = tempos.get('juncao', 0.0)
            costura = tempos.get('costura', 0.0)
            camada = tempos.get('camada', 0.0)
            total = tempos.get('total', 0.0)
            QgsMessageLog.logMessage(
                self.tr('Phase times: download {}, merge {:.1f}s, stitch {:.1f}s, layer {:.1f}s (total {:.1f}s)').format(
                    dl_str, juncao, costura, camada, total),
                'Desire Lines', Qgis.MessageLevel.Info)

    def run_capacity(self):
        """"Compute capacity": HCM capacity per arc, without assigning (D9).

        Works only on the layer selected in ``taNetworkCombo`` (D1): the
        download is a separate, explicit action.
        """
        road_layer = self.taNetworkCombo.currentLayer()

        progress = self._push_progress(self.tr('Computing HCM capacity…'))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            _g, arcs, _zn, _unc = self.build_traffic_network(
                road_layer=road_layer,
                overrides=self._traffic_overrides(),
                field_map=self._traffic_field_map(),
                id_field=self.taIdField.currentField() or None,
                crs=road_layer.crs() if road_layer is not None else None,
            )
            if not arcs:
                return
            self._publish_traffic_layer(
                arcs, [0.0] * len(arcs), {'metodo': 'capacidade'},
                self.traffic_crs, 'capacidade_hcm')
        finally:
            QApplication.restoreOverrideCursor()
            iface.messageBar().popWidget(progress)

        self._push_message(
            self.tr('Capacity computed for {} directed arcs — {}').format(
                len(arcs), self._provenance_note(arcs)),
            level='success')

    def run_assignment(self):
        """"Assign": build the network, run AoN or MSA/BPR and publish the flows.

        Works only on the layer selected in ``taNetworkCombo`` (D1): the
        download is a separate, explicit action. Logs the method used, the
        D7 provenance summary, the urban-arc count (D11) and the final gap
        — 'n/a' under AoN, where capacity never fed back into cost, so v/c
        above 1 means overload rather than equilibrium.
        """
        road_layer = self.taNetworkCombo.currentLayer()
        cent_layer = self.taCentroidsCombo.currentLayer()
        method = self._traffic_method()
        max_dist_m = self.taMaxDist.value()

        centroids, zone_keys = self._traffic_centroid_points(
            cent_layer, self.taZoneIdField.currentField())
        if not centroids:
            self._push_message(
                self.tr('The centroids layer has no usable geometry.'),
                level='critical')
            return

        # D4: the clipping box is built from the centroids only after they
        # are in the metric working CRS (buffer in real metres).
        bbox = None
        clip_buffer_m = max_dist_m

        progress = self._push_progress(
            self.tr('Assigning traffic ({})…').format(method.upper()))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            g, arcs, zone_node, _unconnected = self.build_traffic_network(
                road_layer=road_layer,
                centroids=centroids,
                zone_keys=zone_keys,
                overrides=self._traffic_overrides(),
                field_map=self._traffic_field_map(),
                max_dist_m=max_dist_m,
                id_field=self.taIdField.currentField() or None,
                crs=(road_layer.crs() if road_layer is not None
                     else cent_layer.crs()),
                centroids_crs=cent_layer.crs(),
                clip_buffer_m=clip_buffer_m,
            )
            if g is None or not zone_node:
                return

            od_pairs, unmatched = self.read_od_pairs(
                self.taMatrixCombo.currentLayer(), zone_node,
                origin_field=self.taOriginField.currentField(),
                dest_field=self.taDestField.currentField(),
                value_field=self.taValueField.currentField())
            if not od_pairs:
                self._push_message(
                    self.tr('No OD pair matches the connected centroids. Check '
                            'that Origin, Destination and Traffic id use the '
                            'same id scheme.'), level='critical')
                return

            flows, _history, stats = assignment.assign(
                g, arcs, od_pairs, method=method,
                max_iter=self.taMaxIter.value(),
                gap_tol=self.taGapTol.value())
            assigned_layer = self._publish_traffic_layer(
                arcs, flows, stats, self.traffic_crs, None)
            if assigned_layer is not None:
                self.taCalibAssignCombo.setLayer(assigned_layer)
        except Exception as err:
            self._push_message(
                self.tr('Traffic assignment failed: {}').format(err),
                level='critical')
            return
        finally:
            QApplication.restoreOverrideCursor()
            iface.messageBar().popWidget(progress)

        notes = [self._provenance_note(arcs)]
        if stats['gap'] is None:
            notes.append(self.tr(
                'gap: n/a — AoN does not feed capacity back into cost, so v/c '
                'above 1 diagnoses overload, not equilibrium'))
        else:
            notes.append(self.tr('final gap: {:.4f} in {} iteration(s)').format(
                stats['gap'], stats['iteracoes']))
        if unmatched:
            notes.append(self.tr('{} matrix rows had unknown ids').format(unmatched))
        if stats['unreachable']:
            notes.append(self.tr('{} pairs unreachable (disconnected network)')
                         .format(stats['unreachable']))
        road_arcs = sum(
            1 for a in arcs
            if getattr(a, 'scope', None) != network.CONNECTOR_LINK_ID
        )
        self._push_message(
            self.tr('{} done: {} pairs allocated over {} arcs — {}').format(
                method.upper(), stats['allocated'], road_arcs, '; '.join(notes)),
            level='success')

    def run_calibration(self):
        """Calibrate highway assignment against traffic counts (D3, D5)."""
        assign_layer = self.taCalibAssignCombo.currentLayer()
        posts_layer = self.taCountsCombo.currentLayer()
        count_field = self.taCountField.currentField()
        id_field = self.taPostIdField.currentField() or None
        max_dist_m = self.taCalibMaxDist.value()
        fator = self.taCalibFactor.value()

        progress = self._push_progress(self.tr('Calibrating assignment…')) if iface is not None else None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                resultados, n_invalidos = counts.casar_postos(
                    assign_layer=assign_layer,
                    posts_layer=posts_layer,
                    count_field=count_field,
                    id_field=id_field,
                    max_dist_m=max_dist_m,
                    fator=fator,
                    transform_context=QgsProject.instance().transformContext(),
                )
                if not resultados:
                    self._push_message(
                        self.tr('No valid count posts found.'), level='critical')
                    return
            except (ValueError, RuntimeError) as err:
                self._push_message(str(err), level='critical')
                return

            try:
                resumo = calibration.resumo(resultados)

                crs = assign_layer.crs() if assign_layer is not None else None
                mem_layer = outputs.calibration_to_layer(
                    resultados, crs=crs, layer_name='calibracao_geh')
                out_layer = self._write_layer_to_gpkg(mem_layer, 'calibracao_geh')
                if out_layer is not None:
                    outputs.apply_geh_style(out_layer)
            except Exception as err:
                self._push_message(
                    self.tr('Calibration failed: {}').format(err), level='critical')
                return
        finally:
            QApplication.restoreOverrideCursor()
            if iface is not None and progress is not None:
                iface.messageBar().popWidget(progress)

        # Mensagem final e Message Log conforme D5
        k = resumo['n_sem_link']
        n_total = len(resultados)
        sem_link_str = (
            f" ({k} " + self.tr('without a link within {} m').format(f'{max_dist_m:.0f}') + ')'
            if k else ''
        )
        pct_a = resumo['pct_a'] * 100.0
        pct_ab = resumo['pct_ab'] * 100.0
        rmse_str = f"{resumo['rmse_pct']:.1f}%" if resumo['rmse_pct'] is not None else 'n/a'
        dnit_status = self.tr('met') if resumo['atende_dnit'] else self.tr('not met')
        level = 'success' if resumo['atende_dnit'] else 'warning'

        msg = self.tr(
            'Calibration: {n} posts{sem_link} — A {pct_a:.1f}% · '
            'A+B {pct_ab:.1f}% · %RMSE {rmse} — '
            'DNIT criterion (≥60% A, ≥95% A+B): {status} (factor {factor})'
        ).format(
            n=n_total,
            sem_link=sem_link_str,
            pct_a=pct_a,
            pct_ab=pct_ab,
            rmse=rmse_str,
            status=dnit_status,
            factor=f'{fator:g}',
        )
        self._push_message(msg, level=level)

        if n_invalidos:
            QgsMessageLog.logMessage(
                self.tr('{} count posts ignored (null, non-numeric or negative count)').format(n_invalidos),
                'Desire Lines', Qgis.MessageLevel.Warning)

        postos_geh = [r for r in resultados if r.get('geh') is not None]
        postos_geh.sort(key=lambda r: r['geh'], reverse=True)
        for r in postos_geh[:10]:
            QgsMessageLog.logMessage(
                self.tr('Post {}: count {}, modeled {}, GEH {:.2f}').format(
                    r['posto'], f"{r['contagem']:g}", f"{r['modelado']:g}", r['geh']),
                'Desire Lines', Qgis.MessageLevel.Info)
