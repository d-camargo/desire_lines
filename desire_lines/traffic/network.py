# coding=utf-8
"""Construção da rede rodoviária e conversão em arcos direcionados (D5, D7, D8)."""

import math
from .params import resolve
from .hcm import segment_capacity

# Conector centróide->nó (D4/D8): capacidade alta e custo desprezível para não
# virar gargalo nem influenciar a escolha de rota, servindo só de "rampa de
# acesso" da zona até a malha.
CONNECTOR_LINK_ID = 'conector'
CONNECTOR_CAPACITY_VPH = 99999.0
CONNECTOR_FFS_KMH = 200.0


class Arc(object):
    """Representa um arco direcionado na malha rodoviária.

    Attributes:
        arc_id (tuple | str): Identificador único do arco direcionado.
        link_id (any): Identificador do link/feição de origem.
        from_node (tuple): Coordenadas (x, y) arredondadas do nó inicial.
        to_node (tuple): Coordenadas (x, y) arredondadas do nó final.
        length (float): Comprimento do trecho em metros.
        t0 (float): Tempo de viagem a fluxo livre em minutos.
        capacity (float): Capacidade por sentido em veíc/h.
        scope (str): Escopo do trecho ('rodoviario' ou 'urbano').
        params (dict): Parâmetros HCM resolvidos.
        sources (dict): Proveniência das origens dos parâmetros ('padrao', 'oficial', 'usuario').
        geometry (list): Lista de coordenadas (x, y) na direção do arco.
        forward (bool): True se for o sentido direto (origem->destino), False se for o reverso.
    """

    def __init__(
        self,
        arc_id,
        link_id,
        from_node,
        to_node,
        length,
        t0,
        capacity,
        scope,
        params,
        sources,
        geometry,
        forward=True,
    ):
        self.arc_id = arc_id
        self.link_id = link_id
        self.from_node = from_node
        self.to_node = to_node
        self.length = float(length)
        self.t0 = float(t0)
        self.capacity = float(capacity)
        self.scope = scope
        self.params = params or {}
        self.sources = sources or {}
        self.geometry = geometry or []
        self.forward = bool(forward)

    def __repr__(self):
        return (
            f"<Arc id={self.arc_id!r} {self.from_node} -> {self.to_node} "
            f"len={self.length:.1f}m t0={self.t0:.2f}min cap={self.capacity:.0f}veic/h "
            f"scope={self.scope!r}>"
        )


def node_key(pt, precision=3):
    """Gera uma chave única de nó (x, y) arredondada à precisão especificada.

    Args:
        pt: Tupla (x, y), lista [x, y] ou objeto com métodos x() e y().
        precision (int): Número de casas decimais para snap/arredondamento (padrão 3).

    Returns:
        tuple: (round(x, precision), round(y, precision)).
    """
    if hasattr(pt, 'x') and hasattr(pt, 'y'):
        x = pt.x() if callable(pt.x) else pt.x
        y = pt.y() if callable(pt.y) else pt.y
    else:
        x, y = pt[0], pt[1]
    return (round(float(x), precision), round(float(y), precision))


def extract_points(geometry):
    """Extrai lista de coordenadas (x, y) de uma geometria.

    Suporta QgsGeometry (LineString/MultiLineString), dicionário GeoJSON e lista de pontos.

    Args:
        geometry: Objeto de geometria QGIS, dict GeoJSON ou lista de pontos [(x, y), ...].

    Returns:
        list: Lista de tuplas (x, y).
    """
    if geometry is None:
        return []

    # Lista/tupla de pontos
    if isinstance(geometry, (list, tuple)):
        if not geometry:
            return []
        first = geometry[0]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            return [(float(pt[0]), float(pt[1])) for pt in geometry]
        return []

    # Dict estilo GeoJSON
    if isinstance(geometry, dict):
        coords = geometry.get('coordinates', [])
        gtype = str(geometry.get('type', '')).lower()
        if gtype == 'linestring':
            return [(float(pt[0]), float(pt[1])) for pt in coords]
        elif gtype == 'multilinestring' and coords:
            flat = []
            for line in coords:
                flat.extend([(float(pt[0]), float(pt[1])) for pt in line])
            return flat

    # QgsGeometry ou objeto compatível QGIS
    if hasattr(geometry, 'asPolyline') and callable(geometry.asPolyline):
        polyline = geometry.asPolyline()
        if polyline:
            return [(float(pt.x()), float(pt.y())) for pt in polyline]

    if hasattr(geometry, 'asMultiPolyline') and callable(geometry.asMultiPolyline):
        multi = geometry.asMultiPolyline()
        if multi:
            flat = []
            for line in multi:
                flat.extend([(float(pt.x()), float(pt.y())) for pt in line])
            return flat

    return []


