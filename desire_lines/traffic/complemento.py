# coding=utf-8
"""Módulo para casamento espacial entre malha viária e camadas complementares (D6).

Realiza o cruzamento espacial por proximidade entre a rede rodoviária e uma camada
complementar vetorial (linhas OSM, postos com % de pesados, polígonos urbanos, etc.).
Para cada link rodoviário, busca a feição complementar mais próxima do ponto médio
do link a até uma distância máxima e extrai seus atributos não nulos.

Este módulo utiliza apenas qgis.core e recebe o transform_context explicitamente,
sem dependência de QgsProject ou interface gráfica.
"""

import math

from qgis.core import (
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsFeature,
    QgsGeometry,
    QgsSpatialIndex,
    NULL,
)


def _link_midpoint(geom):
    """Calcula o ponto médio de uma geometria de linha."""
    if geom is None or geom.isNull() or geom.isEmpty():
        return None
    pt = geom.interpolate(geom.length() / 2.0)
    if pt is None or pt.isNull() or pt.isEmpty():
        pt = geom.centroid()
    if pt is None or pt.isNull() or pt.isEmpty():
        return None
    return pt


def _atributos_nao_nulos(feat):
    """Extrai atributos não nulos de uma feição como dict."""
    attrs = {}
    if feat is None:
        return attrs
    if isinstance(feat, dict):
        for k, val in feat.items():
            if val is None or val == "" or str(val) == "NULL" or val == NULL:
                continue
            if isinstance(val, float) and math.isnan(val):
                continue
            attrs[k] = val
        return attrs
    if hasattr(feat, "fields") and callable(feat.fields):
        for fld in feat.fields():
            name = fld.name()
            val = feat.attribute(name)
            if val is None or val == "" or str(val) == "NULL" or val == NULL:
                continue
            if isinstance(val, float) and math.isnan(val):
                continue
            attrs[name] = val
        return attrs
    return attrs


def atributos_por_proximidade(
    road_layer,
    compl_layer,
    max_dist_m=30.0,
    transform_context=None,
):
    """Realiza o casamento espacial entre a malha rodoviária e uma camada complementar (D6).

    Para cada link da malha rodoviária, busca a feição complementar mais próxima
    ao ponto médio do link a até `max_dist_m`. Se encontrada, associa ao ID do link
    os atributos não nulos da feição complementar.

    Args:
        road_layer (QgsVectorLayer): Camada com a malha rodoviária. Deve possuir
            CRS métrico projetado.
        compl_layer (QgsVectorLayer): Camada vetorial complementar (linhas OSM,
            postos de contagem, polígonos urbanos, etc.).
        max_dist_m (float): Distância máxima em metros para associação por
            proximidade (padrão 30.0 m).
        transform_context (QgsCoordinateTransformContext, optional): Contexto
            de transformação de coordenadas. Se None, cria uma instância vazia.

    Returns:
        dict[int, dict]: Dicionário mapeando FID da feição rodoviária para o
            dicionário de atributos não nulos da feição complementar mais próxima.
            Links sem vizinhos a até max_dist_m ficam fora.

    Raises:
        RuntimeError: Se o CRS da camada rodoviária for geográfico.
    """
    if road_layer is None:
        return {}

    road_crs = road_layer.crs()
    if road_crs.isGeographic():
        raise RuntimeError(
            f"Camada rodoviária possui CRS geográfico ({road_crs.authid()}). "
            "CRS métrico projetado é obrigatório para cálculo de distâncias."
        )

    if compl_layer is None:
        return {}

    max_dist = float(max_dist_m)
    if max_dist < 0.0:
        return {}

    if transform_context is None:
        transform_context = QgsCoordinateTransformContext()

    compl_crs = compl_layer.crs()
    transform = None
    if compl_crs.isValid() and road_crs.isValid() and compl_crs != road_crs:
        transform = QgsCoordinateTransform(compl_crs, road_crs, transform_context)

    compl_data = {}
    spatial_index = QgsSpatialIndex()

    for feat in compl_layer.getFeatures():
        geom = feat.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            continue

        geom_transformed = QgsGeometry(geom)
        if transform is not None:
            status = geom_transformed.transform(transform)
            if status != 0 or geom_transformed.isNull() or geom_transformed.isEmpty():
                continue

        fid = feat.id()
        idx_feat = QgsFeature(fid)
        idx_feat.setGeometry(geom_transformed)
        spatial_index.addFeature(idx_feat)

        attrs = _atributos_nao_nulos(feat)
        compl_data[fid] = (geom_transformed, attrs)

    if not compl_data:
        return {}

    resultado = {}
    for road_feat in road_layer.getFeatures():
        geom = road_feat.geometry()
        if geom is None or geom.isNull() or geom.isEmpty():
            continue

        midpoint = _link_midpoint(geom)
        if midpoint is None or midpoint.isNull() or midpoint.isEmpty():
            continue

        box = midpoint.boundingBox()
        box.grow(max_dist)
        cand_ids = spatial_index.intersects(box)
        if not cand_ids:
            continue

        candidatos = []
        for cand_id in cand_ids:
            if cand_id not in compl_data:
                continue
            compl_geom, attrs = compl_data[cand_id]
            dist = midpoint.distance(compl_geom)
            if dist <= max_dist:
                candidatos.append((dist, cand_id, attrs))

        if not candidatos:
            continue

        # De duas candidatas, vence a mais próxima (menor distância)
        candidatos.sort(key=lambda c: (c[0], c[1]))
        best_attrs = candidatos[0][2]
        resultado[road_feat.id()] = best_attrs

    return resultado
