# coding=utf-8
"""Catálogo declarativo de parâmetros e resolução de valores/origens (D7)."""

# Padrão por classe de via (D4, etapa 7): usado quando nenhuma etapa anterior
# da cascata dá valor a `lanes`/`vel_livre`. A classe sai de
# `tipo_segmento`/`pavimentado`, resolvidos na primeira passada.
PADRAO_POR_CLASSE = {
    'pista_dupla': {'lanes': 2, 'vel_livre': 100.0},
    'pista_simples_pavimentada': {'lanes': 1, 'vel_livre': 80.0},
    'nao_pavimentada': {'lanes': 1, 'vel_livre': 60.0},
}

# Grafias de pista dupla aceitas por `hcm.segment_capacity` (ramo multilane).
_TIPOS_PISTA_DUPLA = ('multilane', 'freeway', 'pista_dupla', 'duplicada',
                      'pista dupla', 'dupla', 'multifaixa')

# Primeira passada da cascata: definem a classe da via (D4).
_PRIMEIRA_PASSADA = ('tipo_segmento', 'pavimentado')

PARAMS = {
    'tipo_segmento': {
        'id': 'tipo_segmento',
        'rotulo': 'Tipo de segmento',
        'unidade': '',
        'tipo': str,
        'default': '2_faixas',
        'campos_candidatos': ['tipo_pista', 'pista', 'tipo_seg', 'tp_pista', 'ds_pista', 'tipo_segmento'],
    },
    'lanes': {
        'id': 'lanes',
        'rotulo': 'Número de faixas por sentido',
        'unidade': 'faixas',
        'tipo': int,
        'default': 1,
        'campos_candidatos': ['faixas', 'num_faixas', 'faixas_sentido', 'nr_faixas', 'n_faixas', 'lanes'],
    },
    'pavimentado': {
        'id': 'pavimentado',
        'rotulo': 'Pavimentado',
        'unidade': '',
        'tipo': bool,
        'default': True,
        'campos_candidatos': ['pavimentado', 'superficie', 'tp_superficie', 'ds_superficie', 'st_pavimentado'],
    },
    'urbano': {
        'id': 'urbano',
        'rotulo': 'Trecho urbano',
        'unidade': '',
        'tipo': bool,
        'default': False,
        'campos_candidatos': ['urbano', 'trecho_urbano', 'travessia_urbana', 'tp_trecho', 'is_urbano'],
    },
    'largura_faixa': {
        'id': 'largura_faixa',
        'rotulo': 'Largura de faixa',
        'unidade': 'm',
        'tipo': float,
        'default': 3.5,
        'campos_candidatos': ['largura_faixa', 'larg_faixa', 'lane_width'],
    },
    'largura_acostamento': {
        'id': 'largura_acostamento',
        'rotulo': 'Largura de acostamento',
        'unidade': 'm',
        'tipo': float,
        'default': 2.5,
        'campos_candidatos': ['largura_acostamento', 'acostamento', 'shoulder_width'],
    },
    'terreno': {
        'id': 'terreno',
        'rotulo': 'Tipo de terreno',
        'unidade': '',
        'tipo': str,
        'default': 'ondulado',
        'campos_candidatos': ['terreno', 'tp_terreno', 'ds_terreno', 'terrain'],
    },
    'pct_veic_pesados': {
        'id': 'pct_veic_pesados',
        'rotulo': 'Percentual de veículos pesados',
        'unidade': '%',
        'tipo': float,
        'default': 20.0,
        'campos_candidatos': ['pct_veic_pesados', 'pct_pesados', 'veic_pesados', 'pct_hv', 'heavy_vehicles'],
    },
    'vel_livre': {
        'id': 'vel_livre',
        'rotulo': 'Velocidade de fluxo livre (FFS)',
        'unidade': 'km/h',
        'tipo': float,
        'default': 80.0,
        'campos_candidatos': ['vel_livre', 'ffs', 'v_livre', 'vl_maxima', 'speed_limit'],
    },
    'phf': {
        'id': 'phf',
        'rotulo': 'Fator de Hora de Pico (PHF)',
        'unidade': '',
        'tipo': float,
        'default': 0.92,
        'campos_candidatos': ['phf', 'fator_pico', 'peak_hour_factor'],
    },
    'pct_no_passing': {
        'id': 'pct_no_passing',
        'rotulo': 'Zonas de ultrapassagem proibida',
        'unidade': '%',
        'tipo': float,
        'default': 50.0,
        'campos_candidatos': ['pct_no_passing', 'ultrapassagem_proibida', 'pct_proib_ultrapassagem'],
    },
    'access_density': {
        'id': 'access_density',
        'rotulo': 'Densidade de acessos',
        'unidade': 'acessos/km',
        'tipo': float,
        'default': 10.0,
        'campos_candidatos': ['access_density', 'densidade_acessos', 'n_acessos_km'],
    },
    'directional_split': {
        'id': 'directional_split',
        'rotulo': 'Divisão direcional',
        'unidade': '%',
        'tipo': float,
        'default': 50.0,
        'campos_candidatos': ['directional_split', 'divisao_direcional', 'split_dir'],
    },
    'bpr_alpha': {
        'id': 'bpr_alpha',
        'rotulo': 'Alfa da função BPR',
        'unidade': '',
        'tipo': float,
        'default': 0.15,
        'campos_candidatos': ['bpr_alpha', 'alpha_bpr'],
    },
    'bpr_beta': {
        'id': 'bpr_beta',
        'rotulo': 'Beta da função BPR',
        'unidade': '',
        'tipo': float,
        'default': 4.0,
        'campos_candidatos': ['bpr_beta', 'beta_bpr'],
    },
    'capacidade': {
        'id': 'capacidade',
        'rotulo': 'Capacidade por sentido (0 = HCM)',
        'unidade': 'veíc/h',
        'tipo': float,
        'default': 0.0,
        'campos_candidatos': ['capacidade', 'capacity', 'cap', 'capacidade_vph'],
    },
    'tempo_livre': {
        'id': 'tempo_livre',
        'rotulo': 'Tempo de fluxo livre (0 = comprimento ÷ FFS)',
        'unidade': 'min',
        'tipo': float,
        'default': 0.0,
        'campos_candidatos': ['tempo_livre', 'free_flow_time', 'fft', 't0'],
    },
    'mao_unica': {
        'id': 'mao_unica',
        'rotulo': 'Mão única (sentido da geometria)',
        'unidade': '',
        'tipo': bool,
        'default': False,
        'campos_candidatos': ['mao_unica', 'oneway', 'one_way', 'sentido_unico'],
    },
}


