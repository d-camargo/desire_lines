# coding=utf-8
"""Módulo de costura de pontas soltas, limpeza e unificação de esquema em Python puro (D4, D5, D6).

Este módulo NÃO depende nem importa `qgis` para permitir execução e testes
isolados e rápidos da lógica de higienização de linhas e resolução de esquema.
"""

from collections import defaultdict
import math

from .network import node_key, _project_point_on_polyline, _split_polyline


def _pt_coords(pt):
    """Extrai coordenadas (float x, float y) de uma representação de ponto."""
    if hasattr(pt, 'x') and hasattr(pt, 'y'):
        x = pt.x() if callable(pt.x) else pt.x
        y = pt.y() if callable(pt.y) else pt.y
    else:
        x, y = pt[0], pt[1]
    return float(x), float(y)


def _extract_points(linha):
    """Extrai lista de coordenadas (x, y) de uma linha.

    Suporta dicionários com chaves 'pts', 'points', 'geometry', 'coords',
    objetos com esses atributos ou listas/tuplas de pontos.
    """
    if linha is None:
        return None

    raw_pts = None
    if isinstance(linha, dict):
        for k in ('pts', 'points', 'geometry', 'coords', 'coordinates'):
            if k in linha:
                raw_pts = linha[k]
                break
    elif hasattr(linha, 'pts'):
        raw_pts = linha.pts
    elif hasattr(linha, 'points'):
        raw_pts = linha.points
    elif hasattr(linha, 'geometry'):
        raw_pts = linha.geometry
    elif isinstance(linha, (list, tuple)):
        if linha and isinstance(linha[0], (list, tuple)) and len(linha[0]) >= 2:
            raw_pts = linha
        elif not linha:
            raw_pts = []

    if raw_pts is None:
        return None

    pts = []
    for p in raw_pts:
        try:
            pts.append(_pt_coords(p))
        except (IndexError, TypeError, ValueError):
            continue
    return pts


def _calculate_length_m(points):
    """Calcula o comprimento total em metros de uma lista de pontos (CRS métrico)."""
    if not points or len(points) < 2:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def _canonical_geom_key(pts, precision=3):
    """Gera chave canônica independente do sentido com coordenadas arredondadas (D5)."""
    fwd = tuple((round(x, precision), round(y, precision)) for x, y in pts)
    rev = tuple(reversed(fwd))
    return min(fwd, rev)


def _extract_attrs(linha):
    """Extrai dicionário de atributos de uma linha."""
    if not isinstance(linha, dict):
        if hasattr(linha, 'attrs') and isinstance(linha.attrs, dict):
            return linha.attrs
        if hasattr(linha, 'properties') and isinstance(linha.properties, dict):
            return linha.properties
        return {}
    if 'attrs' in linha and isinstance(linha['attrs'], dict):
        return linha['attrs']
    if 'properties' in linha and isinstance(linha['properties'], dict):
        return linha['properties']
    if 'atributos' in linha and isinstance(linha['atributos'], dict):
        return linha['atributos']
    return {k: v for k, v in linha.items() if k not in ('pts', 'points', 'geometry', 'coords', 'coordinates')}


def _norm_str(v):
    """Normaliza texto removendo espaços e convertendo para minúsculas."""
    if v is None:
        return ""
    return "".join(str(v).split()).lower()


def _matches_excluir(attrs, excluir):
    """Verifica se os atributos batem com o critério excluir sem caixa/espaço (D5)."""
    if not excluir or not attrs:
        return False
    if isinstance(excluir, dict):
        criterios = [excluir]
    elif isinstance(excluir, (list, tuple)):
        criterios = list(excluir)
    else:
        return False

    for crit in criterios:
        if not isinstance(crit, dict):
            continue
        campo = crit.get('campo')
        if not campo:
            continue
        valores = crit.get('valores')
        if valores is None:
            valores = crit.get('valor')
        if valores is None:
            valores = crit.get('values')
        if valores is None:
            continue
        if isinstance(valores, (str, int, float)):
            valores = [valores]

        val = None
        if campo in attrs:
            val = attrs[campo]
        else:
            norm_campo = _norm_str(campo)
            for k, v in attrs.items():
                if _norm_str(k) == norm_campo:
                    val = v
                    break
            else:
                continue

        if val is None:
            continue

        norm_val = _norm_str(val)
        norm_valores = {_norm_str(x) for x in valores}
        if norm_val in norm_valores:
            return True

    return False


