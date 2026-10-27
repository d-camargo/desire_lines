# coding=utf-8
"""Fixture e utilitários para a rede Sioux Falls (D8, D9)."""

import csv
import os
import sys

_PROCESSING_INITIALIZED = False
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'sioux_falls')


def _create_field(name, field_type):
    """Cria um QgsField compatível com Qt5 e Qt6."""
    from qgis.core import QgsField
    meta_name, variant_name = {
        'string': ('QString', 'String'),
        'double': ('Double', 'Double'),
        'int': ('Int', 'Int'),
    }.get(str(field_type).lower(), ('QString', 'String'))
    try:
        from qgis.PyQt.QtCore import QMetaType
        return QgsField(name, getattr(QMetaType.Type, meta_name))
    except (ImportError, AttributeError, TypeError):
        from qgis.PyQt.QtCore import QVariant
        return QgsField(name, getattr(QVariant, variant_name))


def init_processing():
    """Inicializa o framework QGIS Processing para testes (D9)."""
    global _PROCESSING_INITIALIZED
    if _PROCESSING_INITIALIZED:
        return

    from test.utilities import get_qgis_app
    app, canvas, iface, parent = get_qgis_app()

    try:
        import processing
    except ImportError:
        from qgis.core import QgsApplication
        pkg_path = app.pkgDataPath() if app is not None else QgsApplication.pkgDataPath()
        plugins_path = os.path.join(pkg_path, 'python', 'plugins')
        if plugins_path not in sys.path:
            sys.path.append(plugins_path)
        import processing

    from processing.core.Processing import Processing
    Processing.initialize()
    _PROCESSING_INITIALIZED = True


def load_nodes(path=None):
    """Carrega os 24 nós de Sioux Falls a partir de nodes.csv.

    Args:
        path (str, optional): Caminho customizado para nodes.csv.

    Returns:
        dict: Mapeamento {node_id: (x, y)} com coordenadas lon/lat (EPSG:4326).
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'nodes.csv')
    nodes = {}
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            node = int(row['node'])
            x = float(row['x'])
            y = float(row['y'])
            nodes[node] = (x, y)
    return nodes


def load_links(path=None):
    """Carrega os 76 links direcionados de Sioux Falls a partir de links.csv.

    Args:
        path (str, optional): Caminho customizado para links.csv.

    Returns:
        list of tuple: Lista de (init_node, term_node).
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'links.csv')
    links = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            init = int(row['init_node'])
            term = int(row['term_node'])
            links.append((init, term))
    return links


def load_link_records(path=None):
    """Carrega os registros completos dos 76 links a partir de links.csv.

    Args:
        path (str, optional): Caminho customizado para links.csv.

    Returns:
        list of dict: Lista de dicionários com init_node, term_node, capacity, length, free_flow_time.
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'links.csv')
    records = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                'init_node': int(row['init_node']),
                'term_node': int(row['term_node']),
                'capacity': float(row['capacity']),
                'length': float(row['length']),
                'free_flow_time': float(row['free_flow_time']),
            })
    return records


def load_trips(path=None):
    """Carrega os 528 pares OD de Sioux Falls com demanda > 0 a partir de trips.csv (D6).

    Args:
        path (str, optional): Caminho customizado para trips.csv.

    Returns:
        list of tuple: Lista de tuplas (origin, destination, demand) com 528 pares (total 360 600).
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'trips.csv')
    trips = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            o = int(row['origin'])
            d = int(row['destination'])
            dem = float(row['demand'])
            trips.append((o, d, dem))
    return trips


def load_reference_flow(path=None):
    """Carrega os 76 fluxos de equilíbrio do usuário (UE) de referência a partir de flow_ue.csv (D6).

    Args:
        path (str, optional): Caminho customizado para flow_ue.csv.

    Returns:
        dict: Mapeamento {(init_node, term_node): (volume, cost)} com volume e cost como floats.
    """
    if path is None:
        path = os.path.join(DATA_DIR, 'flow_ue.csv')
    flows = {}
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            u = int(row['init_node'])
            v = int(row['term_node'])
            flows[(u, v)] = (float(row['volume']), float(row['cost']))
    return flows


def road_layer(crs='EPSG:4326', tntp_attrs=False):
    """Cria uma camada QgsVectorLayer em memória LineString com os links de Sioux Falls.

    Args:
        crs: CRS da camada (str ou QgsCoordinateReferenceSystem, padrão 'EPSG:4326').
        tntp_attrs (bool): Se True, inclui campos capacity, free_flow_time e oneway (=1) (D6).
            Padrão False para não alterar testes existentes.

    Returns:
        QgsVectorLayer: Camada LineString com os links de Sioux Falls e 76 feições.
    """
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsFeature,
        QgsGeometry,
        QgsPointXY,
        QgsProject,
        QgsVectorLayer,
    )
    from test.utilities import get_qgis_app
    get_qgis_app()

    if isinstance(crs, str):
        target_crs = QgsCoordinateReferenceSystem(crs)
        crs_auth = crs
    else:
        target_crs = crs
        crs_auth = target_crs.authid() if target_crs.isValid() else 'EPSG:4326'

    layer = QgsVectorLayer(f"LineString?crs={crs_auth}", 'sioux_falls_roads', 'memory')
    dp = layer.dataProvider()

    fields = [
        _create_field('init_node', 'int'),
        _create_field('term_node', 'int'),
    ]
    if tntp_attrs:
        fields.extend([
            _create_field('capacity', 'double'),
            _create_field('free_flow_time', 'double'),
            _create_field('oneway', 'int'),
        ])
    dp.addAttributes(fields)
    layer.updateFields()

    nodes = load_nodes()
    link_records = load_link_records()

    src_crs = QgsCoordinateReferenceSystem('EPSG:4326')
    transform = None
    if target_crs.isValid() and target_crs.authid() != 'EPSG:4326':
        transform = QgsCoordinateTransform(src_crs, target_crs, QgsProject.instance())

    features = []
    for rec in link_records:
        init_node = rec['init_node']
        term_node = rec['term_node']
        x1, y1 = nodes[init_node]
        x2, y2 = nodes[term_node]
        pt1 = QgsPointXY(x1, y1)
        pt2 = QgsPointXY(x2, y2)
        if transform is not None:
            pt1 = transform.transform(pt1)
            pt2 = transform.transform(pt2)

        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry.fromPolylineXY([pt1, pt2]))
        if tntp_attrs:
            feat.setAttributes([
                init_node,
                term_node,
                rec['capacity'],
                rec['free_flow_time'],
                1,
            ])
        else:
            feat.setAttributes([init_node, term_node])
        features.append(feat)

    dp.addFeatures(features)
    layer.updateExtents()
    return layer


def od_all_pairs(demand=1.0):
    """Gera pares OD sintéticos para todos os 24x23 pares de nós (origem != destino).

    Args:
        demand (float): Demanda atribuída a cada par (padrão 1.0).

    Returns:
        list of tuple: Lista de (o, d, demand) com 552 tuplas.
    """
    nodes = sorted(load_nodes().keys())
    pairs = []
    for o in nodes:
        for d in nodes:
            if o != d:
                pairs.append((o, d, float(demand)))
    return pairs
