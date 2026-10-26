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

# Ancoragem de centróides por projeção no link mais próximo (D1/D2, 0.6.2):
# a menos de ANCHOR_END_TOL_M de uma ponta, dividir o link só criaria um
# pedaço degenerado — ancora no nó da ponta; projeções em links distintos
# mais próximas que ANCHOR_AMBIGUITY_M uma da outra são a mesma junção (não
# ambiguidade), e links quase equidistantes com projeções distantes entre si
# são ambíguos — caem para o nó mais próximo; conector mais longo que
# CONNECTOR_WARN_M é motivo de aviso no painel (D3).
ANCHOR_END_TOL_M = 0.5
ANCHOR_AMBIGUITY_M = 0.5
CONNECTOR_WARN_M = 1000.0
DEGREES_SUSPECT_SPAN = 10.0


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


def coords_crs_mismatch(extent, is_geographic):
    """Verifica se as coordenadas do extent são incompatíveis com o tipo de CRS (D8).

    Args:
        extent: Tupla/lista (xmin, ymin, xmax, ymax) ou objeto com
            xMinimum/yMinimum/xMaximum/yMaximum.
        is_geographic (bool): True se o CRS é geográfico (graus), False se projetado (metros).

    Returns:
        str | None:
            - 'out_of_geographic_range' se CRS for geográfico mas coordenadas
              estiverem fora de [-180, 180] x [-90, 90].
            - 'degrees_in_projected' se CRS for projetado mas coordenadas
              estiverem dentro de [-180, 180] x [-90, 90] com dimensão máxima
              positiva e menor que DEGREES_SUSPECT_SPAN.
            - None se não houver inconsistência detectada ou se o extent for degenerado.
    """
    if extent is None:
        return None
    if hasattr(extent, 'isNull') and callable(extent.isNull) and extent.isNull():
        return None
    if hasattr(extent, 'xMinimum'):
        x1 = extent.xMinimum()
        y1 = extent.yMinimum()
        x2 = extent.xMaximum()
        y2 = extent.yMaximum()
    else:
        try:
            x1, y1, x2, y2 = extent[:4]
        except (TypeError, ValueError):
            return None

    xmin, xmax = (x1, x2) if x1 <= x2 else (x2, x1)
    ymin, ymax = (y1, y2) if y1 <= y2 else (y2, y1)

    if is_geographic:
        if xmin < -180.0 or xmax > 180.0 or ymin < -90.0 or ymax > 90.0:
            return 'out_of_geographic_range'
        return None

    in_geographic = (-180.0 <= xmin <= 180.0 and -180.0 <= xmax <= 180.0 and
                     -90.0 <= ymin <= 90.0 and -90.0 <= ymax <= 90.0)
    span = max(xmax - xmin, ymax - ymin)
    if in_geographic and 0.0 < span < DEGREES_SUSPECT_SPAN:
        return 'degrees_in_projected'

    return None


def _run_processing_alg(alg_id, params):
    """Executa um algoritmo do Processing do QGIS (`qgis.processing.run`).

    Isolado em função própria só para poder ser substituído por um dublê nos
    testes, sem exigir o framework de Processing completo do QGIS.
    """
    from qgis import processing
    return processing.run(alg_id, params)


def reproject_layer(layer, target_crs):
    """Reprojeta uma camada vetorial para o CRS de destino via Processing (D2, D3).

    Args:
        layer: Camada vetorial de entrada (QgsVectorLayer ou compatível).
        target_crs: CRS de destino (QgsCoordinateReferenceSystem ou str authid).

    Returns:
        QgsVectorLayer: Camada reprojetada.
    """
    return _run_processing_alg('native:reprojectlayer', {
        'INPUT': layer,
        'TARGET_CRS': target_crs,
        'OUTPUT': 'TEMPORARY_OUTPUT',
    })['OUTPUT']


