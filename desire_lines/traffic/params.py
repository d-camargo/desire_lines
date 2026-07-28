# coding=utf-8
"""Catálogo declarativo de parâmetros e resolução de valores/origens (D7)."""

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
}


def _coerce_value(raw_val, target_type):
    """Converte valor bruto para o tipo especificado."""
    if target_type == bool:
        if isinstance(raw_val, bool):
            return raw_val
        s = str(raw_val).strip().lower()
        if s in ('true', '1', 'sim', 's', 'yes', 'y', 'pavimentado', 'urbano'):
            return True
        if s in ('false', '0', 'nao', 'não', 'n', 'no', 'rural', 'nao pavimentado'):
            return False
        return bool(raw_val)
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
        try:
            fields_list = [f.name() for f in feature.fields()]
        except Exception:
            fields_list = []

    if fields_list:
        fields_lower = {f.lower(): f for f in fields_list}
        for cand in candidates:
            if cand.lower() in fields_lower:
                real_field = fields_lower[cand.lower()]
                try:
                    val = feature.attribute(real_field)
                    if val is not None and val != "" and str(val) != "NULL":
                        return val, True
                except Exception:
                    pass

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
        except Exception:
            pass

    return None, False


def resolve(feature=None, overrides=None):
    """Resolve os valores e origens dos parâmetros para uma feição.

    Args:
        feature: dict ou QgsFeature da rodovia (ou None).
        overrides: dict de parâmetro -> valor sobrescrito pelo usuário (ou None).

    Returns:
        tuple: (valores, origens) onde origens[p] em {'oficial', 'padrao', 'usuario'}.
    """
    if overrides is None:
        overrides = {}

    valores = {}
    origens = {}

    for param_id, spec in PARAMS.items():
        # 1. Usuário sobrescreveu
        if param_id in overrides and overrides[param_id] is not None:
            try:
                valores[param_id] = _coerce_value(overrides[param_id], spec['tipo'])
                origens[param_id] = 'usuario'
                continue
            except (ValueError, TypeError):
                pass

        # 2. Dado oficial na feição
        val, found = _get_attribute_from_feature(feature, spec['campos_candidatos'])
        if found:
            try:
                valores[param_id] = _coerce_value(val, spec['tipo'])
                origens[param_id] = 'oficial'
                continue
            except (ValueError, TypeError):
                pass

        # 3. Padrão
        valores[param_id] = spec['default']
        origens[param_id] = 'padrao'

    return valores, origens
