# coding=utf-8
"""Adaptador fino de integração com o plugin GisBR (D6).

Ordem de tentativa ao buscar a malha rodoviária:
1. Algoritmo de processamento `gisbr:*` se exposto pelo GisBR;
2. Fallback importando `gisbr.core.sources` e `gisbr.core.connectors.wfs`;
3. Se o GisBR não estiver instalado ou falhar, erro explícito com mensagem clara.
"""

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
    if uf and uf.upper() == "MG":
        for s in SOURCES:
            if s.get("id") == "der_mg_rodovias":
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