def clip_and_clean(road_layer, bbox, buffer_m=0.0, snap_tol_m=0.01):
    """Recorta a malha rodoviária pela área de estudo e uniformiza a geometria (D4).

    Aplica, nesta ordem: (1) recorte pelo `bbox` expandido por `buffer_m`
    (`native:extractbyextent`) — evita carregar a malha inteira da base
    oficial no grafo; (2) `native:snapgeometries`, unindo extremidades a até
    `snap_tol_m` de distância para que links vizinhos compartilhem nó; (3)
    `native:multiparttosingleparts`, para que cada feição vire um único
    segmento simples antes de virar arcos (D5).

    Args:
        road_layer: QgsVectorLayer com a malha rodoviária bruta (D6). Deve estar
            em CRS projetado (métrico).
        bbox (tuple): (xmin, ymin, xmax, ymax) da área de estudo, no CRS
            (métrico) de `road_layer`.
        buffer_m (float): expansão do bbox antes do recorte, em metros.
        snap_tol_m (float): tolerância de snap de vértices, em metros.

    Returns:
        QgsVectorLayer: malha recortada, com vértices ajustados e sem multipartes.

    Raises:
        ValueError: se `road_layer` possuir CRS geográfico (D2, D3).
        RuntimeError: se o Processing do QGIS não estiver disponível.
    """
    if hasattr(road_layer, 'crs'):
        crs = road_layer.crs() if callable(road_layer.crs) else road_layer.crs
        if crs is not None and hasattr(crs, 'isGeographic'):
            is_geo = crs.isGeographic() if callable(crs.isGeographic) else crs.isGeographic
            if is_geo:
                raise ValueError(
                    "A camada de rodovias possui CRS geográfico. "
                    "Reprojete para um CRS projetado (métrico) antes de chamar clip_and_clean."
                )

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


