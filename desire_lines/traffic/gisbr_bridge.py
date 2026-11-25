# coding=utf-8
"""Adaptador fino de integração com o plugin GisBR (D6).

A malha rodoviária vem de `fontes_rodoviarias` + `baixar_fonte`, juntas por
`malha_gisbr.baixar_malha`; `fetch_road_network` delega para lá. Se o GisBR
não estiver instalado ou falhar, erro explícito com mensagem clara.
"""

TIPOS_RECORTE = ("rm", "micro", "meso", "macsaud")

# Tabela estática de BBOX por UF em EPSG:4674 com folga de 0.1° para fora (D7).
# Fonte: Malhas estaduais do IBGE (https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF).
BBOX_UF = {
    "AC": (-74.0904, -11.2456, -66.5239, -7.0118),
    "AL": (-38.3376, -10.5986, -35.0527, -8.7161),
    "AM": (-73.9016, -9.918, -55.9976, 2.3466),
    "AP": (-54.9763, -1.3362, -49.7758, 4.6088),
    "BA": (-46.6768, -18.4372, -37.2411, -8.4328),
    "CE": (-41.5233, -7.9576, -37.1527, -2.6843),
    "DF": (-48.3857, -16.15, -47.2085, -15.4018),
    "ES": (-41.9796, -21.4011, -29.199, -17.7919),
    "GO": (-53.3485, -19.5981, -45.8072, -12.2954),
    "MA": (-48.8552, -10.3596, -41.6967, -0.9495),
    "MG": (-51.1461, -23.0228, -39.7568, -14.1333),
    "MS": (-58.2686, -24.1682, -50.8242, -17.0663),
    "MT": (-61.7334, -18.1416, -50.1248, -7.249),
    "PA": (-58.9983, -9.9412, -45.9618, 2.691),
    "PB": (-38.8652, -8.403, -34.6932, -5.9259),
    "PE": (-41.4583, -9.5829, -32.2971, -3.7358),
    "PI": (-46.1282, -11.0288, -40.2705, -2.6499),
    "PR": (-54.7199, -26.8171, -47.9235, -22.4163),
    "RJ": (-44.9893, -23.4676, -40.8579, -20.6632),
    "RN": (-38.6821, -7.0827, -34.8685, -4.7314),
    "RO": (-66.9103, -13.7937, -59.6744, -7.8759),
    "RR": (-64.9253, -1.6806, -58.7869, 5.3718),
    "RS": (-57.7497, -33.8508, -49.5914, -26.9823),
    "SC": (-53.9371, -29.4551, -48.2585, -25.8558),
    "SE": (-38.345, -11.6685, -36.2959, -9.415),
    "SP": (-53.2101, -25.4089, -44.0614, -19.6799),
    "TO": (-50.8421, -13.5682, -45.5993, -5.0684),
}


def missing_message():
    """Retorna a mensagem de erro explicativa quando o GisBR não está instalado/disponível."""
    msg = (
        "O plugin GisBR (https://github.com/d-camargo/gisbr) é necessário "
        "para obter a malha rodoviária oficial."
    )
    try:
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate("GisBrBridge", msg)
    except ImportError:
        return msg


def is_available():
    """Verifica se o GisBR está instalado e disponível no ambiente."""
    # 1. Verifica se o módulo python gisbr pode ser importado
    try:
        import gisbr.core.sources  # noqa: F401
        import gisbr.core.connectors.wfs  # noqa: F401
        return True
    except ImportError:
        pass

    # 2. Verifica se o provedor processing 'gisbr' está registrado no QGIS
    try:
        from qgis.core import QgsApplication
        registry = QgsApplication.processingRegistry()
        if registry and registry.providerById("gisbr") is not None:
            return True
    except (ImportError, AttributeError):
        pass

    return False


def fetch_road_network(bbox=None, crs=None, uf=None):
    """Obtém a malha rodoviária oficial via GisBR (D1 do plano 0.8.0).

    Delega para `malha_gisbr.baixar_malha` (DNIT + bases estaduais da UF,
    juntas) e devolve só a camada; `crs` é o CRS do `bbox`.

    Returns:
        QgsVectorLayer com a malha rodoviária unida.

    Raises:
        RuntimeError: Se o GisBR não estiver instalado ou se o download falhar.
    """
    if not is_available():
        raise RuntimeError(missing_message())

    from . import malha_gisbr
    layer, _ = malha_gisbr.baixar_malha(uf, bbox=bbox, bbox_crs=crs)
    return layer