def calculate_length_m(points):
    """Calcula o comprimento acumulado em metros de uma linha representada por pontos (x, y).

    Presume coordenadas projetadas em metros (CRS métrico).

    Args:
        points (list): Lista de tuplas (x, y).

    Returns:
        float: Comprimento total em metros.
    """
    if not points or len(points) < 2:
        return 0.0

    total = 0.0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def calculate_free_flow_time(length_m, ffs_kmh):
    """Calcula o tempo de viagem a fluxo livre (t0) em minutos.

    Args:
        length_m (float): Comprimento em metros.
        ffs_kmh (float): Velocidade de fluxo livre em km/h.

    Returns:
        float: Tempo em minutos (t0).
    """
    length_km = float(length_m) / 1000.0
    speed = float(ffs_kmh) if ffs_kmh is not None and float(ffs_kmh) > 0 else 80.0
    return (length_km / speed) * 60.0


def build_directed_arcs(link_id, points, feature=None, overrides=None, length_m=None, precision=3):
    """Constrói os dois arcos direcionados (direto e reverso) para um link rodoviário (D5).

    Args:
        link_id (any): Identificador único do link.
        points (list): Lista de tuplas (x, y).
        feature (dict | QgsFeature | None): Feição com atributos da rodovia.
        overrides (dict | None): Parâmetros sobrescritos pelo usuário.
        length_m (float | None): Comprimento em metros (se None, calculado dos pontos).
        precision (int): Precisão do snap de nós.

    Returns:
        tuple: (arc_fw, arc_bw) com os arcos direto e reverso.
    """
    if not points or len(points) < 2:
        raise ValueError(f"Link {link_id} não possui geometria válida com ao menos 2 pontos.")

    if length_m is None:
        length_m = calculate_length_m(points)

    valores, origens = resolve(feature=feature, overrides=overrides)
    cap, scope = segment_capacity(valores)
    ffs = valores.get('vel_livre', 80.0)
    t0 = calculate_free_flow_time(length_m, ffs)

    u = node_key(points[0], precision)
    v = node_key(points[-1], precision)

    arc_fw = Arc(
        arc_id=(link_id, 'fw'),
        link_id=link_id,
        from_node=u,
        to_node=v,
        length=length_m,
        t0=t0,
        capacity=cap,
        scope=scope,
        params=valores,
        sources=origens,
        geometry=list(points),
        forward=True,
    )

    arc_bw = Arc(
        arc_id=(link_id, 'bw'),
        link_id=link_id,
        from_node=v,
        to_node=u,
        length=length_m,
        t0=t0,
        capacity=cap,
        scope=scope,
        params=valores,
        sources=origens,
        geometry=list(reversed(points)),
        forward=False,
    )

    return arc_fw, arc_bw


def build_network(features, overrides=None, precision=3, id_field=None):
    """Processa uma coleção de feições/links rodoviários e constrói a rede de arcos direcionados.

    Args:
        features (iterable): Iterável de feições (QgsFeature, dicts com 'geometry'/'attributes' ou objetos).
        overrides (dict | None): Sobrescritas globais de parâmetros pelo usuário.
        precision (int): Casas decimais para snap de nós (padrão 3).
        id_field (str | None): Nome do campo de ID do link. Se None, tenta 'id', 'gid', 'link_id', etc. ou índice numérico.

    Returns:
        list: Lista de objetos Arc direcionados (2 por link válido).
    """
    arcs = []
    if not features:
        return arcs

    idx = 0
    for feat in features:
        idx += 1
        link_id = None
        geometry = None
        attr_dict = None

        if isinstance(feat, dict):
            geometry = feat.get('geometry')
            attr_dict = feat.get('attributes', feat)
            if id_field and id_field in feat:
                link_id = feat[id_field]
            elif 'id' in feat:
                link_id = feat['id']
            elif 'link_id' in feat:
                link_id = feat['link_id']
            elif 'gid' in feat:
                link_id = feat['gid']
        else:
            if hasattr(feat, 'geometry') and callable(feat.geometry):
                geometry = feat.geometry()
            elif hasattr(feat, 'geometry'):
                geometry = feat.geometry

            if hasattr(feat, 'id') and callable(feat.id):
                link_id = feat.id()

            if id_field and hasattr(feat, 'attribute'):
                try:
                    link_id = feat.attribute(id_field)
                except Exception:
                    pass

            attr_dict = feat

        if link_id is None:
            link_id = idx

        points = extract_points(geometry)
        if not points or len(points) < 2:
            continue

        fw, bw = build_directed_arcs(
            link_id=link_id,
            points=points,
            feature=attr_dict,
            overrides=overrides,
            precision=precision,
        )
        arcs.append(fw)
        arcs.append(bw)

    return arcs


def _run_processing_alg(alg_id, params):
    """Executa um algoritmo do Processing do QGIS (`qgis.processing.run`).

    Isolado em função própria só para poder ser substituído por um dublê nos
    testes, sem exigir o framework de Processing completo do QGIS.
    """
    from qgis import processing
    return processing.run(alg_id, params)


