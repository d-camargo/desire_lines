import os
from qgis.PyQt import uic, QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsMapLayerProxyModel, QgsFieldProxyModel
from qgis.gui import QgsFieldComboBox, QgsFileWidget, QgsDockWidget
from qgis.utils import iface

try:
    from . import ui_common
    from .traffic import params, network, graph, outputs, assignment, gisbr_bridge
except ImportError:
    import ui_common
    
    from traffic import params, network, graph, outputs, assignment, gisbr_bridge

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'traffic_panel_base.ui'))

class TrafficAssignmentPanel(ui_common.PluginUiMixin, QgsDockWidget, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._build_traffic_params_ui()
        self.taNetworkCombo.layerChanged.connect(self._traffic_network_changed)
        self.taMatrixCombo.layerChanged.connect(self._traffic_matrix_changed)
        self.taCentroidsCombo.layerChanged.connect(self._traffic_centroids_changed)
        self.taRunCapacity.clicked.connect(self.run_capacity)
        self.taRunAssign.clicked.connect(self.run_assignment)
        for radio in (self.taNetFromLayer, self.taNetFromGisbr):
            radio.toggled.connect(self._update_traffic_tab_state)
        self.taUf.textChanged.connect(self._update_traffic_tab_state)
        self.taMethod.currentIndexChanged.connect(self._update_traffic_tab_state)
        for combo in (self.taNetworkCombo, self.taMatrixCombo,
                      self.taCentroidsCombo):
            combo.layerChanged.connect(self._update_traffic_tab_state)
        for combo in (self.taOriginField, self.taDestField, self.taValueField,
                      self.taZoneIdField):
            combo.fieldChanged.connect(self._update_traffic_tab_state)
        
        self.taMatrixCombo.setFilters(QgsMapLayerProxyModel.NoGeometry)
        self.taCentroidsCombo.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.taCentroidsCombo.setShowCrs(True)
        self.taNetworkCombo.setFilters(QgsMapLayerProxyModel.LineLayer)
        
        self.taOriginField.setFilters(QgsFieldProxyModel.Int)
        self.taDestField.setFilters(QgsFieldProxyModel.Int)
        self.taZoneIdField.setFilters(QgsFieldProxyModel.Int)
        self.taValueField.setFilters(QgsFieldProxyModel.Double)

        self.taOutputFile.setStorageMode(QgsFileWidget.SaveFile)
        self.taOutputFile.setFilter('GeoPackage (*.gpkg)')

        self._traffic_network_changed()
        self._traffic_matrix_changed()
        self._traffic_centroids_changed()
        self._update_traffic_tab_state()

    def _output_path(self):
        """Return the user-chosen output GPKG path, or a sensible fallback."""
        path = (self.taOutputFile.filePath() or '').strip()
        if path:
            if not path.lower().endswith('.gpkg'):
                path = path + '.gpkg'
            return os.path.abspath(path)
        return os.path.join(os.path.expanduser('~'), 'output.gpkg')

    # taMethod combo order must match: index 0 = AoN, index 1 = MSA (D10).
    TRAFFIC_METHODS = ('aon', 'msa')

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

    def _traffic_method(self):
        """Return the selected assignment method id ('aon' or 'msa')."""
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

    def _update_traffic_tab_state(self):
        """Enable/disable the highway tab and its buttons (steps 17, D6).

        The tab needs GisBR only when the network is to be downloaded; with an
        existing layer the rest of the tab works without it. The warning label
        stays visible while GisBR is missing so the reason is never hidden in a
        tooltip. Iterations and gap tolerance only apply to MSA, so AoN greys
        them out (D10).
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
        for widget in (self.taUf, self.taLabelUf, self.taClipToCentroids):
            widget.setEnabled(from_gisbr)

        is_msa = self._traffic_method() == 'msa'
        for widget in (self.taMaxIter, self.taGapTol,
                       self.taLabelMaxIter, self.taLabelGapTol):
            widget.setEnabled(is_msa)

        network_ready = bool(
            (from_gisbr and available and len(self.taUf.text().strip()) == 2)
            or (not from_gisbr and self.taNetworkCombo.currentLayer()))
        self.taRunCapacity.setEnabled(network_ready)
        self.taRunAssign.setEnabled(network_ready and bool(
            self.taMatrixCombo.currentLayer()
            and self.taCentroidsCombo.currentLayer()
            and self.taOriginField.currentField()
            and self.taDestField.currentField()
            and self.taValueField.currentField()
            and self.taZoneIdField.currentField()
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
    ):
        """Turn a highway layer into directed arcs plus a routable graph (steps 18-19).

        Reports every edge case as a translated message instead of raising:
        GisBR download failure, empty network after clipping, non-positive
        capacity and centroids that reach no node within ``max_dist_m``.

        Args:
            road_layer: QgsVectorLayer, iterable of QgsFeature, or list of
                dicts with a 'geometry' key (used by the tests). None with
                ``fetch_gisbr`` asks GisBR for the official network.
            centroids (list | None): Zone centroids as (x, y) tuples.
            zone_keys (list | None): Zone ids parallel to ``centroids``. When
                None, the list index is the zone id.
            overrides (dict | None): Global parameter overrides (D7).
            max_dist_m (float): Longest accepted centroid connector, in metres.
            id_field (str | None): Link id field of the highway layer.
            precision (int): Decimal places of the node snap.
            fetch_gisbr (bool): Download the network via GisBR instead.
            bbox, crs, uf: Passed through to ``gisbr_bridge.fetch_road_network``.

        Returns:
            tuple: ``(graph, arcs, zone_node, unconnected)``. ``graph`` is None
                and ``arcs`` empty when the network could not be built at all;
                ``zone_node`` maps zone id -> graph node and ``unconnected``
                lists the zone ids left out.
        """
        if fetch_gisbr or (road_layer is None and (bbox or uf)):
            try:
                road_layer = gisbr_bridge.fetch_road_network(
                    bbox=bbox, crs=crs, uf=uf)
            except Exception as err:
                self._push_message(
                    self.tr('Could not fetch the highway network from GisBR: {}')
                    .format(err), level='critical')
                return None, [], {}, []

        # CRS of the mesh the arcs actually came from — with the GisBR path the
        # caller cannot know it in advance, and labelling the output layer with
        # the wrong CRS would misplace every arc.
        self.traffic_crs = getattr(road_layer, 'crs', lambda: crs)()

        # D4: clip to the study area before building the graph. A failure here
        # is not fatal — it only means the graph is bigger (and slower) than it
        # had to be, so warn and carry on with the full mesh.
        if bbox is not None and hasattr(road_layer, 'getFeatures'):
            try:
                road_layer = network.clip_and_clean(road_layer, bbox)
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
            id_field=id_field) if features else []

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

        centroids = list(centroids or [])
        if not centroids:
            return graph.build_graph(arcs), arcs, {}, []

        keys = list(zone_keys) if zone_keys else list(range(len(centroids)))
        connectors, node_by_index, unconnected_idx = network.connect_centroids(
            arcs, centroids, max_dist_m=max_dist_m)
        all_arcs = arcs + connectors
        zone_node = {keys[i]: node for i, node in node_by_index.items()}
        unconnected = [keys[i] for i in unconnected_idx]

        if unconnected and not zone_node:
            self._push_message(
                self.tr('No centroid could be connected to the highway network '
                        '(nearest node farther than {:.0f} m).').format(max_dist_m),
                level='critical')
        elif unconnected:
            self._push_message(
                self.tr('{} centroid(s) not connected to the highway network.')
                .format(len(unconnected)))

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

    def _publish_traffic_layer(self, arcs, flows, stats, crs, table):
        """Write the arcs+flows layer to the output GeoPackage and style it by v/c."""
        mem = outputs.flows_to_layer(
            arcs, flows, stats=stats, crs=crs, layer_name=table)
        out_layer = self._write_layer_to_gpkg(mem, table)
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

    def run_capacity(self):
        """"Compute capacity": HCM capacity per arc, without assigning (D9)."""
        road_layer = self.taNetworkCombo.currentLayer()
        from_gisbr = self.taNetFromGisbr.isChecked()
        crs = road_layer.crs() if road_layer is not None else None

        progress = self._push_progress(self.tr('Computing HCM capacity…'))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            _g, arcs, _zn, _unc = self.build_traffic_network(
                road_layer=None if from_gisbr else road_layer,
                overrides=self._traffic_overrides(),
                id_field=self.taIdField.currentField() or None,
                fetch_gisbr=from_gisbr,
                uf=self.taUf.text().strip() or None,
                crs=crs,
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

        Logs the method used, the D7 provenance summary, the urban-arc count
        (D11) and the final gap — 'n/a' under AoN, where capacity never fed
        back into cost, so v/c above 1 means overload rather than equilibrium.
        """
        road_layer = self.taNetworkCombo.currentLayer()
        cent_layer = self.taCentroidsCombo.currentLayer()
        from_gisbr = self.taNetFromGisbr.isChecked()
        method = self._traffic_method()
        max_dist_m = self.taMaxDist.value()
        crs = (road_layer.crs() if road_layer is not None else cent_layer.crs())

        centroids, zone_keys = self._traffic_centroid_points(
            cent_layer, self.taZoneIdField.currentField())
        if not centroids:
            self._push_message(
                self.tr('The centroids layer has no usable geometry.'),
                level='critical')
            return

        # D4: the study area is the centroids' bbox plus the connector radius.
        # It both bounds the GisBR download and clips an existing layer.
        bbox = self._traffic_bbox(centroids, max_dist_m)
        if from_gisbr and not self.taClipToCentroids.isChecked():
            bbox = None

        progress = self._push_progress(
            self.tr('Assigning traffic ({})…').format(method.upper()))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            g, arcs, zone_node, _unconnected = self.build_traffic_network(
                road_layer=None if from_gisbr else road_layer,
                centroids=centroids,
                zone_keys=zone_keys,
                overrides=self._traffic_overrides(),
                max_dist_m=max_dist_m,
                id_field=self.taIdField.currentField() or None,
                fetch_gisbr=from_gisbr,
                bbox=bbox,
                uf=self.taUf.text().strip() or None,
                crs=crs,
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
            self._publish_traffic_layer(
                arcs, flows, stats, self.traffic_crs, None)
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
        self._push_message(
            self.tr('{} done: {} pairs allocated over {} arcs — {}').format(
                method.upper(), stats['allocated'], len(arcs), '; '.join(notes)),
            level='success')