def fontes_rodoviarias(uf):
    """Retorna lista de fontes rodoviárias oficiais aplicáveis à UF (D2).

    Ordem de precedência:
    1. 'dnit_snv' primeiro (rede federal);
    2. Fontes com rede.tipo == 'rodoviaria', uf em ufs e
       protocolo em ('wfs', 'arcgis', 'zip_remoto'), na ordem do catálogo.

    Ficam de fora: fontes sem rede (ex.: IBGE BC250), OSM e protocolos não suportados.
    Devolve [] se o GisBR não estiver disponível / não puder ser importado.

    Args:
        uf: Sigla da UF com 2 letras (ex.: 'MG').

    Returns:
        Lista de dicionários de metadados das fontes.
    """
    if not uf:
        return []

    try:
        from gisbr.core.sources import SOURCES
    except ImportError:
        return []

    uf_upper = str(uf).upper()
    resultado = []
    dnit = None
    for s in SOURCES:
        if s.get("id") == "dnit_snv":
            dnit = s
            break

    if dnit is not None:
        resultado.append(dnit)

    for s in SOURCES:
        if s.get("id") == "dnit_snv":
            continue
        rede = s.get("rede") or {}
        if rede.get("tipo") != "rodoviaria":
            continue
        ufs = [u.upper() for u in s.get("ufs", [])] if s.get("ufs") else []
        if uf_upper not in ufs:
            continue
        proto = s.get("protocolo")
        if proto not in ("wfs", "arcgis", "zip_remoto"):
            continue
        resultado.append(s)

    return resultado


def baixar_fonte(fonte, bbox_4674=None, uf=None):
    """Baixa uma fonte rodoviária usando o conector apropriado do GisBR (D2, D7, D8).

    Despacha por `fonte['protocolo']`:
    - 'wfs': gisbr.core.connectors.wfs.fetch_layer (substitui '{uf}' em type_name)
    - 'arcgis' / 'arcgis_rest': gisbr.core.connectors.arcgis_rest.fetch_layer
    - 'zip_remoto': gisbr.core.connectors.zip_remoto.fetch_layer

    Args:
        fonte: Dicionário de metadados da fonte (do catálogo SOURCES do GisBR).
        bbox_4674: Bounding box (xmin, ymin, xmax, ymax) em EPSG:4674 ou None.
        uf: Sigla opcional da UF para substituição de '{uf}' em type_name.

    Returns:
        QgsVectorLayer válido carregado.

    Raises:
        RuntimeError: Se o GisBR não estiver disponível, se o protocolo não for suportado,
            ou se a camada retornada for inválida (a mensagem inicia com "{fonte['nome']}: ").
    """
    nome = fonte.get("nome", fonte.get("id", "Fonte"))
    proto = fonte.get("protocolo")
    srs = fonte.get("srs", "EPSG:4674")

    try:
        if proto == "wfs":
            from gisbr.core.connectors import wfs

            type_name = fonte.get("type_name") or ""
            if "{uf}" in type_name or "{UF}" in type_name:
                uf_val = uf or (fonte.get("ufs", [None])[0]) or ""
                type_name = type_name.replace("{uf}", str(uf_val).lower()).replace("{UF}", str(uf_val).upper())

            endpoint = fonte.get("endpoint")
            cql = fonte.get("cql") or fonte.get("cql_filter")
            kwargs = {
                "endpoint": endpoint,
                "type_name": type_name,
                "layer_name": nome,
                "srs": srs,
                "bbox": bbox_4674,
            }
            if cql:
                kwargs["cql_filter"] = cql
            layer = wfs.fetch_layer(**kwargs)

        elif proto in ("arcgis", "arcgis_rest"):
            from gisbr.core.connectors import arcgis_rest

            endpoint = fonte.get("endpoint")
            layer_id = str(fonte.get("layer_id", "0"))
            where = fonte.get("where") or fonte.get("cql")
            layer = arcgis_rest.fetch_layer(
                endpoint=endpoint,
                layer_id=layer_id,
                layer_name=nome,
                srs=srs,
                where=where,
                bbox=bbox_4674,
            )

        elif proto == "zip_remoto":
            from gisbr.core.connectors import zip_remoto

            url = fonte.get("url") or fonte.get("endpoint") or fonte.get("origem_url")
            cache_id = fonte.get("cache_id")
            subset = fonte.get("subset")
            layer = zip_remoto.fetch_layer(
                url=url,
                layer_name=nome,
                srs=srs,
                subset=subset,
                cache_id=cache_id,
            )

        else:
            raise RuntimeError(f"{nome}: protocolo não suportado: {proto}")

    except ImportError as exc:
        raise RuntimeError(f"{nome}: {missing_message()}") from exc
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"{nome}: {exc}") from exc

    if layer is None or not (hasattr(layer, "isValid") and layer.isValid()):
        error_msg = getattr(layer, "error_msg", None) or "camada inválida"
        raise RuntimeError(f"{nome}: {error_msg}")

    return layer


