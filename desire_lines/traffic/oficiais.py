# coding=utf-8
"""Mapeamento de atributos de fontes oficiais para parâmetros HCM (D2).

Este módulo concentra as regras de tradução de atributos de bases oficiais
(como DER-SP e DNIT) e colaborativas (como OSM) para os parâmetros
padronizados de capacidade e identificação de trechos.

Módulo em Python puro, sem dependências externas.
"""

import unicodedata

CAMPOS_CAPACIDADE = (
    'tipo_segmento',
    'lanes',
    'pavimentado',
    'urbano',
    'largura_faixa',
    'largura_acostamento',
    'terreno',
    'pct_veic_pesados',
    'vel_livre',
    'phf',
    'pct_no_passing',
    'access_density',
    'directional_split',
    'mao_unica',
)

IDENTIFICACAO = {
    'dnit_snv': {
        'rodovia': 'Codigo_BR',
        'codigo_trecho': 'Codigo_SNV',
        'km_ini': 'Quilometragem_Inicio',
        'km_fim': 'Quilometragem_Fim',
        'administracao': 'Administracao',
    },
    'der_sp_rodovias': {
        'rodovia': 'Rodovia',
        'codigo_trecho': 'Subtrecho',
        'km_ini': 'KmInicial',
        'km_fim': 'KmFinal',
        'administracao': 'Administra',
    },
}

ESQUEMA_PADRONIZADO = {
    'fonte': 'String',
    'ajuste': 'String',
    'rodovia': 'String',
    'codigo_trecho': 'String',
    'km_ini': 'Real',
    'km_fim': 'Real',
    'administracao': 'String',
    'tipo_segmento': 'String',
    'lanes': 'Integer',
    'pavimentado': 'Integer',
    'urbano': 'Integer',
    'largura_faixa': 'Real',
    'largura_acostamento': 'Real',
    'terreno': 'String',
    'pct_veic_pesados': 'Real',
    'vel_livre': 'Real',
    'phf': 'Real',
    'pct_no_passing': 'Real',
    'access_density': 'Real',
    'directional_split': 'Real',
    'mao_unica': 'Integer',
}

_REGRAS_PISTA = {
    'dup': {'tipo_segmento': 'pista_dupla', 'pavimentado': True},
    'pav': {'tipo_segmento': '2_faixas', 'pavimentado': True},
    'eod': {'tipo_segmento': '2_faixas', 'pavimentado': True},
    'imp': {'tipo_segmento': '2_faixas', 'pavimentado': False},
    'eop': {'tipo_segmento': '2_faixas', 'pavimentado': False},
    'len': {'tipo_segmento': '2_faixas', 'pavimentado': False},
}

_REGRAS_ONEWAY = {
    'yes': {'mao_unica': True},
    'true': {'mao_unica': True},
    '1': {'mao_unica': True},
    'no': {'mao_unica': False},
    'false': {'mao_unica': False},
    '0': {'mao_unica': False},
}

_REGRAS_PERIMETRO = {
    'sim': {'urbano': True},
    's': {'urbano': True},
    'nao': {'urbano': False},
    'n': {'urbano': False},
}

REGRAS = {
    'TipoPista': _REGRAS_PISTA,
    'Superficie_Federal': _REGRAS_PISTA,
    'PerimetroU': _REGRAS_PERIMETRO,
    'tipopista': _REGRAS_PISTA,
    'superficie_federal': _REGRAS_PISTA,
    'perimetrou': _REGRAS_PERIMETRO,
    'oneway': _REGRAS_ONEWAY,
}


def _normaliza_str(val):
    """Normaliza texto para comparação: minúsculas, sem espaços e sem acentos."""
    if val is None:
        return ''
    if not isinstance(val, str):
        val = str(val)
    val = val.strip().lower()
    val = unicodedata.normalize('NFKD', val)
    return ''.join(c for c in val if not unicodedata.combining(c))