def _coerce_value(raw_val, target_type):
    """Converte valor bruto para o tipo especificado."""
    if target_type == bool:
        if isinstance(raw_val, bool):
            return raw_val
        if not isinstance(raw_val, str):
            return bool(raw_val)
        s = raw_val.strip().lower()
        if s in ('true', '1', 'sim', 's', 'yes', 'y', 't', 'pavimentado', 'urbano'):
            return True
        if s in ('false', '0', 'nao', 'não', 'nã', 'n', 'no', 'f', 'rural', 'nao pavimentado'):
            return False
        raise ValueError(f"Valor booleano desconhecido: {raw_val!r}")
    if target_type == int:
        return int(float(raw_val))
    if target_type == float:
        return float(raw_val)
    if target_type == str:
        return str(raw_val)
    return raw_val


def _get_attribute_from_feature(feature, candidates):
    """Busca valor em uma feição (dict ou QgsFeature) a partir dos campos candidatos."""
    if feature is None:
        return None, False

    # Se for dicionário
    if isinstance(feature, dict):
        # Busca exata
        for cand in candidates:
            if cand in feature and feature[cand] is not None and feature[cand] != "":
                return feature[cand], True
        # Busca case-insensitive
        feat_lower = {k.lower(): v for k, v in feature.items() if v is not None and v != ""}
        for cand in candidates:
            if cand.lower() in feat_lower:
                return feat_lower[cand.lower()], True
        return None, False

    # Se for QgsFeature ou objeto com método attribute/fields
    fields_list = []
    if hasattr(feature, "fields") and callable(feature.fields):
        fields_list = [f.name() for f in feature.fields()]

    if fields_list:
        fields_lower = {f.lower(): f for f in fields_list}
        for cand in candidates:
            if cand.lower() in fields_lower:
                real_field = fields_lower[cand.lower()]
                val = feature.attribute(real_field)
                if val is not None and val != "" and str(val) != "NULL":
                    return val, True

    # Tenta acesso genérico por chave / atributo
    for cand in candidates:
        if hasattr(feature, cand):
            val = getattr(feature, cand)
            if val is not None and val != "" and not callable(val):
                return val, True
        try:
            val = feature[cand]
            if val is not None and val != "" and str(val) != "NULL":
                return val, True
        except (KeyError, IndexError, TypeError):
            # Candidato ausente no container ou objeto não indexável
            continue

    return None, False


def _is_null(val):
    """True para None, string vazia e NULL do QGIS (QVariant nulo no Qt5)."""
    return val is None or val == "" or str(val) == "NULL"


def _feature_attrs(feature):
    """Atributos de uma feição (dict ou QgsFeature) como dict, sem os nulos."""
    if feature is None:
        return {}
    if isinstance(feature, dict):
        return {k: v for k, v in feature.items() if not _is_null(v)}
    if hasattr(feature, "fields") and callable(feature.fields):
        attrs = {}
        for fld in feature.fields():
            val = feature.attribute(fld.name())
            if not _is_null(val):
                attrs[fld.name()] = val
        return attrs
    return {}