def listar_recortes(tipo, uf):
    """Lista recortes regionais disponíveis para um determinado tipo e UF (D3).

    Args:
        tipo: Um de TIPOS_RECORTE ('rm', 'micro', 'meso', 'macsaud').
        uf: Sigla da UF com 2 letras.

    Returns:
        Lista de tuplas (id, nome). Devolve [] se tipo não estiver em TIPOS_RECORTE
        ou em caso de ImportError (ex.: versão antiga do GisBR).
    """
    if tipo not in TIPOS_RECORTE:
        return []

    try:
        if tipo == "rm":
            from gisbr.core import regioes_metropolitanas
            raw = regioes_metropolitanas.listar_por_uf(uf)
            return [
                (item["id"], item["nome"])
                if isinstance(item, dict)
                else (item[0], item[1])
                for item in (raw or [])
            ]
        elif tipo in ("micro", "meso"):
            from gisbr.core import divisao_regional
            raw = divisao_regional.listar(tipo, uf)
            return [
                (item[0], item[1])
                if not isinstance(item, dict)
                else (item["id"], item["nome"])
                for item in (raw or [])
            ]
        elif tipo == "macsaud":
            from gisbr.core import macro_saude
            raw = macro_saude.listar(uf)
            return [
                (item[0], item[1])
                if not isinstance(item, dict)
                else (item["id"], item["nome"])
                for item in (raw or [])
            ]
    except ImportError:
        return []

    return []


def _unir_e_transformar_camada(saida, rotulo):
    """Converte saída (camada ou caminho) em uma única geometria unida em EPSG:4674 (D2).

    Args:
        saida: QgsVectorLayer ou caminho em disco (str).
        rotulo: Texto descritivo para mensagens de erro (ex.: "UF 'SP'").

    Returns:
        QgsGeometry unida em EPSG:4674.

    Raises:
        RuntimeError: Se a camada for None, inválida, vazia ou sem geometrias
            válidas (a mensagem inclui o rótulo).
    """
    if saida is None:
        raise RuntimeError(f"Camada nula ao obter limite de {rotulo}")

    if isinstance(saida, str):
        from qgis.core import QgsVectorLayer
        layer = QgsVectorLayer(saida, str(rotulo), "ogr")
    else:
        layer = saida

    if layer is None or not layer.isValid():
        raise RuntimeError(f"Camada inválida ao obter limite de {rotulo}")

    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsCoordinateTransformContext,
        QgsGeometry,
    )

    geoms = [f.geometry() for f in layer.getFeatures()
             if f.hasGeometry() and not f.geometry().isEmpty()]
    if not geoms:
        raise RuntimeError(f"Nenhuma geometria válida encontrada ao obter limite de {rotulo}")

    geom_unida = QgsGeometry.unaryUnion(geoms)
    if geom_unida.isEmpty():
        raise RuntimeError(f"Geometria resultante vazia ao obter limite de {rotulo}")

    crs_camada = layer.crs()
    crs_4674 = QgsCoordinateReferenceSystem("EPSG:4674")
    if crs_camada.isValid() and crs_camada != crs_4674:
        geom_unida.transform(QgsCoordinateTransform(
            crs_camada, crs_4674, QgsCoordinateTransformContext()))
    return geom_unida