def limpa_linhas(linhas, excluir=None, precision=3):
    """Descarta linhas inválidas, trechos planejados e duplicatas exatas (D5).

    Regras de descarte:
    - Menos de 2 pontos (vazia ou 1 ponto);
    - Comprimento zero (pontos sobrepostos);
    - Trechos que batem no critério `excluir` (comparação sem caixa/espaços);
    - Duplicatas exatas dentro da fonte (coordenadas arredondadas a `precision` casas,
      independente do sentido de digitalização).

    Args:
        linhas (list): Lista de dicts/feições representando linhas.
        excluir (dict | list | None): Critério rede.excluir, ex.
            {"campo": "ds_superfi", "valores": ["PLA"]}.
        precision (int): Casas decimais para detecção de duplicatas (padrão 3).

    Returns:
        tuple: (mantidas, relatorio)
            mantidas (list): Linhas preservadas na ordem original.
            relatorio (dict): Contagens de linhas processadas e motivos de descarte.
    """
    if linhas is None:
        linhas = []

    total = len(linhas)
    mantidas = []

    count_menos_2_pontos = 0
    count_zero_length = 0
    count_excluir = 0
    count_duplicatas = 0

    seen_geoms = set()

    for linha in linhas:
        pts = _extract_points(linha)

        # 1. Menos de 2 pontos
        if pts is None or len(pts) < 2:
            count_menos_2_pontos += 1
            continue

        # 2. Comprimento zero
        length = _calculate_length_m(pts)
        if length <= 1e-9:
            count_zero_length += 1
            continue

        # 3. Filtro excluir
        attrs = _extract_attrs(linha)
        if _matches_excluir(attrs, excluir):
            count_excluir += 1
            continue

        # 4. Duplicata exata
        geom_key = _canonical_geom_key(pts, precision=precision)
        if geom_key in seen_geoms:
            count_duplicatas += 1
            continue

        seen_geoms.add(geom_key)
        mantidas.append(linha)

    removidas = total - len(mantidas)

    relatorio = {
        'total': total,
        'mantidas': len(mantidas),
        'removidas': removidas,
        'menos_2_pontos': count_menos_2_pontos,
        'zero_length': count_zero_length,
        'excluir': count_excluir,
        'duplicata': count_duplicatas,
    }

    return mantidas, relatorio


def uniao_campos(listas, incluir_base=True):
    """Calcula o esquema unificado de atributos para múltiplas fontes (D6).

    Args:
        listas (list): Lista de listas de tuplas (nome_campo, tipo_str),
            ex.: [[('campo1', 'Integer'), ('campo2', 'String')], ...].
        incluir_base (bool): Se True (padrão), inclui os campos base ('fonte', 'String')
            e ('ajuste', 'String') no início da lista.

    Returns:
        list: Lista de tuplas (nome_campo, tipo_str) ordenada pela primeira aparição.
            Em caso de conflito de tipo entre fontes, o tipo vira 'String'.
            Os campos 'fonte' e 'ajuste' não são duplicados.
    """
    if listas is None:
        listas = []

    # Se uma lista plana de tuplas foi passada por engano, encapsula em lista
    if listas and isinstance(listas[0], (tuple, list)) and len(listas[0]) == 2 and isinstance(listas[0][0], str):
        listas = [listas]

    resultado = []
    indices = {}  # norm_name -> index in resultado

    if incluir_base:
        for base_name in ('fonte', 'ajuste'):
            norm = base_name.lower()
            indices[norm] = len(resultado)
            resultado.append((base_name, 'String'))

    for lista in listas:
        if not lista:
            continue

        if isinstance(lista, dict):
            itens = lista.items()
        else:
            itens = lista

        for item in itens:
            if not item or len(item) < 2:
                continue
            nome, tipo = item[0], item[1]
            nome_str = str(nome)
            tipo_str = str(tipo)
            norm = nome_str.lower()

            if norm in indices:
                idx = indices[norm]
                nome_existente, tipo_existente = resultado[idx]

                # Campos base fonte/ajuste permanecem como String e não duplicam
                if norm in ('fonte', 'ajuste'):
                    continue

                # Conflito de tipo vira String
                if tipo_existente != tipo_str and tipo_existente.lower() != tipo_str.lower():
                    resultado[idx] = (nome_existente, 'String')
            else:
                indices[norm] = len(resultado)
                resultado.append((nome_str, tipo_str))

    return resultado


