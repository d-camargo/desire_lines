# coding=utf-8
"""Fixture e asserções para o caso de nós próximos do Diego (D5).

CRS: EPSG:31983 (SIRGAS 2000 / UTM zone 23S, métrico, sem reprojeção).
Nós: A(0,0), B(10000,0), N1(5000,300), N2(5003,300), T(5000,5000), U(10000,5000).
Links: L1 (A-B), L2 (N1-T), L3 (N2-U), L4 (T-U), L5 (B-U), L6 (A-T).
Centróides:
  1 -> (5000, -200)   (200 m abaixo do meio de L1; na lógica antiga ancorava em N1, cruzando L1)
  2 -> (7500, 5100)   (100 m acima de L4)
  3 -> (5001.5, 320)  (equidistante de N1 e N2 a 20,06 m; projeta em L2 a 1,5 m)
OD:
  1 -> 2 = 100
  3 -> 2 = 50
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)


def _create_field(name, field_type):
    """Cria um QgsField compatível com Qt5 e Qt6."""
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


# Nós da fixture D5
NODES = {
    'A': (0.0, 0.0),
    'B': (10000.0, 0.0),
    'N1': (5000.0, 300.0),
    'N2': (5003.0, 300.0),
    'T': (5000.0, 5000.0),
    'U': (10000.0, 5000.0),
}

# Geometrias dos links (id -> [(x, y), ...])
LINKS = {
    'L1': [(0.0, 0.0), (10000.0, 0.0)],
    'L2': [(5000.0, 300.0), (5000.0, 5000.0)],
    'L3': [(5003.0, 300.0), (10000.0, 5000.0)],
    'L4': [(5000.0, 5000.0), (10000.0, 5000.0)],
    'L5': [(10000.0, 0.0), (10000.0, 5000.0)],
    'L6': [(0.0, 0.0), (5000.0, 5000.0)],
}

# Centróides das zonas de tráfego (zone -> (x, y))
CENTROIDS = {
    1: (5000.0, -200.0),
    2: (7500.0, 5100.0),
    3: (5001.5, 320.0),
}

# Matriz OD de demanda ((origem, destino, viagens))
OD_PAIRS = [
    (1, 2, 100.0),
    (3, 2, 50.0),
]

# Âncoras esperadas sobre os links
EXPECTED_ANCHORS = {
    1: (5000.0, 0.0),
    2: (7500.0, 5000.0),
    3: (5000.0, 320.0),
}

# Comprimentos esperados dos conectores
EXPECTED_CONNECTOR_LENGTHS = {
    1: 200.0,
    2: 100.0,
    3: 1.5,
}


def road_layer(crs='EPSG:31983'):
    """Cria uma camada QgsVectorLayer em memória LineString com os links L1..L6.

    Args:
        crs (str | QgsCoordinateReferenceSystem): CRS da camada (padrão 'EPSG:31983').

    Returns:
        QgsVectorLayer: Camada em memória com campo 'id' (string) e 6 feições.
    """
    if isinstance(crs, str):
        crs_auth = crs
    elif isinstance(crs, QgsCoordinateReferenceSystem):
        crs_auth = crs.authid() if crs.isValid() else 'EPSG:31983'
    else:
        crs_auth = 'EPSG:31983'

    layer = QgsVectorLayer(f"LineString?crs={crs_auth}", 'close_nodes_roads', 'memory')
    dp = layer.dataProvider()
    dp.addAttributes([_create_field('id', 'string')])
    layer.updateFields()

    features = []
    for lid, pts in LINKS.items():
        feat = QgsFeature(layer.fields())
        polyline = [QgsPointXY(x, y) for x, y in pts]
        feat.setGeometry(QgsGeometry.fromPolylineXY(polyline))
        feat['id'] = lid
        features.append(feat)

    dp.addFeatures(features)
    layer.updateExtents()
    return layer


def centroid_layer(crs='EPSG:31983'):
    """Cria uma camada QgsVectorLayer em memória Point com os centróides da fixture.

    Args:
        crs (str | QgsCoordinateReferenceSystem): CRS da camada (padrão 'EPSG:31983').

    Returns:
        QgsVectorLayer: Camada em memória com campo 'zone' (int) e 3 feições de ponto.
    """
    if isinstance(crs, str):
        crs_auth = crs
    elif isinstance(crs, QgsCoordinateReferenceSystem):
        crs_auth = crs.authid() if crs.isValid() else 'EPSG:31983'
    else:
        crs_auth = 'EPSG:31983'

    layer = QgsVectorLayer(f"Point?crs={crs_auth}", 'close_nodes_centroids', 'memory')
    dp = layer.dataProvider()
    dp.addAttributes([_create_field('zone', 'int')])
    layer.updateFields()

    features = []
    for zid, (x, y) in CENTROIDS.items():
        feat = QgsFeature(layer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        feat['zone'] = zid
        features.append(feat)

    dp.addFeatures(features)
    layer.updateExtents()
    return layer


def od_layer():
    """Cria uma camada de tabela sem geometria com a matriz OD da fixture.

    Returns:
        QgsVectorLayer: Tabela em memória com campos 'orig' (int), 'dest' (int), 'trips' (double).
    """
    layer = QgsVectorLayer('none', 'close_nodes_od', 'memory')
    dp = layer.dataProvider()
    dp.addAttributes([
        _create_field('orig', 'int'),
        _create_field('dest', 'int'),
        _create_field('trips', 'double'),
    ])
    layer.updateFields()

    features = []
    for orig, dest, trips in OD_PAIRS:
        feat = QgsFeature(layer.fields())
        feat['orig'] = orig
        feat['dest'] = dest
        feat['trips'] = trips
        features.append(feat)

    dp.addFeatures(features)
    return layer


def assert_only_network(layer, links, centroids=None, tol_m=0.001):
    """Verifica que a camada contém apenas links originais e divididos (D5).

    Regras verificadas:
    1. Toda feição tem `tipo in ('link', 'link_dividido')`; não há conector nem outro tipo.
    2. Toda feição `tipo in ('link', 'link_dividido')` tem todos os vértices sobre a polyline
       do link original de mesmo `link_id` (tolerância tol_m = 1 mm) e, por `link_id`/sentido,
       os comprimentos dos pedaços somam o comprimento original (tolerância tol_m = 1 mm).

    Args:
        layer (QgsVectorLayer): Camada gravada ou gerada pela alocação.
        links (dict | QgsVectorLayer): Mapeamento {link_id: [(x, y), ...]} ou camada de links.
        centroids (dict | list | QgsVectorLayer, optional): Não utilizado (mantido por compatibilidade).
        tol_m (float): Tolerância geométrica em metros (padrão 0.001 = 1 mm).
    """
    # 1. Normalização dos links originais em {link_id: QgsGeometry}
    if hasattr(links, 'getFeatures'):
        link_dict = {}
        for feat in links.getFeatures():
            fields = [f.name() for f in feat.fields()]
            lid = feat['id'] if 'id' in fields else feat['link_id']
            link_dict[str(lid)] = feat.geometry()
    elif isinstance(links, dict):
        link_dict = {}
        for lid, pts in links.items():
            if isinstance(pts, QgsGeometry):
                link_dict[str(lid)] = pts
            else:
                polyline = [QgsPointXY(float(p[0]), float(p[1])) for p in pts]
                link_dict[str(lid)] = QgsGeometry.fromPolylineXY(polyline)
    else:
        raise TypeError(f"Formato de links não suportado: {type(links)}")

    orig_lengths = {lid: geom.length() for lid, geom in link_dict.items()}

    pieces_by_link_sentido = {}

    for feat in layer.getFeatures():
        tipo = feat['tipo']
        assert tipo in ('link', 'link_dividido'), (
            f"Tipo inesperado '{tipo}' na feição arc_id={feat['arc_id']}"
        )

        pts = feat.geometry().asPolyline()

        lid = str(feat['link_id'])
        assert lid in link_dict, f"link_id '{lid}' não pertence aos links originais"
        orig_geom = link_dict[lid]

        for pt in pts:
            dist = orig_geom.distance(QgsGeometry.fromPointXY(pt))
            assert dist <= tol_m, (
                f"Vértice {pt} do arco {feat['arc_id']} não está sobre o link original {lid} (dist={dist} m)"
            )

        sentido = str(feat['sentido'])
        pieces_by_link_sentido.setdefault((lid, sentido), []).append(feat)

    # Verifica a soma dos comprimentos dos pedaços para cada (link_id, sentido)
    for (lid, sentido), piece_feats in pieces_by_link_sentido.items():
        total_comp = sum(float(f['comp_m']) for f in piece_feats)
        orig_len = orig_lengths[lid]
        assert abs(total_comp - orig_len) <= tol_m, (
            f"Comprimentos somados de {lid} sentido {sentido} ({total_comp:.4f} m) "
            f"diferem do original ({orig_len:.4f} m)"
        )
