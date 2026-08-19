# coding=utf-8
"""Procedimentos HCM para cálculo de capacidade rodoviária (HCM 6ª ed.).

Este módulo implementa cálculos de capacidade para rodovias em Python puro.
"""

# Equivalentes de automóveis para veículos pesados (E_T) por tipo de terreno
# HCM 6ª ed. Cap. 15 (Two-Lane Highways)
TERRAIN_ET = {
    'plano': 1.5,
    'ondulado': 2.5,
    'montanhoso': 4.5,
    'level': 1.5,
    'rolling': 2.5,
    'mountainous': 4.5,
}

# Capacidades base para rodovia de pista simples (2 faixas, 1 por sentido)
BASE_TWO_LANE_DIRECTIONAL_CAPACITY = 1700.0  # pc/h por sentido
BASE_TWO_LANE_TOTAL_CAPACITY = 3200.0        # pc/h total (somando os dois sentidos)

# Capacidade base por faixa (pc/h/faixa) para segmento básico de pista dupla /
# multilane e freeway, em função da velocidade de fluxo livre (FFS).
# HCM 6ª ed. Cap. 12 (Basic Freeway/Multilane Segments), limiares de FFS
# convertidos de mph (75/70/65/60/55) para km/h.
BASE_MULTILANE_FREEWAY_CAPACITY_BY_FFS = (
    (120.0, 2400.0),
    (112.0, 2400.0),
    (105.0, 2350.0),
    (97.0, 2300.0),
    (88.5, 2250.0),
)

# Faixas de v/c para o LOS aproximado (ver D3 em docs/referencia/metodos.md): o LOS real
# do HCM sai de densidade/follower density, que exigem mais entrada do que há
# por arco; aqui o v/c serve apenas para ranquear gargalos.
LOS_VC_THRESHOLDS = (
    (0.35, 'A'),
    (0.55, 'B'),
    (0.75, 'C'),
    (0.90, 'D'),
    (1.00, 'E'),
)


def get_et(terrain):
    """Obtém o equivalente de veículo pesado (E_T) para o tipo de terreno.

    Args:
        terrain (str | float | int): Nome do terreno ('plano', 'ondulado', 'montanhoso')
            ou valor numérico direto de E_T.

    Returns:
        float: Valor de E_T.
    """
    if isinstance(terrain, (int, float)):
        return float(terrain)
    if not terrain:
        return TERRAIN_ET['ondulado']

    t_str = str(terrain).strip().lower()
    return TERRAIN_ET.get(t_str, TERRAIN_ET['ondulado'])


def heavy_vehicle_factor(pct_hv, et):
    """Calcula o fator de ajuste para veículos pesados (f_HV).

    Fórmula HCM: f_HV = 1 / (1 + P_T * (E_T - 1))

    Args:
        pct_hv (float): Percentual de veículos pesados (ex: 20.0 para 20%, ou 0.20 se <= 1.0).
        et (float): Equivalente de veículo pesado (E_T).

    Returns:
        float: Fator f_HV (<= 1.0).
    """
    pct_val = float(pct_hv) if pct_hv is not None else 0.0
    if pct_val < 0.0:
        pct_val = 0.0

    # Suporta percentual 0..100 (ex: 20.0) ou fração 0..1 (ex: 0.20)
    p_t = pct_val / 100.0 if pct_val > 1.0 else pct_val

    et_val = float(et) if et is not None else 1.0
    if et_val < 1.0:
        et_val = 1.0

    denom = 1.0 + p_t * (et_val - 1.0)
    if denom <= 0:
        return 1.0

    return 1.0 / denom


def two_lane_capacity(pct_hv=20.0, terrain='ondulado', phf=0.92, directional_split=50.0):
    """Calcula a capacidade de rodovia de pista simples (2 faixas) em veíc/h por sentido.

    HCM 6ª ed. Cap. 15:
    - Capacidade base por sentido: 1700 pc/h
    - Teto de capacidade total (dois sentidos): 3200 pc/h
    - Capacidade direcional base = min(1700, 3200 * d) pc/h, onde d é a fração direcional
    - Capacidade em veíc/h por sentido = c_base_d * f_HV * PHF

    Args:
        pct_hv (float): Percentual de veículos pesados (padrão 20.0).
        terrain (str | float): Terreno ('plano', 'ondulado', 'montanhoso') ou E_T direto.
        phf (float): Fator de Hora de Pico (padrão 0.92).
        directional_split (float): Divisão direcional em % para o sentido analisado (padrão 50.0).

    Returns:
        float: Capacidade em veículos por hora por sentido (veíc/h/sentido).
    """
    ds_val = float(directional_split) if directional_split is not None else 50.0
    split_frac = ds_val / 100.0 if ds_val > 1.0 else ds_val
    if split_frac <= 0.0:
        split_frac = 0.5
    elif split_frac > 1.0:
        split_frac = 1.0

    base_dir_from_total = BASE_TWO_LANE_TOTAL_CAPACITY * split_frac
    c_base_d = min(BASE_TWO_LANE_DIRECTIONAL_CAPACITY, base_dir_from_total)

    et = get_et(terrain)
    f_hv = heavy_vehicle_factor(pct_hv, et)

    phf_val = float(phf) if phf is not None else 1.0
    if phf_val <= 0:
        phf_val = 1.0

    return c_base_d * f_hv * phf_val


