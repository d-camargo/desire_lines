# coding=utf-8
"""Módulo de saída e estilização de camadas para alocação de tráfego (D8, D15)."""

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsRuleBasedRenderer,
    QgsLineSymbol,
)

from .hcm import level_of_service
from .assignment import bpr_time
from .params import PARAMS
from .network import CONNECTOR_LINK_ID


def _create_field(name, field_type):
    """Cria um QgsField compatível com Qt5 e Qt6.

    `QMetaType.Type.<X>` existe tanto no PyQt5 quanto no PyQt6 e é a forma
    **não** obsoleta do construtor; o QVariant fica só como último recurso para
    QGIS antigo (o construtor por QVariant emite DeprecationWarning no 3.38+).
    Atenção aos nomes: em `QMetaType` o tipo texto é `QString`, em `QVariant` é
    `String` — usar o nome errado cai silenciosamente no caminho obsoleto.

    Args:
        name (str): Nome do campo.
        field_type (str): Tipo ('string', 'double', 'int', 'int64').

    Returns:
        QgsField: Instância configurada.
    """
    meta_name, variant_name = {
        'string': ('QString', 'String'),
        'double': ('Double', 'Double'),
        'int': ('Int', 'Int'),
        'int64': ('LongLong', 'LongLong'),
    }.get(str(field_type).lower(), ('QString', 'String'))
    try:
        from qgis.PyQt.QtCore import QMetaType
        return QgsField(name, getattr(QMetaType.Type, meta_name))
    except (ImportError, AttributeError, TypeError):
        from qgis.PyQt.QtCore import QVariant
        return QgsField(name, getattr(QVariant, variant_name))


def _is_integer_id(val):
    """Verifica se o valor pode ser representado como identificador inteiro (D3)."""
    if isinstance(val, bool):
        return False
    if isinstance(val, int):
        return True
    if isinstance(val, float) and val.is_integer():
        return True
    return False


def provenance_summary(arcs):
    """Conta a origem efetiva de cada parâmetro sobre todos os arcos (D7).

    Args:
        arcs (list): Arcos de `network.build_network`.

    Returns:
        dict: {'oficial': n, 'padrao': n, 'usuario': n} — número de
            (arco, parâmetro) resolvidos por cada origem. Conectores de
            centróide, que não têm parâmetros HCM, ficam de fora.
    """
    resumo = {'oficial': 0, 'padrao': 0, 'usuario': 0}
    for arc in arcs or []:
        for origem in (getattr(arc, 'sources', None) or {}).values():
            if origem in resumo:
                resumo[origem] += 1
    return resumo


def urban_arc_count(arcs):
    """Conta arcos marcados como travessia urbana (`escopo='urbano'`, D11)."""
    return sum(1 for arc in (arcs or []) if getattr(arc, 'scope', '') == 'urbano')


