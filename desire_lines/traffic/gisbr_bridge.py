# coding=utf-8
"""Adaptador fino de integração com o plugin GisBR (D6).

Ordem de tentativa ao buscar a malha rodoviária:
1. Algoritmo de processamento `gisbr:*` se exposto pelo GisBR;
2. Fallback importando `gisbr.core.sources` e `gisbr.core.connectors.wfs`;
3. Se o GisBR não estiver instalado ou falhar, erro explícito com mensagem clara.
"""

TIPOS_RECORTE = ("rm", "micro", "meso", "macsaud")


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


def _try_processing_algorithm(bbox, crs, uf=None):
    """Tenta executar algoritmo do provedor GisBR no QGIS Processing."""
    try:
        from qgis.core import QgsApplication
        import processing
    except ImportError:
        return None

    registry = QgsApplication.processingRegistry()
    if not registry:
        return None

    candidate_algs = ["gisbr:dnit_snv", "gisbr:road_network", "gisbr:snv"]
    alg_id = None
    for algname in candidate_algs:
        if registry.algorithm(algname):
            alg_id = algname
            break

    if not alg_id:
        return None

    params = {}
    if bbox is not None:
        params["BBOX"] = bbox
    if crs is not None:
        params["CRS"] = crs
    if uf is not None:
        params["UF"] = uf

    try:
        result = processing.run(alg_id, params)
        if isinstance(result, dict) and "OUTPUT" in result:
            return result["OUTPUT"]
        return result
    except Exception:
        return None


def _try_wfs_connector(bbox, crs, uf=None):
    """Tenta carregar a malha através dos conectores WFS internos do GisBR."""
    try:
        from gisbr.core.sources import SOURCES
        from gisbr.core.connectors.wfs import fetch_layer
    except ImportError:
        return None

    source_entry = None
    if uf:
        for s in SOURCES:
            if (
                (s.get("rede") or {}).get("tipo") == "rodoviaria"
                and uf.upper() in s.get("ufs", [])
                and s.get("protocolo", "wfs") == "wfs"
            ):
                source_entry = s
                break

    if not source_entry:
        for s in SOURCES:
            if s.get("id") == "dnit_snv":
                source_entry = s
                break

    if not source_entry:
        return None

    endpoint = source_entry.get("endpoint")
    type_name = source_entry.get("type_name")
    srs = source_entry.get("srs", crs or "EPSG:4674")
    layer_name = source_entry.get("nome", "Malha Rodoviária")

    try:
        layer = fetch_layer(
            endpoint=endpoint,
            type_name=type_name,
            layer_name=layer_name,
            srs=srs,
            bbox=bbox,
        )
        if layer and hasattr(layer, "isValid") and layer.isValid():
            return layer
        elif layer and getattr(layer, "error_msg", None):
            raise RuntimeError(
                f"Erro ao carregar WFS do GisBR: {layer.error_msg}"
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Falha ao chamar conector WFS do GisBR: {exc}")

    return None


def fetch_road_network(bbox=None, crs=None, uf=None):
    """Obtém a malha rodoviária oficial via GisBR (D6).

    Ordem de tentativa:
    1. Processing algorithm `gisbr:<alg>` se existir;
    2. Fallback direto via conector WFS do GisBR (`gisbr.core.connectors.wfs`);
    3. Exceção com `missing_message()` se o GisBR não estiver disponível ou falhar.

    Returns:
        QgsVectorLayer com a malha rodoviária.

    Raises:
        RuntimeError: Se o GisBR não estiver instalado ou se os métodos falharem.
    """
    if not is_available():
        raise RuntimeError(missing_message())

    # 1. Algoritmo de processamento
    layer = _try_processing_algorithm(bbox, crs, uf)
    if layer is not None:
        return layer

    # 2. Conector WFS interno
    layer = _try_wfs_connector(bbox, crs, uf)
    if layer is not None:
        return layer

    # 3. Erro explícito se nenhum caminho funcionou
    raise RuntimeError(
        f"GisBR está disponível mas não foi possível obter a malha rodoviária. {missing_message()}"
    )


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
            devolver None (a mensagem inclui tipo e id_recorte).
    """
    if tipo not in TIPOS_RECORTE:
        raise ValueError(
            f"Tipo de recorte inválido: {tipo!r}. Esperado um de: {TIPOS_RECORTE}"
        )

    from gisbr.core import recorte

    if tipo == "rm":
        from gisbr.core import regioes_metropolitanas
        codes = regioes_metropolitanas.codes(id_recorte)
        if not codes:
            raise RuntimeError(
                f"Nenhum município encontrado para recorte tipo={tipo!r}, id={id_recorte!r}"
            )
        rec = recorte.Recorte.de_rm(str(id_recorte), str(id_recorte), codes)
    elif tipo in ("micro", "meso"):
        from gisbr.core import divisao_regional
        munis = divisao_regional.municipios(tipo, id_recorte)
        codes = [m[0] if isinstance(m, (tuple, list)) else m for m in (munis or [])]
        if not codes:
            raise RuntimeError(
                f"Nenhum município encontrado para recorte tipo={tipo!r}, id={id_recorte!r}"
            )
        rec = recorte.Recorte.de_agregado(tipo, str(id_recorte), str(id_recorte), codes)
    elif tipo == "macsaud":
        from gisbr.core import macro_saude
        munis = macro_saude.municipios(id_recorte)
        codes = [m[0] if isinstance(m, (tuple, list)) else m for m in (munis or [])]
        if not codes:
            raise RuntimeError(
                f"Nenhum município encontrado para recorte tipo={tipo!r}, id={id_recorte!r}"
            )
        rec = recorte.Recorte.de_agregado(tipo, str(id_recorte), str(id_recorte), codes)
    else:
        raise ValueError(f"Tipo de recorte não implementado: {tipo!r}")

    layer = recorte.camada_do_recorte(rec)
    if layer is None:
        raise RuntimeError(
            f"camada_do_recorte devolveu None para recorte tipo={tipo!r}, id={id_recorte!r}"
        )

    extent = layer.extent()
    if hasattr(extent, "xMinimum"):
        return (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
    return (extent[0], extent[1], extent[2], extent[3])