def _classe(valores):
    """Classe da via (chave de PADRAO_POR_CLASSE) a partir da primeira passada."""
    if not valores.get('pavimentado', True):
        return 'nao_pavimentada'
    tipo = str(valores.get('tipo_segmento', '')).strip().lower()
    if tipo in _TIPOS_PISTA_DUPLA:
        return 'pista_dupla'
    return 'pista_simples_pavimentada'


def resolve(feature=None, overrides=None, field_map=None, complemento=None, defaults=None):
    """Resolve os valores e origens dos parâmetros para uma feição (D4).

    Cascata por parâmetro — a primeira etapa que dá valor vence; valor que
    não converte para o tipo do parâmetro faz a cascata seguir:

    1. ``overrides`` (parâmetros fixados) → ``'usuario'``;
    2. campo mapeado em ``field_map`` → ``'oficial'``;
    3. ``oficiais.traduz(atributos da feição)`` → ``'oficial'``;
    4. ``campos_candidatos`` na feição → ``'oficial'``;
    5. ``complemento``: ``oficiais.traduz`` e depois ``campos_candidatos`` →
       ``'complementar'``;
    6. ``defaults`` (valor onde não há dado) → ``'usuario'``;
    7. ``PADRAO_POR_CLASSE`` → ``'padrao'``;
    8. ``PARAMS[p]['default']`` → ``'padrao'``.

    Duas passadas: primeiro ``tipo_segmento``/``pavimentado`` (que definem a
    classe da etapa 7), depois o resto.

    Args:
        feature: dict ou QgsFeature da rodovia (ou None).
        overrides: dict de parâmetro -> valor fixado pelo usuário (ou None).
        field_map: dict de parâmetro -> nome do campo mapeado na camada (ou None).
        complemento: dict (ou feição) de atributos da camada complementar (ou None).
        defaults: dict de parâmetro -> valor onde não há dado (ou None).

    Returns:
        tuple: (valores, origens) onde origens[p] em
            {'oficial', 'complementar', 'padrao', 'usuario'}.
    """
    # Import local: `oficiais` importa `params` no topo (D2).
    from . import oficiais

    overrides = overrides or {}
    field_map = field_map or {}
    defaults = defaults or {}
    feat_attrs = _feature_attrs(feature)
    # Coluna com o próprio id do parâmetro já é valor padronizado (malha D3):
    # a tradução não a reinterpreta (ex.: `lanes` por sentido não é dividido
    # por 2 pela regra OSM de `lanes` total). Fica para a etapa 4.
    ids_na_feicao = {str(k).lower() for k in feat_attrs}
    traduzido = {p: v for p, v in oficiais.traduz(feat_attrs).items()
                 if p not in ids_na_feicao}
    compl_attrs = _feature_attrs(complemento)
    compl_traduzido = oficiais.traduz(compl_attrs)

    valores = {}
    origens = {}

    def _resolve_param(param_id, spec):
        tipo = spec['tipo']
        etapas = []
        # 1. Fixado pelo usuário
        if overrides.get(param_id) is not None:
            etapas.append(('usuario', overrides[param_id]))
        # 2. Campo mapeado
        if field_map.get(param_id):
            val, found = _get_attribute_from_feature(feature, [field_map[param_id]])
            if found:
                etapas.append(('oficial', val))
        # 3. Tradução dos atributos brutos da feição
        if traduzido.get(param_id) is not None:
            etapas.append(('oficial', traduzido[param_id]))
        # 4. Candidatos na feição
        val, found = _get_attribute_from_feature(feature, spec['campos_candidatos'])
        if found:
            etapas.append(('oficial', val))
        # 5. Camada complementar: tradução, depois candidatos
        if compl_traduzido.get(param_id) is not None:
            etapas.append(('complementar', compl_traduzido[param_id]))
        val, found = _get_attribute_from_feature(compl_attrs, spec['campos_candidatos'])
        if found:
            etapas.append(('complementar', val))
        # 6. Valor onde não há dado
        if defaults.get(param_id) is not None:
            etapas.append(('usuario', defaults[param_id]))

        for origem, bruto in etapas:
            try:
                return _coerce_value(bruto, tipo), origem
            except (ValueError, TypeError):
                continue

        # 7. Padrão por classe
        if param_id not in _PRIMEIRA_PASSADA:
            por_classe = PADRAO_POR_CLASSE[_classe(valores)]
            if param_id in por_classe:
                return por_classe[param_id], 'padrao'
        # 8. Padrão do catálogo
        return spec['default'], 'padrao'

    for passada in (True, False):
        for param_id, spec in PARAMS.items():
            if (param_id in _PRIMEIRA_PASSADA) != passada:
                continue
            valores[param_id], origens[param_id] = _resolve_param(param_id, spec)

    # Devolve na ordem do catálogo
    valores = {p: valores[p] for p in PARAMS}
    origens = {p: origens[p] for p in PARAMS}
    return valores, origens