def flows_to_layer(arcs, fluxos, stats=None, crs=None, layer_name=None):
    """Materializa os arcos e seus fluxos alocados em uma camada vetorial QGIS.

    Camada do tipo LineString em memória contendo os atributos de tráfego,
    desempenho, provenientes de parâmetros e nível de serviço (D8, D15).
    Conectores de centróide (`scope == CONNECTOR_LINK_ID`) são arcos
    artificiais usados exclusivamente para o roteamento e não são publicados
    na camada de saída (D1).

    O tipo do campo `link_id` é `int64` quando todos os arcos publicados
    possuem identificador numérico inteiro (`int` excluindo `bool`, ou `float`
    com `.is_integer()`), e `string` como fallback quando contêm valores não
    numéricos (como texto `'L1'` ou tuplas) (D3).

    Args:
        arcs (list): Lista de objetos Arc (de `network.py`).
        fluxos (list | dict): Fluxo alocado por arco (na ordem de `arcs` se lista,
            ou mapeado por arco/arc_id se dicionário).
        stats (dict | None): Estatísticas da alocação (deve conter 'metodo' ou 'method').
        crs (QgsCoordinateReferenceSystem | str | None): Sistema de referência.
        layer_name (str | None): Nome da camada. Se None, é derivado do método
            (`alocacao_aon` / `alocacao_msa` / `alocacao_fw`), como manda D9/passo 15.

    Returns:
        QgsVectorLayer: Camada vetorial em memória pronta com feições e atributos.
    """
    stats = stats or {}
    metodo = str(stats.get('metodo', stats.get('method', 'msa'))).lower()

    if layer_name is None:
        layer_name = f'alocacao_{metodo}'

    if crs and hasattr(crs, 'authid') and callable(crs.authid) and crs.isValid():
        crs_auth = crs.authid()
    elif crs and hasattr(crs, 'authid') and not callable(crs.authid):
        crs_auth = str(crs.authid)
    elif crs:
        crs_auth = str(crs)
    else:
        crs_auth = 'EPSG:4326'

    uri = f"LineString?crs={crs_auth}"
    layer = QgsVectorLayer(uri, layer_name, 'memory')
    provider = layer.dataProvider()

    # D3: link_id é int64 quando todos os arcos publicados possuem id inteiro
    published_arcs = [
        arc for arc in (arcs or [])
        if getattr(arc, 'scope', None) != CONNECTOR_LINK_ID
    ]
    int_link_id = bool(published_arcs) and all(
        _is_integer_id(getattr(arc, 'link_id', None))
        for arc in published_arcs
    )
    link_id_field_type = 'int64' if int_link_id else 'string'

    # Campos base
    fields = [
        _create_field('arc_id', 'string'),
        _create_field('link_id', link_id_field_type),
        _create_field('tipo', 'string'),
        _create_field('sentido', 'string'),
        _create_field('faixas', 'int'),
        _create_field('comp_m', 'double'),
        _create_field('vel_livre', 'double'),
        _create_field('capacidade', 'double'),
        _create_field('volume', 'double'),
        _create_field('vc', 'double'),
        _create_field('los', 'string'),
        _create_field('tempo_h', 'double'),
        _create_field('atraso_h', 'double'),
        _create_field('metodo', 'string'),
        _create_field('escopo', 'string'),
    ]

    # Campos de proveniência dos parâmetros (src_*)
    param_keys = list(PARAMS.keys())
    for p_key in param_keys:
        fields.append(_create_field(f'src_{p_key}', 'string'))

    provider.addAttributes(fields)
    layer.updateFields()

    alpha = float(stats.get('alpha', 0.15))
    beta = float(stats.get('beta', 4.0))

    features = []
    if arcs:
        for idx, arc in enumerate(arcs):
            # D1: Conectores de centróide não são publicados; preserva idx para fluxos
            if getattr(arc, 'scope', None) == CONNECTOR_LINK_ID:
                continue

            # Obtém volume alocado
            if isinstance(fluxos, dict):
                v = float(fluxos.get(arc.arc_id, fluxos.get(arc, fluxos.get(idx, 0.0))))
            elif isinstance(fluxos, (list, tuple)) and idx < len(fluxos):
                v = float(fluxos[idx])
            else:
                v = 0.0

            cap = float(arc.capacity) if arc.capacity is not None else 0.0
            vc = (v / cap) if cap > 0.0 else 0.0
            los = level_of_service(vc)

            t0_min = float(arc.t0) if arc.t0 is not None else 0.0
            t0_h = t0_min / 60.0

            if v > 0.0 and cap > 0.0:
                t_min = bpr_time(t0_min, v, cap, alpha=alpha, beta=beta)
                tempo_h = float(t_min) / 60.0
            else:
                tempo_h = t0_h

            atraso_h = max(0.0, tempo_h - t0_h)

            if isinstance(getattr(arc, 'arc_id', None), (tuple, list)) and len(arc.arc_id) == 3:
                tipo = 'link_dividido'
            else:
                tipo = 'link'

            sentido = 'fw' if getattr(arc, 'forward', True) else 'bw'
            if isinstance(arc.arc_id, tuple) and len(arc.arc_id) >= 2:
                sentido = str(arc.arc_id[1])

            lanes = arc.params.get('lanes', arc.params.get('faixas', 1)) if hasattr(arc, 'params') and arc.params else 1
            vel_livre = arc.params.get('vel_livre', 80.0) if hasattr(arc, 'params') and arc.params else 80.0

            feat = QgsFeature(layer.fields())

            # Geometria
            if hasattr(arc, 'geometry') and arc.geometry:
                pts = [QgsPointXY(float(p[0]), float(p[1])) for p in arc.geometry]
                geom = QgsGeometry.fromPolylineXY(pts)
                feat.setGeometry(geom)

            link_id_val = int(arc.link_id) if int_link_id else str(arc.link_id)

            attr_vals = [
                str(arc.arc_id),
                link_id_val,
                tipo,
                sentido,
                int(lanes),
                float(arc.length),
                float(vel_livre),
                cap,
                v,
                vc,
                los,
                tempo_h,
                atraso_h,
                metodo,
                str(getattr(arc, 'scope', 'rodoviario')),
            ]

            sources_dict = getattr(arc, 'sources', {}) or {}
            for p_key in param_keys:
                attr_vals.append(str(sources_dict.get(p_key, 'padrao')))

            feat.setAttributes(attr_vals)
            features.append(feat)

    provider.addFeatures(features)
    layer.updateExtents()

    return layer


VC_CLASSES = [
    (0.00, 0.35, 'A (<= 0.35)', '#1a9641', 0.6),
    (0.35, 0.55, 'B (0.35 - 0.55)', '#a6d96a', 0.8),
    (0.55, 0.75, 'C (0.55 - 0.75)', '#ffffbf', 1.0),
    (0.75, 0.90, 'D (0.75 - 0.90)', '#fdae61', 1.2),
    (0.90, 1.00, 'E (0.90 - 1.00)', '#d7191c', 1.5),
    (1.00, 999999.0, 'F (> 1.00)', '#7b3294', 2.0),
]


def apply_vc_style(layer):
    """Aplica o estilo de simbologia baseado em regras (QgsRuleBasedRenderer).

    Aplica classes de v/c de A a F para os links da rede (D2, D4).

    Args:
        layer (QgsVectorLayer): Camada vetorial de saída da alocação.
    """
    if not layer or not layer.isValid():
        return

    root_rule = QgsRuleBasedRenderer.Rule(None)

    # Regras das classes A-F de v/c (D2, D4)
    for idx, (min_val, max_val, label, color_hex, width) in enumerate(VC_CLASSES):
        op = '<=' if idx == len(VC_CLASSES) - 1 else '<'
        filter_exp = f'"vc" >= {min_val} AND "vc" {op} {max_val}'
        symbol = QgsLineSymbol.createSimple({
            'color': color_hex,
            'width': str(width),
        })
        rule = QgsRuleBasedRenderer.Rule(
            symbol,
            filterExp=filter_exp,
            label=label,
        )
        root_rule.appendChild(rule)

    renderer = QgsRuleBasedRenderer(root_rule)
    layer.setRenderer(renderer)
    layer.triggerRepaint()


__all__ = [
    'flows_to_layer', 'apply_vc_style', 'provenance_summary', 'urban_arc_count',
]