def _dist(a, b):
    """Distância euclidiana entre dois pontos (x, y)."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point_rect_distance(pt, bbox):
    """Distância mínima entre um ponto (x, y) e um retângulo (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = bbox
    dx = max(xmin - pt[0], 0.0, pt[0] - xmax)
    dy = max(ymin - pt[1], 0.0, pt[1] - ymax)
    return math.hypot(dx, dy)


def _project_point_on_polyline(pt, points):
    """Projeção ortogonal de um ponto sobre o segmento mais próximo da polyline.

    Args:
        pt (tuple): Ponto (x, y).
        points (list): Vértices (x, y) da polyline.

    Returns:
        tuple | None: (distancia, s ao longo da polyline, ponto_projetado), ou
        None se a polyline não tiver segmento de comprimento > 0.
    """
    best = None
    s_accum = 0.0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        seg_dx = x2 - x1
        seg_dy = y2 - y1
        seg_len = math.hypot(seg_dx, seg_dy)
        if seg_len <= 0.0:
            continue
        t = ((pt[0] - x1) * seg_dx + (pt[1] - y1) * seg_dy) / (seg_len * seg_len)
        t = max(0.0, min(1.0, t))
        qx = x1 + t * seg_dx
        qy = y1 + t * seg_dy
        d = math.hypot(pt[0] - qx, pt[1] - qy)
        if best is None or d < best[0]:
            best = (d, s_accum + t * seg_len, (qx, qy))
        s_accum += seg_len
    return best


def _split_polyline(points, splits):
    """Divide a polyline nos pontos de corte ``(s, nó)``, já ordenados por ``s``.

    O nó de corte entra como vértice de ponta dos dois pedaços vizinhos, para
    que as geometrias dos pedaços compartilhem o nó de âncora.

    Args:
        points (list): Vértices (x, y) da polyline.
        splits (list): Pares (s, nó) em ordem crescente de s.

    Returns:
        list: Polylines dos pedaços, do começo ao fim.
    """
    pieces = []
    current = [points[0]]
    s_accum = 0.0
    next_split = 0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        while (next_split < len(splits)
               and splits[next_split][0] <= s_accum + seg_len + 1e-9):
            _s_target, node = splits[next_split]
            if _dist(node, current[-1]) > 1e-9:
                current.append(node)
            if len(current) >= 2:
                pieces.append(current)
            current = [node]
            next_split += 1
        if _dist((x2, y2), current[-1]) > 1e-9:
            current.append((x2, y2))
        s_accum += seg_len
    if len(current) >= 2:
        pieces.append(current)
    if not pieces:
        pieces.append(list(points))
    return pieces


def _build_piece_arcs(link_id, entry, splits, precision):
    """Constrói os pares de arcos dos pedaços de um link dividido (D1).

    Cada pedaço ``k`` (na ordem do sentido direto) vira par fw/bw com
    ``arc_id=(link_id, sentido, k)``, mesmo ``link_id``, capacidade/escopo/
    parâmetros do arco original e ``t0`` proporcional ao comprimento do pedaço.

    Args:
        link_id (any): Identificador do link dividido.
        entry (dict): Entrada do link em `anchor_centroids` ('fw'/'bw'/'points'/'length').
        splits (list): Pares (s, nó) de corte, em ordem crescente de s.
        precision (int): Casas decimais do snap de nós.

    Returns:
        list: Arcos dos pedaços (fw_k, bw_k, fw_{k+1}, ...).
    """
    pieces = _split_polyline(entry['points'], splits)
    total = entry['length']
    arcs_out = []
    for k, piece in enumerate(pieces):
        length = calculate_length_m(piece)
        frac = (length / total) if total > 0.0 else 0.0
        for direction in ('fw', 'bw'):
            orig = entry[direction]
            if orig is None:
                continue
            pts = piece if direction == 'fw' else list(reversed(piece))
            arcs_out.append(Arc(
                arc_id=(link_id, direction, k),
                link_id=link_id,
                from_node=node_key(pts[0], precision),
                to_node=node_key(pts[-1], precision),
                length=length,
                t0=orig.t0 * frac,
                capacity=orig.capacity,
                scope=orig.scope,
                params=orig.params,
                sources=orig.sources,
                geometry=pts,
                forward=(direction == 'fw'),
            ))
    return arcs_out


def anchor_centroids(arcs, centroids, max_dist_m, precision=3):
    """Ancora cada centróide no ponto mais próximo do link mais próximo (D1, D2).

    Substitui `connect_centroids`: em vez de ligar o centróide ao **nó**
    existente mais próximo (que, em trecho com nós próximos, o prende à via
    errada e desenha uma ligação que não existe), projeta-o ortogonalmente
    sobre a polyline do link mais próximo e, quando o pé da projeção cai no
    meio do link, **divide o link nesse ponto** — a âncora vira um nó real do
    grafo, as duas metades roteiam por ela e o conector passa a carregar as
    viagens da zona. Cada zona ancorada ganha um par de conectores (ida e
    volta) entre o nó virtual `(CONNECTOR_LINK_ID, zone_id)` e o nó de âncora:
    o Dijkstra parte do nó virtual pelo conector (D2) e dois centróides na
    mesma âncora deixam de ser par ``o == d`` ignorado em silêncio.

    Casos extremos, sempre reportados em ``report`` (nunca exceção):

    - sem link candidato ou distância maior que ``max_dist_m``:
      ``report['unconnected']`` com a menor distância encontrada (ou ``None``);
    - link mais próximo ambíguo (outro link quase equidistante cuja projeção
      fica longe da primeira): ancora no nó existente mais próximo e registra
      ``report['fallback']`` — projeções que coincidem (junção) não são ambíguas;
    - pé da projeção a ``<= ANCHOR_END_TOL_M`` de uma ponta do link: ancora no
      nó da ponta, sem dividir;
    - vários centróides no mesmo link: divide de uma vez em todos os pontos,
      ordenados ao longo do link (pontos a ``<= ANCHOR_END_TOL_M`` um do outro
      se fundem num único nó);
    - conector mais longo que ``CONNECTOR_WARN_M``: ``report['far']``;
    - zonas que compartilham nó de âncora ou pontos distintos do mesmo link:
      ``report['shared_node']`` / ``report['shared_link']``.

    Args:
        arcs (list): Arcos já construídos (ex.: `build_network`), dois por link
            (direto/reverso). Arcos de conector (``scope ==
            CONNECTOR_LINK_ID``) são ignorados.
        centroids (list): Lista de centróides — tuplas/listas (x, y) ou
            objetos com métodos/atributos ``x``/``y``. O índice na lista é o id
            da zona (mesma convenção de ``od_pairs`` em `assignment.assign`).
        max_dist_m (float): Distância máxima, em metros, do centróide à malha
            (link ou, no fallback, nó).
        precision (int): Casas decimais do snap de nós.

    Returns:
        tuple: (net_arcs, connector_arcs, zone_node, report)
            net_arcs (list): A malha de entrada com os links divididos
                substituídos pelos pares de arcos de cada pedaço
                (``arc_id=(link_id, sentido, k)``), na ordem original; link
                sem centróide sai como o mesmo objeto `Arc`.
            connector_arcs (list): Arcos conectores (ida e volta) por zona
                ancorada, com `link_id=CONNECTOR_LINK_ID`, capacidade alta e
                custo desprezível.
            zone_node (dict): {zone_id: (CONNECTOR_LINK_ID, zone_id)} — o nó
                virtual de onde o roteamento parte e chega (D2).
            report (dict): Diagnóstico da ancoragem, por índice de zona:
                ``'unconnected': [(i, dist_ou_None)]``,
                ``'fallback': [i]``, ``'far': [(i, d)]``,
                ``'shared_node': [[i, j, ...]]``,
                ``'shared_link': {link_id: [i, j, ...]}`` e
                ``'anchors': {i: (x, y)}``.
    """
    # 1. Agrupa os arcos de malha por link (par fw/bw); conectores não entram.
    links = {}
    for arc in arcs:
        if getattr(arc, 'scope', None) == CONNECTOR_LINK_ID:
            continue
        entry = links.setdefault(arc.link_id, {'fw': None, 'bw': None})
        if arc.forward:
            if entry['fw'] is None:
                entry['fw'] = arc
        elif entry['bw'] is None:
            entry['bw'] = arc

    # Pré-cálculo por link: geometria na direção do fw (bbox para o pré-filtro
    # e polyline para a projeção exata).
    for entry in links.values():
        ref = entry['fw'] if entry['fw'] is not None else entry['bw']
        pts = [node_key(pt, precision) for pt in ref.geometry]
        entry['points'] = pts
        entry['length'] = calculate_length_m(pts)
        entry['bbox'] = (
            min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts),
        )

    # Nós existentes da malha (para o fallback ambíguo), em ordem determinística.
    nodes = []
    seen = set()
    for arc in arcs:
        if getattr(arc, 'scope', None) == CONNECTOR_LINK_ID:
            continue
        for node in (arc.from_node, arc.to_node):
            if node not in seen:
                seen.add(node)
                nodes.append(node)

    report = {
        'unconnected': [], 'fallback': [], 'far': [],
        'shared_node': [], 'shared_link': {}, 'anchors': {},
    }
    connector_arcs = []
    zone_node = {}
    # zone_id -> {'kind': 'split'|'node', 'link_id', 'node', 'd', 's'}
    anchored = {}

    for zone_id, centroid in enumerate(centroids):
        cx, cy = node_key(centroid, precision=6)

        # 2. Pré-filtro por bbox de link (distância ponto-retângulo <=
        # max_dist_m) e projeção ortogonal exata nos sobreviventes.
        candidates = []   # (d, link_id, s, q)
        min_seen = None   # menor distância conhecida (bbox ou exata)
        for link_id, entry in links.items():
            bbox_d = _point_rect_distance((cx, cy), entry['bbox'])
            if min_seen is None or bbox_d < min_seen:
                min_seen = bbox_d
            if bbox_d > max_dist_m:
                continue
            proj = _project_point_on_polyline((cx, cy), entry['points'])
            if proj is None:
                continue
            d, s, q = proj
            if min_seen is None or d < min_seen:
                min_seen = d
            candidates.append((d, link_id, s, q))

        # 3. Fora da rede: sem candidato ou nada dentro do teto.
        if not candidates:
            report['unconnected'].append((zone_id, min_seen))
            continue
        candidates.sort(key=lambda c: (c[0], str(c[1])))
        best_d, best_link, best_s, best_q = candidates[0]
        if best_d > max_dist_m:
            report['unconnected'].append((zone_id, best_d))
            continue

        # 4. Ambiguidade: outro link quase equidistante cuja projeção não
        # coincide com a do melhor (projeções iguais = junção, não ambíguo).
        ambiguous = any(
            d2 <= best_d + ANCHOR_AMBIGUITY_M
            and _dist(q2, best_q) > ANCHOR_AMBIGUITY_M
            for d2, _lid, _s2, q2 in candidates[1:]
        )
        if ambiguous:
            nearest = min(
                nodes,
                key=lambda n: (math.hypot(n[0] - cx, n[1] - cy), n),
            )
            node_d = math.hypot(nearest[0] - cx, nearest[1] - cy)
            if node_d > max_dist_m:
                report['unconnected'].append((zone_id, node_d))
                continue
            report['fallback'].append(zone_id)
            anchored[zone_id] = {
                'kind': 'node', 'link_id': None,
                'node': nearest, 'd': node_d, 's': None,
            }
            continue

        # 5/6. Na ponta: ancora no nó da ponta, sem dividir. No meio: a
        # âncora é um nó novo, o link será dividido nele.
        pts = links[best_link]['points']
        if _dist(best_q, pts[0]) <= ANCHOR_END_TOL_M:
            anchored[zone_id] = {
                'kind': 'node', 'link_id': best_link,
                'node': pts[0], 'd': best_d, 's': best_s,
            }
        elif _dist(best_q, pts[-1]) <= ANCHOR_END_TOL_M:
            anchored[zone_id] = {
                'kind': 'node', 'link_id': best_link,
                'node': pts[-1], 'd': best_d, 's': best_s,
            }
        else:
            anchored[zone_id] = {
                'kind': 'split', 'link_id': best_link,
                'node': node_key(best_q, precision), 'd': best_d, 's': best_s,
            }

    # 6. Divide cada link de uma vez nos pontos de âncora do meio, ordenados
    # por s; pontos a <= ANCHOR_END_TOL_M um do outro se fundem num único nó.
    split_items_by_link = {}
    for zone_id, info in anchored.items():
        if info['kind'] == 'split':
            split_items_by_link.setdefault(info['link_id'], []).append(
                (info['s'], info['node'], zone_id))

    piece_arcs_by_link = {}
    for link_id, items in split_items_by_link.items():
        items.sort(key=lambda t: (t[0], t[2]))
        merged = []   # [(s, nó, [zone_ids])]
        for s, node, zone_id in items:
            if merged and s - merged[-1][0] <= ANCHOR_END_TOL_M:
                merged[-1][2].append(zone_id)
            else:
                merged.append((s, node, [zone_id]))
        for _s, node, zone_ids in merged:
            for z in zone_ids:
                anchored[z]['node'] = node
        piece_arcs_by_link[link_id] = _build_piece_arcs(
            link_id, links[link_id],
            [(s, node) for s, node, _zs in merged], precision)

    # 7. Monta net_arcs na ordem original: link sem centróide sai com os
    # mesmos objetos; link dividido sai com os pedaços.
    net_arcs = []
    for link_id, entry in links.items():
        if link_id in piece_arcs_by_link:
            net_arcs.extend(piece_arcs_by_link[link_id])
        else:
            if entry['fw'] is not None:
                net_arcs.append(entry['fw'])
            if entry['bw'] is not None:
                net_arcs.append(entry['bw'])

    # 8. Conectores entre o nó virtual da zona e o nó de âncora (D2).
    for zone_id, centroid in enumerate(centroids):
        info = anchored.get(zone_id)
        if info is None:
            continue
        cx, cy = node_key(centroid, precision=6)
        node = info['node']
        d = info['d']
        zone_node[zone_id] = (CONNECTOR_LINK_ID, zone_id)
        report['anchors'][zone_id] = node
        if d > CONNECTOR_WARN_M:
            report['far'].append((zone_id, d))
        t0 = calculate_free_flow_time(d, CONNECTOR_FFS_KMH)
        connector_arcs.append(Arc(
            arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'fw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=(CONNECTOR_LINK_ID, zone_id),
            to_node=node,
            length=d,
            t0=t0,
            capacity=CONNECTOR_CAPACITY_VPH,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[(cx, cy), node],
            forward=True,
        ))
        connector_arcs.append(Arc(
            arc_id=(f'{CONNECTOR_LINK_ID}-{zone_id}', 'bw'),
            link_id=CONNECTOR_LINK_ID,
            from_node=node,
            to_node=(CONNECTOR_LINK_ID, zone_id),
            length=d,
            t0=t0,
            capacity=CONNECTOR_CAPACITY_VPH,
            scope=CONNECTOR_LINK_ID,
            params={},
            sources={},
            geometry=[node, (cx, cy)],
            forward=False,
        ))

    # 9. Zonas que compartilham nó de âncora ou pontos distintos do mesmo link.
    by_node = {}
    by_link = {}
    for zone_id, info in anchored.items():
        by_node.setdefault(info['node'], []).append(zone_id)
        if info['link_id'] is not None:
            by_link.setdefault(info['link_id'], {}).setdefault(
                info['node'], []).append(zone_id)
    report['shared_node'] = sorted(
        (sorted(zs) for zs in by_node.values() if len(zs) > 1),
        key=lambda zs: zs[0],
    )
    report['shared_link'] = {
        link_id: sorted(z for zs in by_link[link_id].values() for z in zs)
        for link_id in by_link if len(by_link[link_id]) > 1
    }

    return net_arcs, connector_arcs, zone_node, report


__all__ = [
    'Arc',
    'node_key',
    'extract_points',
    'calculate_length_m',
    'calculate_free_flow_time',
    'build_directed_arcs',
    'build_network',
    'clip_and_clean',
    'anchor_centroids',
    'reproject_layer',
    'DEGREES_SUSPECT_SPAN',
    'coords_crs_mismatch',
]
