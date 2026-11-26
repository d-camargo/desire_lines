# coding=utf-8
"""Núcleo de cálculo estatístico para calibração de modelos de tráfego.

Implementa a formulação do GEH, classificação em faixas normativas (DNIT),
agregação de volumes modelados em postos e cálculo de indicadores de aderência
(%RMSE e critério DNIT).

Módulo em Python puro, sem dependências de bibliotecas de SIG.
"""

import math

# Limites superiores para classificação de faixas de GEH:
# Faixa A: GEH < 5
# Faixa B: 5 <= GEH < 10
# Faixa C: 10 <= GEH < 12
# Faixa D: GEH >= 12
GEH_LIMITES = (5, 10, 12)

# Critérios DNIT para calibração da macrossimulação (% mínimo desejado)
# Faixa A >= 60% e Faixas A + B acumuladas >= 95%
DNIT_MIN_A = 0.60
DNIT_MIN_AB = 0.95


def geh(modelado, contado):
    """Calcula a estatística GEH para comparação entre volume modelado e contado.

    Fórmula:
        GEH = sqrt( 2 * (M - C)^2 / (M + C) )

    Args:
        modelado (float | int): Volume modelado (M).
        contado (float | int): Volume contado em campo (C).

    Returns:
        float: Valor da estatística GEH. Retorna 0.0 quando M + C == 0.

    Raises:
        ValueError: Se modelado ou contado forem valores negativos.
    """
    if modelado < 0 or contado < 0:
        raise ValueError(
            f"Volumes não podem ser negativos: modelado={modelado}, contado={contado}"
        )
    soma = modelado + contado
    if soma == 0:
        return 0.0
    dif = modelado - contado
    return math.sqrt(2.0 * (dif ** 2) / soma)


def faixa_geh(g):
    """Classifica o valor do GEH nas faixas normativas A, B, C ou D.

    Limites fechados à esquerda:
    - Faixa A: GEH < 5
    - Faixa B: 5 <= GEH < 10
    - Faixa C: 10 <= GEH < 12
    - Faixa D: GEH >= 12

    Args:
        g (float | int): Valor do GEH.

    Returns:
        str: Letra correspondente à faixa ('A', 'B', 'C' ou 'D').

    Raises:
        ValueError: Se g for negativo.
    """
    if g < 0:
        raise ValueError(f"GEH não pode ser negativo: {g}")
    if g < GEH_LIMITES[0]:
        return 'A'
    if g < GEH_LIMITES[1]:
        return 'B'
    if g < GEH_LIMITES[2]:
        return 'C'
    return 'D'


def volume_no_posto(candidatos, tol_m=1.0):
    """Calcula o volume modelado somado para um posto a partir dos trechos candidatos.

    Localiza o trecho com a menor distância ao posto e soma os volumes das
    feições pertencentes ao mesmo link_id cuja distância esteja dentro de tol_m
    da menor distância encontrada. Essa agregação captura os dois sentidos
    (fw + bw) do mesmo segmento viário e descarta trechos de outros links
    ou candidatos do mesmo link em posições afastadas.

    Args:
        candidatos (list[tuple[float, any, float]]): Lista de tuplas
            (dist_m, link_id, volume).
        tol_m (float): Tolerância máxima em metros acima da menor distância
            para considerar feições do mesmo link (padrão 1.0 m).

    Returns:
        float: Volume total somado no posto (0.0 se não houver candidatos).
    """
    if not candidatos:
        return 0.0

    min_cand = min(candidatos, key=lambda c: c[0])
    min_dist = min_cand[0]
    target_link_id = min_cand[1]

    total_volume = 0.0
    for dist_m, link_id, volume in candidatos:
        if link_id == target_link_id and (dist_m - min_dist) <= tol_m:
            if volume is not None:
                total_volume += float(volume)

    return float(total_volume)


def resumo(resultados):
    """Gera o resumo estatístico consolidado da calibração a partir dos postos.

    Args:
        resultados (list[dict]): Lista de dicionários por posto contendo ao menos
            as chaves 'contagem', 'modelado', 'geh' e 'faixa'. Postos com
            faixa == 'sem_link' não são incluídos no total de postos casados (n).

    Returns:
        dict: Dicionário contendo:
            - 'n' (int): Quantidade de postos casados avaliados.
            - 'n_sem_link' (int): Quantidade de postos sem trecho associado.
            - 'por_faixa' (dict[str, int]): Contagem de postos por faixa {'A': n, ...}.
            - 'pct_a' (float): Fração de postos na faixa A (0.0 a 1.0).
            - 'pct_ab' (float): Fração acumulada nas faixas A + B (0.0 a 1.0).
            - 'atende_dnit' (bool): Se cumpre o critério DNIT (>= 60% A e >= 95% A+B).
            - 'rmse_pct' (float | None): Percentual de erro médio quadrático
              (%RMSE = 100 * sqrt(Σ(M-C)^2 / n) / (ΣC / n)), ou None se n == 0
              ou se a soma das contagens for zero.
    """
    n_sem_link = 0
    casados = []

    for r in resultados or []:
        if r.get('faixa') == 'sem_link':
            n_sem_link += 1
        else:
            casados.append(r)

    n = len(casados)

    por_faixa = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for r in casados:
        f = r.get('faixa')
        if f in por_faixa:
            por_faixa[f] += 1
        elif f is not None:
            por_faixa[f] = por_faixa.get(f, 0) + 1

    if n == 0:
        return {
            'n': 0,
            'n_sem_link': n_sem_link,
            'por_faixa': por_faixa,
            'pct_a': 0.0,
            'pct_ab': 0.0,
            'atende_dnit': False,
            'rmse_pct': None,
        }

    pct_a = por_faixa['A'] / n
    pct_ab = (por_faixa['A'] + por_faixa['B']) / n
    atende_dnit = (pct_a >= DNIT_MIN_A) and (pct_ab >= DNIT_MIN_AB)

    sum_c = sum(float(r.get('contagem', 0.0) or 0.0) for r in casados)
    sum_sq_diff = sum(
        (float(r.get('modelado', 0.0) or 0.0) - float(r.get('contagem', 0.0) or 0.0)) ** 2
        for r in casados
    )

    if sum_c == 0.0:
        rmse_pct = None
    else:
        rmse = math.sqrt(sum_sq_diff / n)
        mean_c = sum_c / n
        rmse_pct = 100.0 * rmse / mean_c

    return {
        'n': n,
        'n_sem_link': n_sem_link,
        'por_faixa': por_faixa,
        'pct_a': pct_a,
        'pct_ab': pct_ab,
        'atende_dnit': atende_dnit,
        'rmse_pct': rmse_pct,
    }