def converte_valor(val, tipo_str):
    """Converte um valor de atributo para o tipo unificado correspondente (D6).

    Se val for None, permanece None (NULL continua NULL).
    Se tipo_str for 'String', converte para str(val).
    """
    if val is None:
        return None
    if tipo_str == 'String':
        return str(val)
    if tipo_str in ('Integer', 'int'):
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    if tipo_str in ('Real', 'Double', 'float'):
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    return val


def _get_geom_key(linha):
    """Identifica o nome da chave geométrica usada no dicionário."""
    if isinstance(linha, dict):
        for k in ('pts', 'points', 'geometry', 'coords', 'coordinates'):
            if k in linha:
                return k
    return 'pts'


def _update_ajuste(d, novo_ajuste='costurada'):
    """Atualiza o atributo 'ajuste' caso presente no dicionário (D3, D4)."""
    if isinstance(d, dict) and 'ajuste' in d:
        atual = d.get('ajuste') or ''
        if novo_ajuste not in atual:
            d['ajuste'] = f"{atual}+{novo_ajuste}" if atual else novo_ajuste


def _pts_modified(p1, p2):
    """Verifica se as sequências de coordenadas diferem."""
    if not p1 or not p2 or len(p1) != len(p2):
        return True
    return any(a != b for a, b in zip(p1, p2))


def _grid_cell(pt, cell_size):
    """Calcula os índices inteiros de célula (cx, cy) para um ponto."""
    return int(math.floor(pt[0] / cell_size)), int(math.floor(pt[1] / cell_size))


def _grid_neighbors(cx, cy):
    """Gera as 9 células da vizinhança de (cx, cy)."""
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            yield cx + dx, cy + dy


