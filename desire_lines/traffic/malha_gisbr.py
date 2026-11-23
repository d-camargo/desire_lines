# coding=utf-8
"""Junção das malhas rodoviárias do GISBR (lado QGIS).

- `subtrai_sobreposicao` (D3): uma linha de fonte nova perde os trechos que
  já estão desenhados na malha de referência (fontes anteriores na ordem de
  precedência). Trabalha com `QgsGeometry` em CRS métrico (comprimentos e
  tolerâncias em metros).
- `baixar_malha` (D1, D3–D8): baixa as fontes rodoviárias da UF pelo GISBR,
  recorta, reprojeta, limpa, junta e costura, e devolve uma camada em memória.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)

from . import gisbr_bridge
from .merge import converte_valor, costura_extremidades, limpa_linhas, uniao_campos
from .outputs import _create_field
from ..aon import pick_metric_crs

TOL_SOBREPOSICAO_M = 20.0
MIN_SOBREPOSICAO_M = 100.0
MIN_PEDACO_M = 50.0
TOL_COSTURA_M = 30.0

# Tipo do campo (valor numérico comum a QVariant.Type e QMetaType.Type) ->
# nome usado por `merge.uniao_campos`; o que não estiver aqui vira String (D6).
_TIPO_CAMPO = {2: 'Integer', 3: 'Integer', 4: 'Integer64', 5: 'Integer64',
               6: 'Real'}
_TIPO_QGIS = {'Integer': 'int', 'Integer64': 'int64', 'Real': 'double'}

_EPS = 1e-6


def _partes_simples(geom):
    """Lista de partes simples de uma geometria (ela própria se não for multi)."""
    if geom.isMultipart() or geom.wkbType() == QgsWkbTypes.GeometryCollection:
        return [p for p in geom.asGeometryCollection() if not p.isEmpty()]
    return [geom]


def _intervalos_dentro(linha, zona):
    """Intervalos [a, b] (distância ao longo de `linha`) que caem dentro de `zona`.

    Intervalos contíguos são fundidos. `linha` deve ser parte simples.
    """
    inter = linha.intersection(zona)
    if inter.isNull() or inter.isEmpty():
        return []
    intervalos = []
    for parte in _partes_simples(inter):
        if parte.type() != QgsWkbTypes.LineGeometry:
            continue  # toque pontual na borda do buffer: comprimento zero
        for pts in (parte.asMultiPolyline() if parte.isMultipart() else [parte.asPolyline()]):
            if len(pts) < 2:
                continue
            a = linha.lineLocatePoint(QgsGeometry.fromPointXY(pts[0]))
            b = linha.lineLocatePoint(QgsGeometry.fromPointXY(pts[-1]))
            if a < 0 or b < 0:
                continue
            intervalos.append(sorted((a, b)))
    intervalos.sort()
    fundidos = []
    for a, b in intervalos:
        if fundidos and a <= fundidos[-1][1] + _EPS:
            fundidos[-1][1] = max(fundidos[-1][1], b)
        else:
            fundidos.append([a, b])
    return fundidos


def subtrai_sobreposicao(geoms_ref, geoms_novas, tol_m=TOL_SOBREPOSICAO_M,
                         min_sobrep_m=MIN_SOBREPOSICAO_M,
                         min_pedaco_m=MIN_PEDACO_M):
    """Subtrai das geometrias novas o que se sobrepõe à referência (D3).

    Para cada linha nova, os trechos que caem dentro do buffer `tol_m` da
    referência e têm comprimento >= `min_sobrep_m` são removidos; trechos
    menores (toque de entroncamento) ficam, sem corte. Pedaços restantes com
    menos de `min_pedaco_m` são descartados (fiapos). Só são bufferizadas as
    geometrias de referência candidatas pelo `QgsSpatialIndex`, nunca a união
    inteira da referência.

    Args:
        geoms_ref: iterável de `QgsGeometry` (linhas) da malha de referência.
        geoms_novas: iterável de `QgsGeometry` (linhas) da fonte nova.
        tol_m, min_sobrep_m, min_pedaco_m: tolerâncias em metros.

    Returns:
        Lista (uma entrada por geometria nova, na mesma ordem) de dicts:
        ``{'pedacos': [QgsGeometry, ...], 'aparada': bool,
        'metros_removidos': float}``. `pedacos` vazio = removida inteira;
        `aparada` indica que houve subtração por sobreposição;
        `metros_removidos` inclui os fiapos descartados. Linha sem
        subtração volta intacta (cópia da original, um único pedaço).
    """
    indice = QgsSpatialIndex()
    refs = {}
    for i, g in enumerate(geoms_ref):
        if g is None or g.isNull() or g.isEmpty():
            continue
        feat = QgsFeature(i)
        feat.setGeometry(g)
        indice.addFeature(feat)
        refs[i] = g
    buffers = {}

    resultado = []
    for geom in geoms_novas:
        if geom is None or geom.isNull() or geom.isEmpty():
            resultado.append({'pedacos': [], 'aparada': False,
                              'metros_removidos': 0.0})
            continue
        intacta = {'pedacos': [QgsGeometry(geom)], 'aparada': False,
                   'metros_removidos': 0.0}

        caixa = geom.boundingBox()
        caixa.grow(tol_m)
        ids = indice.intersects(caixa)
        if not ids:
            resultado.append(intacta)
            continue
        for i in ids:
            if i not in buffers:
                buffers[i] = refs[i].buffer(tol_m, 8)
        zona = QgsGeometry.unaryUnion([buffers[i] for i in ids])

        pedacos = []
        removidos = 0.0
        aparada = False
        for parte in _partes_simples(geom):
            comp = parte.length()
            cortes = [iv for iv in _intervalos_dentro(parte, zona)
                      if iv[1] - iv[0] >= min_sobrep_m]
            if not cortes:
                pedacos.append(QgsGeometry(parte))
                continue
            aparada = True
            linha = parte.constGet()
            inicio = 0.0
            mantido = 0.0
            for a, b in cortes + [[comp, comp]]:
                if a - inicio >= min_pedaco_m:
                    pedacos.append(QgsGeometry(linha.curveSubstring(inicio, a)))
                    mantido += a - inicio
                inicio = b
            removidos += comp - mantido

        if not aparada:
            resultado.append(intacta)
        else:
            resultado.append({'pedacos': pedacos, 'aparada': True,
                              'metros_removidos': removidos})
    return resultado


# --- Orquestrador do download (D1, D3–D8) -----------------------------------

def _crs(valor):
    """`QgsCoordinateReferenceSystem` a partir de um CRS ou de um authid."""
    if isinstance(valor, QgsCoordinateReferenceSystem):
        return valor
    return QgsCoordinateReferenceSystem(str(valor))


def _bbox_4674(uf, bbox, bbox_crs, crs_4674):
    """bbox do pedido em EPSG:4674 (D7); `None` vira a extensão da UF."""
    if bbox is None:
        if uf not in gisbr_bridge.BBOX_UF:
            raise ValueError(f'UF inválida para o download da malha: {uf!r}')
        return QgsRectangle(*gisbr_bridge.BBOX_UF[uf])
    rect = QgsRectangle(bbox) if isinstance(bbox, QgsRectangle) else QgsRectangle(*bbox)
    origem = _crs(bbox_crs) if bbox_crs else crs_4674
    if origem != crs_4674:
        rect = QgsCoordinateTransform(
            origem, crs_4674, QgsProject.instance()).transformBoundingBox(rect)
    return rect


def _tipo_campo(campo):
    """Nome de tipo (D6) de um `QgsField`, igual em Qt5 e Qt6."""
    tipo = campo.type()
    try:
        return _TIPO_CAMPO.get(int(getattr(tipo, 'value', tipo)), 'String')
    except (TypeError, ValueError):
        return 'String'


def _valor_py(valor):
    """Valor de atributo como Python puro: NULL -> None, datas -> ISO."""
    if valor is None:
        return None
    is_null = getattr(valor, 'isNull', None)
    if callable(is_null) and is_null():
        return None
    for conv in ('toPyDateTime', 'toPyDate', 'toPyTime'):
        func = getattr(valor, conv, None)
        if callable(func):
            return func().isoformat()
    return valor


def _geom(pts):
    return QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in pts])


def _pts_de(geom):
    """Listas de (x, y) 2D das partes lineares de uma geometria."""
    saida = []
    for parte in _partes_simples(geom):
        if parte.type() != QgsWkbTypes.LineGeometry:
            continue
        # asPolyline devolve QgsPointXY: Z e M ficam de fora (D5).
        pts = [(p.x(), p.y()) for p in parte.asPolyline()]
        if len(pts) >= 2:
            saida.append(pts)
    return saida


def _linhas_da_fonte(camada, fonte_id, rect_4674, para_4674, para_metrico):
    """Recorta pelo bbox (4674), reprojeta e extrai linhas simples 2D (D5, D7)."""
    caixa = QgsGeometry.fromRect(rect_4674)
    nomes = camada.fields().names()
    linhas = []
    nulas = fora = 0
    for feat in camada.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            nulas += 1
            continue
        geom = QgsGeometry(geom)
        if para_4674 is not None:
            geom.transform(para_4674)
        if not geom.boundingBox().intersects(rect_4674) or not geom.intersects(caixa):
            fora += 1
            continue
        if not caixa.contains(geom):
            geom = geom.intersection(caixa)
        geom.transform(para_metrico)
        attrs = {n: _valor_py(v) for n, v in zip(nomes, feat.attributes())}
        for pts in _pts_de(geom):
            linhas.append({'pts': pts, 'attrs': attrs, 'fonte': fonte_id,
                           'ajuste': ''})
    return linhas, nulas, fora


def _progresso(feedback, pct, msg):
    if feedback is None:
        return
    if hasattr(feedback, 'setProgress'):
        feedback.setProgress(pct)
    if hasattr(feedback, 'pushInfo'):
        feedback.pushInfo(msg)


def baixar_malha(uf, bbox=None, bbox_crs=None, ids_fontes=None, feedback=None):
    """Baixa e junta as malhas rodoviárias da UF via GISBR (D1, D3–D8).

    Pipeline: fontes da UF na ordem de D2 (filtradas por `ids_fontes`) ->
    bbox em EPSG:4674 (D7) -> download de cada fonte (falha aborta, D8) ->
    recorte pelo bbox -> reprojeção para `aon.pick_metric_crs` -> linhas
    simples 2D -> `limpa_linhas` com o `rede.excluir` da fonte ->
    `subtrai_sobreposicao` contra a malha acumulada -> `costura_extremidades`
    na malha unida -> camada com o esquema de D6.

    Args:
        uf (str): Sigla da UF (2 letras).
        bbox: (xmin, ymin, xmax, ymax) ou `QgsRectangle` em `bbox_crs`;
            None = extensão da UF (`gisbr_bridge.BBOX_UF`).
        bbox_crs: CRS do bbox (`QgsCoordinateReferenceSystem` ou authid);
            None = EPSG:4674.
        ids_fontes (list | None): ids das fontes a baixar; None = todas.
        feedback: objeto opcional com `setProgress`/`pushInfo`.

    Returns:
        tuple: (QgsVectorLayer em memória, relatorio dict).

    Raises:
        RuntimeError: GISBR ausente, nenhuma fonte, ou falha de uma fonte (a
            mensagem começa com o nome dela).
    """
    uf = (uf or '').strip().upper()
    fontes = gisbr_bridge.fontes_rodoviarias(uf)
    if ids_fontes is not None:
        pedidas = set(ids_fontes)
        fontes = [f for f in fontes if f.get('id') in pedidas]
    if not fontes:
        if not gisbr_bridge.is_available():
            raise RuntimeError(gisbr_bridge.missing_message())
        raise RuntimeError(f'Nenhuma fonte rodoviária do GisBR para a UF {uf!r}.')

    crs_4674 = QgsCoordinateReferenceSystem('EPSG:4674')
    rect = _bbox_4674(uf, bbox, bbox_crs, crs_4674)
    bbox_tupla = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())
    crs_metrico, _ = pick_metric_crs(crs_4674, bbox_tupla)
    if crs_metrico is None:
        raise RuntimeError('Não foi possível determinar um CRS métrico para a malha.')
    para_metrico = QgsCoordinateTransform(crs_4674, crs_metrico, QgsProject.instance())

    # 1) Baixa tudo antes de processar: falha de qualquer fonte aborta (D8).
    camadas = []
    for i, fonte in enumerate(fontes):
        nome = fonte.get('nome') or fonte.get('id')
        _progresso(feedback, 50.0 * i / len(fontes), f'Baixando {nome}')
        try:
            camada = gisbr_bridge.baixar_fonte(fonte, bbox_tupla, uf=uf)
        except Exception as err:
            msg = str(err)
            raise RuntimeError(
                msg if msg.startswith(f'{nome}:') else f'{nome}: {msg}') from err
        camadas.append(camada)

    # 2) Junta na ordem de precedência (D3).
    malha = []
    campos_por_fonte = []
    rel_fontes = []
    for i, (fonte, camada) in enumerate(zip(fontes, camadas)):
        nome = fonte.get('nome') or fonte.get('id')
        _progresso(feedback, 50.0 + 40.0 * i / len(fontes), f'Juntando {nome}')
        campos_por_fonte.append([(c.name(), _tipo_campo(c)) for c in camada.fields()])
        para_4674 = None
        if camada.crs() != crs_4674:
            para_4674 = QgsCoordinateTransform(camada.crs(), crs_4674,
                                               QgsProject.instance())
        linhas, nulas, fora = _linhas_da_fonte(camada, fonte.get('id'), rect,
                                               para_4674, para_metrico)
        excluir = (fonte.get('rede') or {}).get('excluir')
        linhas, rel_limpeza = limpa_linhas(linhas, excluir=excluir)

        removidas = aparadas = 0
        metros = 0.0
        if malha and linhas:
            res = subtrai_sobreposicao([_geom(l['pts']) for l in malha],
                                       [_geom(l['pts']) for l in linhas])
            novas = []
            for linha, r in zip(linhas, res):
                if r['aparada']:
                    metros += r['metros_removidos']
                    if r['pedacos']:
                        aparadas += 1
                    else:
                        removidas += 1
                for pedaco in r['pedacos']:
                    for pts in _pts_de(pedaco):
                        novas.append(dict(linha, pts=pts,
                                          ajuste='aparada' if r['aparada'] else ''))
            linhas = novas
        malha.extend(linhas)
        rel_fontes.append({
            'id': fonte.get('id'), 'nome': nome,
            'baixadas': camada.featureCount(), 'nulas': nulas,
            'fora_do_recorte': fora, 'limpeza': rel_limpeza,
            'removidas_inteiras': removidas, 'aparadas': aparadas,
            'metros_removidos': metros, 'linhas': len(linhas),
            'vazia': not linhas,
        })

    # 3) Costura das pontas soltas na malha unida (D4).
    malha, rel_costura = costura_extremidades(malha, tol_m=TOL_COSTURA_M)

    # 4) Camada com o esquema de D6.
    campos = uniao_campos(campos_por_fonte)
    saida = QgsVectorLayer('LineString', f'malha_gisbr_{uf.lower()}', 'memory')
    saida.setCrs(crs_metrico)
    prov = saida.dataProvider()
    prov.addAttributes([_create_field(n, _TIPO_QGIS.get(t, 'string'))
                        for n, t in campos])
    saida.updateFields()
    feats = []
    for linha in malha:
        attrs = {k.lower(): v for k, v in linha['attrs'].items()}
        valores = []
        for nome_campo, tipo in campos:
            if nome_campo == 'fonte':
                valores.append(linha['fonte'])
            elif nome_campo == 'ajuste':
                valores.append(linha['ajuste'])
            else:
                valores.append(converte_valor(attrs.get(nome_campo.lower()), tipo))
        feat = QgsFeature(saida.fields())
        feat.setGeometry(_geom(linha['pts']))
        feat.setAttributes(valores)
        feats.append(feat)
    prov.addFeatures(feats)
    saida.updateExtents()
    _progresso(feedback, 100.0, f'Malha unida: {len(feats)} trechos')

    relatorio = {
        'uf': uf, 'bbox_4674': bbox_tupla, 'crs': crs_metrico.authid(),
        'fontes': rel_fontes, 'costura': rel_costura, 'feicoes': len(feats),
    }
    return saida, relatorio
