# coding=utf-8
"""Módulo para leitura e casamento espacial de postos de contagem com trechos alocados (D2, D3).

Realiza o cruzamento espacial entre camadas de contagens de tráfego e camadas
de alocação viária, associando postos aos trechos mais próximos, agregando
volumes bidirecionais (fw + bw) do mesmo link e calculando a estatística GEH
para calibração de macrossimulação.

Este módulo utiliza qgis.core e recebe o transform_context explicitamente,
sem dependência de instâncias de projeto ou interface gráfica.
"""

import math

from qgis.core import (
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsGeometry,
    QgsSpatialIndex,
    NULL,
)

from .calibration import geh, faixa_geh, volume_no_posto


def casar_postos(
    assign_layer,
    posts_layer,
    count_field,
    id_field=None,
    max_dist_m=200.0,
    fator=1.0,
    transform_context=None,
):
    """Associa postos de contagem aos trechos alocados mais próximos e calcula GEH.

    Args:
        assign_layer (QgsVectorLayer): Camada com a rede de alocação de tráfego.
            Deve possuir CRS métrico projetado e conter os atributos 'link_id' e 'volume'.
        posts_layer (QgsVectorLayer): Camada de pontos com os postos de contagem.
        count_field (str): Nome do atributo numérico contendo o volume contado.
        id_field (str, optional): Nome do atributo identificador do posto. Se omitido,
            vazio ou None, o FID da feição será utilizado.
        max_dist_m (float): Distância máxima em metros para associação posto → trecho
            (padrão 200.0 m). Acima desse limite, o posto recebe faixa 'sem_link'.
        fator (float): Fator multiplicador aplicado ao volume modelado (padrão 1.0).
        transform_context (QgsCoordinateTransformContext, optional): Contexto de
            transformação de coordenadas. Se None, cria uma instância vazia.

    Returns:
        tuple[list[dict], int]: Tupla (resultados, n_invalidos), onde:
            - resultados: lista de dicts com as chaves:
                - 'posto': identificador do posto (ou FID),
                - 'contagem': volume contado (float),
                - 'modelado': volume modelado × fator (float),
                - 'fator': fator aplicado (float),
                - 'dif': M - C (float),
                - 'dif_pct': (M - C) / C * 100 (float, ou None se contagem == 0),
                - 'geh': estatística GEH (float, ou None se faixa == 'sem_link'),
                - 'faixa': classificação GEH ('A', 'B', 'C', 'D' ou 'sem_link'),
                - 'link_id': identificador do link associado (ou None se 'sem_link'),
                - 'dist_m': distância em metros ao trecho (ou None se 'sem_link'),
                - 'geometry': QgsGeometry do posto no CRS da alocação.
            - n_invalidos: quantidade de postos ignorados por contagem nula,
              não-numérica ou negativa.

    Raises:
        ValueError: Se assign_layer não possuir os campos 'link_id' ou 'volume',
            ou se count_field não existir em posts_layer.
        RuntimeError: Se o CRS de assign_layer for geográfico.
    """
    if assign_layer is None or posts_layer is None:
        raise ValueError("Camadas de alocação e postos são obrigatórias.")

    assign_fields = [f.name() for f in assign_layer.fields()]
    missing = [f for f in ('link_id', 'volume') if f not in assign_fields]
    if missing:
        raise ValueError(
            f"Camada de alocação não possui os campos obrigatórios: {', '.join(missing)}"
        )

    if assign_layer.crs().isGeographic():
        raise RuntimeError(
            f"Camada de alocação possui CRS geográfico ({assign_layer.crs().authid()}). "
            "CRS métrico projetado é obrigatório para cálculo de distâncias."
        )

    posts_fields = [f.name() for f in posts_layer.fields()]
    if count_field not in posts_fields:
        raise ValueError(
            f"Campo de contagem '{count_field}' não encontrado na camada de postos."
        )

    use_id_field = bool(id_field and str(id_field).strip())
    if use_id_field and str(id_field).strip() not in posts_fields:
        raise ValueError(
            f"Campo identificador '{id_field}' não encontrado na camada de postos."
        )

    if transform_context is None:
        transform_context = QgsCoordinateTransformContext()

    assign_crs = assign_layer.crs()
    posts_crs = posts_layer.crs()

    transform = None
    if posts_crs.isValid() and assign_crs.isValid() and posts_crs != assign_crs:
        transform = QgsCoordinateTransform(posts_crs, assign_crs, transform_context)

    # Constrói o índice espacial dos trechos da camada de alocação
    spatial_index = QgsSpatialIndex()
    assign_features = {}

    for feat in assign_layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            continue

        raw_vol = feat['volume']
        if raw_vol is None or raw_vol == NULL:
            vol = None
        else:
            try:
                vol = float(raw_vol)
            except (ValueError, TypeError):
                vol = None

        raw_link_id = feat['link_id']
        link_id = None if raw_link_id == NULL else raw_link_id

        fid = feat.id()
        assign_features[fid] = (QgsGeometry(geom), link_id, vol)
        spatial_index.addFeature(feat)

    resultados = []
    n_invalidos = 0
    fator_float = float(fator)

    for post_feat in posts_layer.getFeatures():
        raw_count = post_feat[count_field]
        if raw_count is None or raw_count == NULL or isinstance(raw_count, bool):
            n_invalidos += 1
            continue

        try:
            contagem = float(raw_count)
        except (ValueError, TypeError):
            n_invalidos += 1
            continue

        if math.isnan(contagem) or math.isinf(contagem) or contagem < 0:
            n_invalidos += 1
            continue

        geom = post_feat.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            n_invalidos += 1
            continue

        post_geom = QgsGeometry(geom)
        if transform is not None:
            status = post_geom.transform(transform)
            if status != 0 or post_geom.isNull() or post_geom.isEmpty():
                n_invalidos += 1
                continue

        # Identificador do posto
        if use_id_field:
            raw_id = post_feat[str(id_field).strip()]
            if raw_id is not None and raw_id != NULL:
                posto = raw_id
            else:
                posto = post_feat.id()
        else:
            posto = post_feat.id()

        # Busca espacial dos trechos candidatos dentro de max_dist_m
        caixa = post_geom.boundingBox()
        caixa.grow(max_dist_m)
        cand_fids = spatial_index.intersects(caixa)

        candidatos = []
        for cand_fid in cand_fids:
            arc_geom, arc_link_id, arc_vol = assign_features[cand_fid]
            dist = post_geom.distance(arc_geom)
            if dist <= max_dist_m:
                candidatos.append((dist, arc_link_id, arc_vol))

        if not candidatos:
            modelado = 0.0
            dif = float(modelado - contagem)
            dif_pct = None if contagem == 0.0 else float(100.0 * (modelado - contagem) / contagem)
            geh_val = None
            faixa = 'sem_link'
            link_id = None
            dist_m = None
        else:
            min_cand = min(candidatos, key=lambda c: c[0])
            dist_m = float(min_cand[0])
            link_id = min_cand[1]

            raw_vol = volume_no_posto(candidatos, tol_m=1.0)
            modelado = float(raw_vol * fator_float)
            dif = float(modelado - contagem)
            dif_pct = None if contagem == 0.0 else float(100.0 * (modelado - contagem) / contagem)
            geh_val = float(geh(modelado, contagem))
            faixa = faixa_geh(geh_val)

        resultados.append({
            'posto': posto,
            'contagem': contagem,
            'modelado': modelado,
            'fator': fator_float,
            'dif': dif,
            'dif_pct': dif_pct,
            'geh': geh_val,
            'faixa': faixa,
            'link_id': link_id,
            'dist_m': dist_m,
            'geometry': post_geom,
        })

    return resultados, n_invalidos