def costura_extremidades(linhas, tol_m=30.0, precision=3):
    """Costura pontas soltas conectando-as a nós próximos ou gerando junções em T (D4).

    Utiliza grade espacial de células de lado `tol_m` para busca eficiente.
    Regras de prioridade:
    - Uma ponta é solta quando nenhuma outra ponta está a <= precision (node_key).
    - Prioridade 1: Snap nó-nó para ponta de outra linha a <= tol_m.
    - Prioridade 2: Snap em T na projeção ortogonal do interior de outra linha a <= tol_m,
      dividindo a outra linha no ponto projetado.
    - Pontas já conectadas nunca se movem.
    - Cruzamento de linhas sem ponta próxima não sofre divisão.
    - Atributos da linha dividida são preservados e copiados para os pedaços.

    Args:
        linhas (list): Lista de dicts {'pts': [(x, y), ...], ...} ou feições.
        tol_m (float): Tolerância máxima em metros para costura (padrão 30.0).
        precision (int): Casas decimais para identificação de nós (padrão 3).

    Returns:
        tuple: (linhas_saida, relatorio)
            linhas_saida (list): Linhas costuradas e divididas.
            relatorio (dict): Contagens de costuras nó-nó e em T.
    """
    if not linhas:
        return [], {
            'no_no': 0,
            't': 0,
            'total': 0,
            'costuradas': 0,
        }

    line_records = []
    for idx, item in enumerate(linhas):
        pts = _extract_points(item)
        if pts is None or len(pts) < 2:
            line_records.append({
                'idx': idx,
                'orig': item,
                'valid': False,
                'pts': [tuple(p) for p in pts] if pts else [],
                'geom_key': _get_geom_key(item),
            })
        else:
            line_records.append({
                'idx': idx,
                'orig': item,
                'valid': True,
                'pts': [tuple(p) for p in pts],
                'geom_key': _get_geom_key(item),
            })

    cell_size = max(float(tol_m), 1.0)

    # 1. Identificar nós conectados inicialmente (count > 1) e pontas soltas (count == 1)
    endpoint_keys = defaultdict(list)
    for rec in line_records:
        if not rec['valid']:
            continue
        i = rec['idx']
        k0 = node_key(rec['pts'][0], precision)
        k1 = node_key(rec['pts'][-1], precision)
        endpoint_keys[k0].append((i, 0))
        endpoint_keys[k1].append((i, -1))

    connected_endpoints = set()
    for k, ep_list in endpoint_keys.items():
        if len(ep_list) > 1:
            for ep in ep_list:
                connected_endpoints.add(ep)

    # 2. Grade de endpoints para busca espacial nó-nó
    grid_endpoints = defaultdict(list)
    for rec in line_records:
        if not rec['valid']:
            continue
        i = rec['idx']
        p0 = tuple(rec['pts'][0])
        p1 = tuple(rec['pts'][-1])
        grid_endpoints[_grid_cell(p0, cell_size)].append((i, 0))
        grid_endpoints[_grid_cell(p1, cell_size)].append((i, -1))

    # Identificar pares candidatos para snap nó-nó
    candidates_map = {}
    for rec in line_records:
        if not rec['valid']:
            continue
        i = rec['idx']
        for wa in (0, -1):
            ep_a = (i, wa)
            if ep_a in connected_endpoints:
                continue
            pt_a = tuple(rec['pts'][wa])
            cx, cy = _grid_cell(pt_a, cell_size)
            for ncx, ncy in _grid_neighbors(cx, cy):
                for ep_b in grid_endpoints.get((ncx, ncy), []):
                    j, wb = ep_b
                    if j == i:
                        continue
                    pt_b = tuple(line_records[j]['pts'][wb])
                    d = math.hypot(pt_a[0] - pt_b[0], pt_a[1] - pt_b[1])
                    if d <= tol_m:
                        pair_key = (min(ep_a, ep_b), max(ep_a, ep_b))
                        if pair_key not in candidates_map or d < candidates_map[pair_key]:
                            candidates_map[pair_key] = d

    sorted_candidates = sorted(
        [(d, ep1, ep2) for (ep1, ep2), d in candidates_map.items()],
        key=lambda x: x[0],
    )

    count_no_no = 0
    for d, ep_a, ep_b in sorted_candidates:
        conn_a = (ep_a in connected_endpoints)
        conn_b = (ep_b in connected_endpoints)
        if conn_a and conn_b:
            continue

        ia, wa = ep_a
        ib, wb = ep_b
        curr_pta = tuple(line_records[ia]['pts'][wa])
        curr_ptb = tuple(line_records[ib]['pts'][wb])
        curr_d = math.hypot(curr_pta[0] - curr_ptb[0], curr_pta[1] - curr_ptb[1])
        if curr_d > tol_m + 1e-9:
            continue

        if conn_a and not conn_b:
            line_records[ib]['pts'][wb] = curr_pta
            connected_endpoints.add(ep_b)
            count_no_no += 1
        elif not conn_a and conn_b:
            line_records[ia]['pts'][wa] = curr_ptb
            connected_endpoints.add(ep_a)
            count_no_no += 1
        else:
            if ia <= ib:
                line_records[ib]['pts'][wb] = curr_pta
            else:
                line_records[ia]['pts'][wa] = curr_ptb
            connected_endpoints.add(ep_a)
            connected_endpoints.add(ep_b)
            count_no_no += 1

    # 3. Grade de segmentos para busca espacial em T
    grid_segments = defaultdict(set)
    for rec in line_records:
        if not rec['valid']:
            continue
        j = rec['idx']
        pts_j = rec['pts']
        for s_idx in range(len(pts_j) - 1):
            p1 = pts_j[s_idx]
            p2 = pts_j[s_idx + 1]
            min_cx = int(math.floor(min(p1[0], p2[0]) / cell_size))
            max_cx = int(math.floor(max(p1[0], p2[0]) / cell_size))
            min_cy = int(math.floor(min(p1[1], p2[1]) / cell_size))
            max_cy = int(math.floor(max(p1[1], p2[1]) / cell_size))
            if (max_cx - min_cx + 1) * (max_cy - min_cy + 1) <= 100:
                for cx in range(min_cx, max_cx + 1):
                    for cy in range(min_cy, max_cy + 1):
                        grid_segments[(cx, cy)].add(j)
            else:
                seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                steps = max(1, int(math.ceil(seg_len / (cell_size * 0.5))))
                for step in range(steps + 1):
                    t = step / steps
                    sx = p1[0] + t * (p2[0] - p1[0])
                    sy = p1[1] + t * (p2[1] - p1[1])
                    scx, scy = _grid_cell((sx, sy), cell_size)
                    for ncx, ncy in _grid_neighbors(scx, scy):
                        grid_segments[(ncx, ncy)].add(j)

    splits_by_line = defaultdict(list)
    count_t = 0
    for rec in line_records:
        if not rec['valid']:
            continue
        i = rec['idx']
        for wa in (0, -1):
            ep = (i, wa)
            if ep in connected_endpoints:
                continue
            pt = tuple(rec['pts'][wa])
            cx, cy = _grid_cell(pt, cell_size)
            candidate_lines = set()
            for ncx, ncy in _grid_neighbors(cx, cy):
                candidate_lines.update(grid_segments.get((ncx, ncy), set()))

            best_cand = None
            for j in candidate_lines:
                if j == i:
                    continue
                pts_j = line_records[j]['pts']
                proj = _project_point_on_polyline(pt, pts_j)
                if proj is None:
                    continue
                dist, s, (qx, qy) = proj
                len_j = _calculate_length_m(pts_j)
                if dist <= tol_m and 1e-3 < s < len_j - 1e-3:
                    if best_cand is None or dist < best_cand[0]:
                        node = (round(qx, precision), round(qy, precision))
                        best_cand = (dist, s, node, j)

            if best_cand is not None:
                best_dist, best_s, best_node, best_j = best_cand
                line_records[i]['pts'][wa] = best_node
                connected_endpoints.add(ep)
                splits_by_line[best_j].append((best_s, best_node))
                count_t += 1

    # 4. Construir linhas de saída preservando atributos
    linhas_saida = []
    for rec in line_records:
        if not rec['valid']:
            linhas_saida.append(rec['orig'])
            continue

        idx = rec['idx']
        orig = rec['orig']
        gk = rec['geom_key']
        pts = rec['pts']

        if idx in splits_by_line and splits_by_line[idx]:
            splits = sorted(splits_by_line[idx], key=lambda x: x[0])
            pieces = _split_polyline(pts, splits)
            for piece in pieces:
                piece_tuples = [tuple(p) for p in piece]
                if isinstance(orig, dict):
                    out = dict(orig)
                    out[gk] = piece_tuples
                    _update_ajuste(out, 'costurada')
                    linhas_saida.append(out)
                elif isinstance(orig, (list, tuple)):
                    linhas_saida.append(type(orig)(piece_tuples))
                else:
                    out = dict(_extract_attrs(orig))
                    out[gk] = piece_tuples
                    linhas_saida.append(out)
        else:
            pts_tuples = [tuple(p) for p in pts]
            if isinstance(orig, dict):
                out = dict(orig)
                out[gk] = pts_tuples
                if _pts_modified(orig.get(gk), pts_tuples):
                    _update_ajuste(out, 'costurada')
                linhas_saida.append(out)
            elif isinstance(orig, (list, tuple)):
                linhas_saida.append(type(orig)(pts_tuples))
            else:
                out = dict(_extract_attrs(orig))
                out[gk] = pts_tuples
                linhas_saida.append(out)

    relatorio = {
        'no_no': count_no_no,
        't': count_t,
        'total': len(linhas_saida),
        'costuradas': count_no_no + count_t,
    }

    return linhas_saida, relatorio