def clip_and_clean(road_layer, bbox, buffer_m=0.0, snap_tol_m=0.01):
    """Recorta a malha rodoviária pela área de estudo e uniformiza a geometria (D4).

    Aplica, nesta ordem: (1) recorte pelo `bbox` expandido por `buffer_m`
    (`native:extractbyextent`) — evita carregar a malha inteira da base
    oficial no grafo; (2) `native:snapgeometries`, unindo extremidades a até
    `snap_tol_m` de distância para que links vizinhos compartilhem nó; (3)
    `native:multiparttosingleparts`, para que cada feição vire um único
    segmento simples antes de virar arcos (D5).

    Args:
        road_layer: QgsVectorLayer com a malha rodoviária bruta (D6).
        bbox (tuple): (xmin, ymin, xmax, ymax) da área de estudo, no CRS
            (métrico) de `road_layer`.
        buffer_m (float): expansão do bbox antes do recorte, em metros.
        snap_tol_m (float): tolerância de snap de vértices, em metros.

    Returns:
        QgsVectorLayer: malha recortada, com vértices ajustados e sem multipartes.

    Raises:
        RuntimeError: se o Processing do QGIS não estiver disponível.
    """
    try:
        from qgis.core import QgsRectangle
    except ImportError:
        raise RuntimeError(
            "Processing do QGIS não está disponível para recortar a malha rodoviária."
        )

    xmin, ymin, xmax, ymax = bbox
    extent = QgsRectangle(
        xmin - buffer_m, ymin - buffer_m, xmax + buffer_m, ymax + buffer_m
    )

    clipped = _run_processing_alg('native:extractbyextent', {
        'INPUT': road_layer,
        'EXTENT': extent,
        'CLIP': True,
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })['OUTPUT']

    snapped = _run_processing_alg('native:snapgeometries', {
        'INPUT': clipped,
        'REFERENCE_LAYER': clipped,
        'TOLERANCE': snap_tol_m,
        'BEHAVIOR': 0,
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })['OUTPUT']

    single = _run_processing_alg('native:multiparttosingleparts', {
        'INPUT': snapped,
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })['OUTPUT']

    return single


def connect_centroids(arcs, centroids, max_dist_m):
    """Cria arcos-conectores entre centróides de zona e o nó mais próximo da malha.

    Cada centróide conectado ganha um par de arcos (ida e volta, como em D5)
    até o nó existente mais próximo, com `link_id='conector'`, capacidade alta
    e custo desprezível (`CONNECTOR_CAPACITY_VPH`/`CONNECTOR_FFS_KMH`), para
    servir de rampa de acesso à malha sem influenciar a alocação. Centróides
    sem nó a até `max_dist_m` não são conectados — o motivo é reportado, sem
    lançar exceção, para que a alocação siga normalmente para os pares OD que
    alcançam a malha.

    Args:
        arcs (list): Arcos já construídos (ex.: `build_network`); seus nós
            (`from_node`/`to_node`) formam o conjunto de destinos possíveis.
        centroids (list): Lista de centróides — tuplas/listas (x, y) ou
            objetos com métodos/atributos `x`/`y` (ex.: `QgsPointXY`). O
            índice na lista é o id da zona (mesma convenção de `od_pairs` em
            `aon.allocate_aon`).
        max_dist_m (float): Distância máxima, em metros, para aceitar a conexão.

    Returns:
        tuple: (connector_arcs, zone_node, unconnected)
            connector_arcs (list): Arcos conectores (ida e volta) por centróide conectado.
            zone_node (dict): {zone_id: node} para os centróides conectados.
            unconnected (list): ids de zona sem conector (fora de `max_dist_m`
                ou malha vazia).
    """
    nodes = []
    seen = set()
    for arc in arcs:
        for node in (arc.from_node, arc.to_node):
            if node not in seen:
                seen.add(node)
                nodes.append(node)

    connector_arcs = []
    zone_node = {}
    unconnected = []

    for zone_id, centroid in enumerate(centroids):
        cx, cy = node_key(centroid, precision=6)

        if not nodes:
            unconnected.append(zone_id)
            continue

        nearest = min(nodes, key=lambda n: math.hypot(n[0] - cx, n[1] - cy))
        dist = math.hypot(nearest[0] - cx, nearest[1] - cy)

        if dist > max_dist_m:
            unconnected.append(zone_id)
            continue

        zone_node[zone_id] = nearest
        centroid_node = (cx, cy)
        t0 = calculate_free_flow_time(dist, CONNECTOR_FFS_KMH)

        connector_arcs.append(Arc(
            arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'fw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=centroid_node,
            to_node=nearest,
            length=dist,
            t0=t0,
            capacity=CONNECTOR_CAPACITY_VPH,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[centroid_node, nearest],
            forward=True,
        ))
        connector_arcs.append(Arc(
            arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'bw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=nearest,
            to_node=centroid_node,
            length=dist,
            t0=t0,
            capacity=CONNECTOR_CAPACITY_VPH,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[nearest, centroid_node],
            forward=False,
        ))

    return connector_arcs, zone_node, unconnected


__all__ = [
    'Arc',
    'node_key',
    'extract_points',
    'calculate_length_m',
    'calculate_free_flow_time',
    'build_directed_arcs',
    'build_network',
    'clip_and_clean',
    'connect_centroids',
]