def base_capacity_per_lane(ffs):
    """Obtém a capacidade base por faixa (pc/h/faixa) a partir do FFS.

    HCM 6ª ed. Cap. 12: a capacidade cai por faixas de velocidade de fluxo
    livre; abaixo do menor limiar tabelado, usa-se o menor valor (sem
    extrapolar para fora da faixa coberta pelo HCM).

    Args:
        ffs (float): Velocidade de fluxo livre em km/h.

    Returns:
        float: Capacidade base em pc/h/faixa.
    """
    ffs_val = float(ffs) if ffs is not None else 0.0

    for threshold, capacity in BASE_MULTILANE_FREEWAY_CAPACITY_BY_FFS:
        if ffs_val >= threshold:
            return capacity

    return BASE_MULTILANE_FREEWAY_CAPACITY_BY_FFS[-1][1]


def multilane_freeway_capacity(lanes=2, pct_hv=20.0, terrain='ondulado', phf=0.92, ffs=110.0):
    """Calcula a capacidade de segmento básico de pista dupla/multilane e freeway.

    HCM 6ª ed. Cap. 12:
    - Capacidade base por faixa depende do FFS (ver `base_capacity_per_lane`).
    - Capacidade por faixa = c_base_faixa * f_HV * PHF
    - Capacidade por sentido = capacidade por faixa * número de faixas do sentido

    Args:
        lanes (int): Número de faixas por sentido (padrão 2).
        pct_hv (float): Percentual de veículos pesados (padrão 20.0).
        terrain (str | float): Terreno ('plano', 'ondulado', 'montanhoso') ou E_T direto.
        phf (float): Fator de Hora de Pico (padrão 0.92).
        ffs (float): Velocidade de fluxo livre em km/h (padrão 110.0).

    Returns:
        float: Capacidade em veículos por hora por sentido (veíc/h/sentido).
    """
    lanes_val = int(lanes) if lanes else 1
    if lanes_val < 1:
        lanes_val = 1

    et = get_et(terrain)
    f_hv = heavy_vehicle_factor(pct_hv, et)

    phf_val = float(phf) if phf is not None else 1.0
    if phf_val <= 0:
        phf_val = 1.0

    c_base_faixa = base_capacity_per_lane(ffs)

    return c_base_faixa * f_hv * phf_val * lanes_val


def level_of_service(vc):
    """Obtém o nível de serviço (LOS) aproximado a partir da razão v/c.

    Aproximação por faixas de v/c (ver D3 em docs/referencia/metodos.md), não por
    densidade: A ≤ 0,35; B ≤ 0,55; C ≤ 0,75; D ≤ 0,90; E ≤ 1,00; F > 1,00.

    Args:
        vc (float): Razão volume/capacidade (v/c).

    Returns:
        str: Letra do LOS ('A' a 'F').
    """
    vc_val = float(vc) if vc is not None else 0.0

    for threshold, los in LOS_VC_THRESHOLDS:
        if vc_val <= threshold:
            return los

    return 'F'


def _get_val(values, keys, default):
    """Busca a primeira chave existente em values com valor não nulo."""
    if not isinstance(values, dict):
        return default
    for k in keys:
        if k in values and values[k] is not None:
            return values[k]
    return default


def segment_capacity(values=None):
    """Calcula a capacidade do segmento despachando para o procedimento HCM adequado.

    Determina o tipo de segmento (pista simples / 2 faixas vs pista dupla / multilane / freeway)
    a partir do dicionário de parâmetros e despacha para `two_lane_capacity` ou
    `multilane_freeway_capacity`.

    Args:
        values (dict | None): Dicionário com os parâmetros do segmento (ex: retornado por
            `params.resolve` ou construído manualmente).

    Returns:
        tuple: (capacidade, escopo) onde capacidade é float em veículos por hora por sentido
            (veíc/h/sentido) e escopo é 'urbano' se for travessia/trecho urbano, senão 'rodoviario'.
    """
    if values is None:
        values = {}

    pct_hv = _get_val(values, ['pct_veic_pesados', 'pct_hv'], 20.0)
    terrain = _get_val(values, ['terreno', 'terrain'], 'ondulado')
    phf = _get_val(values, ['phf'], 0.92)

    tipo = str(_get_val(values, ['tipo_segmento', 'tipo_pista', 'pista'], '')).strip().lower()
    lanes_val = _get_val(values, ['lanes', 'num_faixas', 'faixas'], None)

    is_multilane = False
    if tipo in ('multilane', 'freeway', 'pista_dupla', 'duplicada', 'pista dupla', 'dupla', 'multifaixa'):
        is_multilane = True
    elif tipo in ('2_faixas', 'pista_simples', 'simples', 'two_lane', '2 faixas', 'pista simples'):
        is_multilane = False
    elif lanes_val is not None:
        try:
            is_multilane = int(lanes_val) > 1
        except (ValueError, TypeError):
            is_multilane = False

    if is_multilane:
        lanes = int(lanes_val) if lanes_val is not None else 2
        ffs = _get_val(values, ['vel_livre', 'ffs'], 110.0)
        cap = multilane_freeway_capacity(
            lanes=lanes,
            pct_hv=pct_hv,
            terrain=terrain,
            phf=phf,
            ffs=ffs,
        )
    else:
        directional_split = _get_val(values, ['directional_split', 'split_dir', 'divisao_direcional'], 50.0)
        cap = two_lane_capacity(
            pct_hv=pct_hv,
            terrain=terrain,
            phf=phf,
            directional_split=directional_split,
        )

    urbano_val = _get_val(values, ['urbano', 'trecho_urbano', 'travessia_urbana', 'tp_trecho', 'is_urbano'], False)
    if isinstance(urbano_val, str):
        is_urbano = urbano_val.strip().lower() in ('true', '1', 'sim', 's', 'yes', 'y', 'urbano')
    else:
        is_urbano = bool(urbano_val)

    escopo = 'urbano' if is_urbano else 'rodoviario'

    return cap, escopo