def traduz(attrs):
    """Traduz atributos brutos de fontes oficiais para parâmetros do HCM (D2).

    A busca de campo não diferencia maiúsculas de minúsculas.
    Os valores são normalizados (sem caixa, sem espaços e sem acentos).
    Valores desconhecidos ou nulos não geram tradução.

    Args:
        attrs (dict): Dicionário de atributos brutos.

    Returns:
        dict: Dicionário contendo os parâmetros traduzidos.
    """
    if not isinstance(attrs, dict):
        return {}

    attrs_norm = {}
    for k, v in attrs.items():
        if k is not None:
            attrs_norm[str(k).strip().lower()] = v

    res = {}

    # 1. TipoPista / Superficie_Federal
    for fld in ('tipopista', 'superficie_federal'):
        if fld in attrs_norm and attrs_norm[fld] is not None:
            v_norm = _normaliza_str(attrs_norm[fld])
            if v_norm in _REGRAS_PISTA:
                res.update(_REGRAS_PISTA[v_norm])
                break

    # 2. PerimetroU
    if 'perimetrou' in attrs_norm and attrs_norm['perimetrou'] is not None:
        v_norm = _normaliza_str(attrs_norm['perimetrou'])
        if v_norm.startswith('s'):
            res['urbano'] = True
        elif v_norm.startswith('n'):
            res['urbano'] = False

    # 3. oneway
    norm_oneway = None
    if 'oneway' in attrs_norm and attrs_norm['oneway'] is not None:
        norm_oneway = _normaliza_str(attrs_norm['oneway'])
        if norm_oneway in ('yes', 'true', '1'):
            res['mao_unica'] = True
        elif norm_oneway in ('no', 'false', '0'):
            res['mao_unica'] = False
        elif norm_oneway == '-1':
            pass

    # 4. lanes
    if 'lanes' in attrs_norm and attrs_norm['lanes'] is not None:
        v_lanes = attrs_norm['lanes']
        try:
            l_int = int(float(str(v_lanes).strip()))
            if l_int > 0:
                if norm_oneway in ('yes', 'true', '1'):
                    res['lanes'] = l_int
                else:
                    res['lanes'] = max(1, l_int // 2)
        except (ValueError, TypeError):
            pass

    # 5. maxspeed
    if 'maxspeed' in attrs_norm and attrs_norm['maxspeed'] is not None:
        s_speed = str(attrs_norm['maxspeed']).strip().lower()
        if s_speed.endswith('km/h'):
            s_speed = s_speed[:-4].strip()
        elif s_speed.endswith('kmh'):
            s_speed = s_speed[:-3].strip()
        try:
            limite = float(s_speed)
            if limite > 0:
                vel = (limite + 8) if limite >= 80 else (limite + 11)
                if vel.is_integer():
                    vel = int(vel)
                res['vel_livre'] = vel
        except (ValueError, TypeError):
            pass

    return res


def padroniza(attrs, fonte_id=None):
    """Padroniza atributos de uma feição para o esquema de 21 colunas do plugin (D2).

    Devolve exatamente todas as chaves de ESQUEMA_PADRONIZADO, com None onde não há dado.

    Args:
        attrs (dict): Dicionário de atributos brutos da feição.
        fonte_id (str | None): Identificador da fonte (ex.: 'der_sp_rodovias', 'dnit_snv').

    Returns:
        dict: Dicionário com todas as 21 chaves padronizadas.
    """
    if not isinstance(attrs, dict):
        attrs = {}

    attrs_norm = {}
    for k, v in attrs.items():
        if k is not None:
            attrs_norm[str(k).strip().lower()] = v

    res = {k: None for k in ESQUEMA_PADRONIZADO}

    # 1. fonte e ajuste
    if 'fonte' in attrs_norm and attrs_norm['fonte'] is not None:
        res['fonte'] = attrs_norm['fonte']
    elif fonte_id is not None:
        res['fonte'] = fonte_id

    if 'ajuste' in attrs_norm and attrs_norm['ajuste'] is not None:
        res['ajuste'] = attrs_norm['ajuste']

    # 2. Identificação segundo o id da fonte
    if fonte_id in IDENTIFICACAO:
        mapping = IDENTIFICACAO[fonte_id]
        for campo_padrao, campo_fonte in mapping.items():
            cf_norm = campo_fonte.strip().lower()
            if cf_norm in attrs_norm:
                val = attrs_norm[cf_norm]
                if val is not None:
                    if campo_padrao in ('km_ini', 'km_fim'):
                        try:
                            res[campo_padrao] = float(val)
                        except (ValueError, TypeError):
                            res[campo_padrao] = None
                    else:
                        s = str(val).strip()
                        res[campo_padrao] = s if s != '' else None

    # 3. Capacidade
    trad = traduz(attrs)
    for param in CAMPOS_CAPACIDADE:
        if param in trad and trad[param] is not None:
            res[param] = trad[param]
        elif param in attrs_norm and attrs_norm[param] is not None:
            res[param] = attrs_norm[param]

    return res