def limite_uf(uf):
    """Obtém o polígono do limite da UF em EPSG:4674 via GisBR (D2).

    Executa o algoritmo 'gisbr:read_state' com 'SIMPLIFIED'=True.
    A saída pode ser QgsVectorLayer ou caminho em disco.

    Args:
        uf: Sigla da UF (ex.: 'SP').

    Returns:
        QgsGeometry com a união das feições da UF em EPSG:4674.

    Raises:
        RuntimeError: Se o GisBR falhar, se a camada for None, vazia ou inválida
            (a mensagem inclui a UF).
    """
    if not uf:
        raise RuntimeError(f"UF inválida ou não informada: {uf!r}")

    uf_str = str(uf).upper()
    try:
        import processing
        res = processing.run(
            "gisbr:read_state",
            {"CODE": uf_str, "SIMPLIFIED": True, "OUTPUT": "TEMPORARY_OUTPUT"},
        )
    except Exception as exc:
        raise RuntimeError(f"Erro ao obter limite para UF {uf_str!r}: {exc}") from exc

    if res is None:
        raise RuntimeError(f"Nenhum resultado retornado para UF {uf_str!r}")

    saida = res.get("OUTPUT") if isinstance(res, dict) else res
    if saida is None:
        raise RuntimeError(f"Saída nula para UF {uf_str!r}")

    return _unir_e_transformar_camada(saida, f"UF {uf_str!r}")


def limite_recorte(tipo, id_recorte):
    """Obtém o polígono do limite de um recorte regional em EPSG:4674 (D2).

    Args:
        tipo: Um de TIPOS_RECORTE ('rm', 'micro', 'meso', 'macsaud').
        id_recorte: Identificador do recorte (ex.: '04501').

    Returns:
        QgsGeometry com a união das feições do recorte em EPSG:4674.

    Raises:
        ValueError: Se o tipo estiver fora de TIPOS_RECORTE.
        RuntimeError: Quando não há municípios, em caso de exceção, ou se
            camada_do_recorte devolver None, camada vazia ou inválida
            (a mensagem inclui tipo e id_recorte).
    """
    if tipo not in TIPOS_RECORTE:
        raise ValueError(
            f"Tipo de recorte inválido: {tipo!r}. Esperado um de: {TIPOS_RECORTE}"
        )

    rotulo = f"recorte tipo={tipo!r}, id={id_recorte!r}"
    try:
        from gisbr.core import recorte

        if tipo == "rm":
            from gisbr.core import regioes_metropolitanas
            codes = regioes_metropolitanas.codes(id_recorte)
            if not codes:
                raise RuntimeError(
                    f"Nenhum município encontrado para {rotulo}"
                )
            rec = recorte.Recorte.de_rm(str(id_recorte), str(id_recorte), codes)
        elif tipo in ("micro", "meso"):
            from gisbr.core import divisao_regional
            munis = divisao_regional.municipios(tipo, id_recorte)
            codes = [m[0] if isinstance(m, (tuple, list)) else m for m in (munis or [])]
            if not codes:
                raise RuntimeError(
                    f"Nenhum município encontrado para {rotulo}"
                )
            rec = recorte.Recorte.de_agregado(tipo, str(id_recorte), str(id_recorte), codes)
        elif tipo == "macsaud":
            from gisbr.core import macro_saude
            munis = macro_saude.municipios(id_recorte)
            codes = [m[0] if isinstance(m, (tuple, list)) else m for m in (munis or [])]
            if not codes:
                raise RuntimeError(
                    f"Nenhum município encontrado para {rotulo}"
                )
            rec = recorte.Recorte.de_agregado(tipo, str(id_recorte), str(id_recorte), codes)
        else:
            raise ValueError(f"Tipo de recorte não implementado: {tipo!r}")

        layer = recorte.camada_do_recorte(rec)
    except ValueError:
        raise
    except Exception as exc:
        if rotulo in str(exc):
            raise
        raise RuntimeError(f"Erro ao obter camada para {rotulo}: {exc}") from exc

    if layer is None:
        raise RuntimeError(
            f"camada_do_recorte devolveu None para {rotulo}"
        )

    return _unir_e_transformar_camada(layer, rotulo)


def extensao_recorte(tipo, id_recorte):
    """Obtém a extensão geográfica (bbox) de um recorte regional em EPSG:4674 (D3).

    Args:
        tipo: Um de TIPOS_RECORTE ('rm', 'micro', 'meso', 'macsaud').
        id_recorte: Identificador do recorte (ex.: '04501').

    Returns:
        Tupla (xMinimum, yMinimum, xMaximum, yMaximum) da extensão da camada.

    Raises:
        ValueError: Se o tipo estiver fora de TIPOS_RECORTE.
        RuntimeError: Quando não há município para o recorte ou se a camada_do_recorte
            devolver None, camada vazia ou exceção (a mensagem inclui tipo e id_recorte).
    """
    geom = limite_recorte(tipo, id_recorte)
    bbox = geom.boundingBox()
    if hasattr(bbox, "xMinimum"):
        return (bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum())
    return (bbox[0], bbox[1], bbox[2], bbox[3])
