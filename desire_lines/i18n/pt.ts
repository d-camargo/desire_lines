<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1">
<context>
    <name>DesireLines</name>
    <message>
        <location filename="../desirelines.py" line="296"/>
        <source>&amp;Desire Lines</source>
        <translation>&amp;Desire Lines</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="183"/>
        <source>Desire Lines</source>
        <translation>Desire Lines</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="190"/>
        <source>Alocação em rodovias</source>
        <translation>Alocação em rodovias</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="229"/>
        <source>Desire Lines — GISBR</source>
        <translation>Desire Lines — GISBR</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="230"/>
        <source>Other plugin features remain available without it.</source>
        <translation>Outras funções do plugin continuam disponíveis sem ele.</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="234"/>
        <source>Open Plugin Manager</source>
        <translation>Abrir Gerenciador de Complementos</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="238"/>
        <source>Not now</source>
        <translation>Agora não</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="243"/>
        <source>Don&apos;t show again</source>
        <translation>Não mostrar novamente</translation>
    </message>
</context>
<context>
    <name>DesireLinesDialog</name>
    <message>
        <location filename="../desirelines_dialog.py" line="144"/>
        <source>Layer {!r} not found. {}</source>
        <translation>Camada {!r} não encontrada. {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="165"/>
        <source>Select a CSV matrix file first.</source>
        <translation>Selecione primeiro um arquivo CSV de matriz.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="170"/>
        <source>pandas is required for wide-to-long conversion. Install it in the QGIS Python environment and reload the plugin.</source>
        <translation>O pandas é necessário para a conversão de formato largo para longo. Instale-o no ambiente Python do QGIS e recarregue o plugin.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="198"/>
        <source>Select a vector file first.</source>
        <translation>Selecione primeiro um arquivo vetorial.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="203"/>
        <source>Layer failed to load!</source>
        <translation>Falha ao carregar a camada!</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="287"/>
        <source>Invalid layer or field name: {!r}. Use letters (including accents), digits, spaces, underscores, dots or hyphens — no quotes or semicolons.</source>
        <translation>Nome de camada ou campo inválido: {!r}. Use letras (inclusive acentuadas), dígitos, espaços, sublinhados, pontos ou hífens — sem aspas ou ponto e vírgula.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="327"/>
        <source>Generating desire lines…</source>
        <translation>Gerando linhas de desejo…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="429"/>
        <source>Need at least 3 valid centroids to build a Delaunay network.</source>
        <translation>São necessários pelo menos 3 centroides válidos para construir uma rede de Delaunay.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="441"/>
        <source>source CRS is already metric</source>
        <translation>o SRC de origem já é métrico</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="443"/>
        <source>auto UTM zone {} (EPSG:{})</source>
        <translation>zona UTM automática {} (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="446"/>
        <source>Brazil Albers (EPSG:{})</source>
        <translation>Albers Brasil (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="449"/>
        <source>could not determine a metric CRS automatically; reproject the centroids to a metric system (UTM) and try again</source>
        <translation>não foi possível determinar um SRC métrico automaticamente; reprojete os centroides para um sistema métrico (UTM) e tente novamente</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="481"/>
        <source>No OD pairs matched the centroid ids. Check that Origin, Destination and Traffic ID refer to the same id scheme.</source>
        <translation>Nenhum par OD correspondeu aos ids dos centroides. Verifique se Origem, Destino e ID de Tráfego usam o mesmo esquema de id.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="488"/>
        <source>Allocating (AoN over Delaunay)…</source>
        <translation>Alocando (AoN sobre Delaunay)…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="508"/>
        <source>{} unreachable (disconnected graph)</source>
        <translation>{} inacessível(is) (grafo desconectado)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="511"/>
        <source>{} matrix rows had unknown ids</source>
        <translation>{} linha(s) da matriz com ids desconhecidos</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="513"/>
        <source>{} skipped</source>
        <translation>{} ignorado(s)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="515"/>
        <source>AoN done: {} pairs allocated over {} edges using {}{}</source>
        <translation>AoN concluído: {} pares alocados em {} arestas usando {}{}</translation>
    </message>
</context>
<context>
    <name>DesireLinesDialogBase</name>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="338"/>
        <source>Desire Lines</source>
        <translation>Gerar Linhas de Desejo</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="29"/>
        <source>Origin/Destination Matrix</source>
        <translation>Matriz Origem/Destino</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="42"/>
        <source>Origin/Destination Matrix (csv format)</source>
        <translation>Matriz Origem/Destino (formato csv)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="54"/>
        <source>Read CSV</source>
        <translation>Ler CSV</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="61"/>
        <source>Travel Demand Matrix format</source>
        <translation>Formato da Matriz de Demanda de Viagens</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="90"/>
        <source>Traffic zone (shp or gpkg format)</source>
        <translation>Zona de tráfego (formato shp ou gpkg)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="102"/>
        <source>Read Vector</source>
        <translation>Ler Vetor</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="124"/>
        <source>…or assign an existing traffic-zones layer from the project (leave empty to use the imported file above):</source>
        <translation>…ou selecione uma camada de zonas de tráfego já existente no projeto (deixe em branco para usar o arquivo importado acima):</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="139"/>
        <source>Add Centroids to Traffic Zones</source>
        <translation>Adicionar Centroides às Zonas de Tráfego</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="168"/>
        <source>Output GeoPackage</source>
        <translation>GeoPackage de Saída</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="386"/>
        <source>Matrix</source>
        <translation>Matriz</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="400"/>
        <source>Centroids</source>
        <translation>Centroides</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="420"/>
        <source>Origin</source>
        <translation>Origem</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="434"/>
        <source>Traffic ID</source>
        <translation>ID de Tráfego</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="454"/>
        <source>Destination</source>
        <translation>Destino</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="292"/>
        <source>Value to Desire Lines</source>
        <translation>Valor para Linhas de Desejo</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="361"/>
        <source>AoN (Delaunay)</source>
        <translation>AoN (Delaunay)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="370"/>
        <source>All-or-Nothing allocation over a simplified Delaunay network built on the zone centroids. The whole flow of each OD pair follows its single least-cost path. This is a topological abstraction of demand over zone neighbourhood — not a real road-network loading.</source>
        <translation>Alocação Tudo-ou-Nada (AoN) sobre uma rede de Delaunay simplificada, construída a partir dos centroides das zonas. Todo o fluxo de cada par OD segue seu único caminho de menor custo. É uma abstração topológica da demanda sobre a vizinhança das zonas — não é um carregamento real da rede viária.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="471"/>
        <source>Value (flow)</source>
        <translation>Valor (fluxo)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="483"/>
        <source>Keep both travel directions per segment as separate fields (flow_ab = volume along the drawn A→B direction, flow_ba = the reverse). Unchecked: a single flow field with the combined total.</source>
        <translation>Manter os dois sentidos de viagem por segmento como campos separados (flow_ab = volume no sentido A→B do traçado, flow_ba = o sentido inverso). Desmarcado: um único campo de fluxo com o total combinado.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="486"/>
        <source>Split by direction (flow_ab / flow_ba)</source>
        <translation>Dividir por sentido (flow_ab / flow_ba)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="527"/>
        <source>Allocate (AoN)</source>
        <translation>Alocar (AoN)</translation>
    </message>
</context>
<context>
    <name>DesireLinesTrafficPanel</name>
    <message>
        <location filename="../traffic_panel_base.ui" line="14"/>
        <source>Desire Lines — Alocação em rodovias</source>
        <translation>Desire Lines — Alocação em rodovias</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="21"/>
        <source>The GisBR plugin is required to download the official highway network.</source>
        <translation>O plugin GisBR é necessário para baixar a malha rodoviária oficial.</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="31"/>
        <source>Scope: rural/interurban highways (HCM ch. 12 and 15). Urban stretches are flagged escopo='urbano' — urban capacity follows a different procedure and is out of scope.</source>
        <translation>Escopo: rodovias rurais/interurbanas (HCM cap. 12 e 15). Trechos urbanos são marcados com escopo='urbano' — a capacidade em área urbana segue outro procedimento e está fora do escopo.</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="69"/>
        <source>Network</source>
        <translation>Rede</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="75"/>
        <source>Use an existing layer</source>
        <translation>Usar uma camada existente</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="85"/>
        <source>Highway layer</source>
        <translation>Camada da malha rodoviária</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="95"/>
        <source>Link id field (optional)</source>
        <translation>Campo de id do link (opcional)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="109"/>
        <source>Download via GisBR (official SNV/DER network)</source>
        <translation>Baixar via GisBR (malha oficial SNV/DER)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="116"/>
        <source>State (UF)</source>
        <translation>Estado (UF)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="304"/>
        <source>Assignment</source>
        <translation>Alocação</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="310"/>
        <source>OD matrix</source>
        <translation>Matriz OD</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="320"/>
        <source>Origin</source>
        <translation>Origem</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="330"/>
        <source>Destination</source>
        <translation>Destino</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="340"/>
        <source>Demand (veh/h)</source>
        <translation>Demanda (veíc/h)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="350"/>
        <source>Centroids</source>
        <translation>Centroides</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="360"/>
        <source>Traffic id</source>
        <translation>Id de tráfego</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="370"/>
        <source>Max connector (m)</source>
        <translation>Conector máx. (m)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="393"/>
        <source>Method</source>
        <translation>Método</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="404"/>
        <source>All-or-Nothing (no capacity restraint)</source>
        <translation>All-or-Nothing (sem restrição de capacidade)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="409"/>
        <source>Equilibrium MSA + BPR</source>
        <translation>Equilíbrio MSA + BPR</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="422"/>
        <source>Iterations</source>
        <translation>Iterações</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="442"/>
        <source>Gap tolerance</source>
        <translation>Tolerância de gap</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="270"/>
        <source>Compute capacity</source>
        <translation>Calcular capacidade</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="486"/>
        <source>Assign</source>
        <translation>Alocar</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="195"/>
        <source>HCM parameters (default, or override globally / by field)</source>
        <translation>Parâmetros HCM (padrão, ou sobrescritos globalmente / por campo)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="130"/>
        <source>Download area</source>
        <translation>Área de download</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="140"/>
        <source>Region</source>
        <translation>Região</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="414"/>
        <source>Equilibrium Frank-Wolfe + BPR</source>
        <translation>Equilíbrio Frank-Wolfe + BPR</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="150"/>
        <source>Sources</source>
        <translation>Fontes</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="160"/>
        <source>Download network</source>
        <translation>Baixar malha</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="43"/>
        <source>Output GeoPackage</source>
        <translation>GeoPackage de saída</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="185"/>
        <source>Capacity</source>
        <translation>Capacidade</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="510"/>
        <source>Calibration</source>
        <translation>Calibração</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="520"/>
        <source>Calibration with traffic counts (GEH)</source>
        <translation>Calibração com contagens de tráfego (GEH)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="526"/>
        <source>Assignment layer</source>
        <translation>Camada de alocação</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="536"/>
        <source>Count posts</source>
        <translation>Postos de contagem</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="546"/>
        <source>Count field</source>
        <translation>Campo da contagem</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="556"/>
        <source>Post id field</source>
        <translation>Campo de id do posto</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="566"/>
        <source>Max. snapping distance</source>
        <translation>Distância máxima de casamento</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="589"/>
        <source>Model → count factor</source>
        <translation>Fator modelo → contagem</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="633"/>
        <source>Calibrate</source>
        <translation>Calibrar</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="203"/>
        <source>Complementary data (optional)</source>
        <translation>Dados complementares (opcional)</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="209"/>
        <source>Complementary layer</source>
        <translation>Camada complementar</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="226"/>
        <source>Max. distance</source>
        <translation>Distância máxima</translation>
    </message>
    <message>
        <location filename="../traffic_panel_base.ui" line="245"/>
        <source> m</source>
        <translation> m</translation>
    </message>
</context>
<context>
    <name>TrafficAssignmentPanel</name>
    <message>
        <location filename="../traffic_panel.py" line="204"/>
        <source>no</source>
        <translation>não</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="204"/>
        <source>yes</source>
        <translation>sim</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="547"/>
        <source>Could not fetch the highway network from GisBR: {}</source>
        <translation>Falha ao obter a malha rodoviária do GisBR: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="650"/>
        <source>Could not clip the network to the study area ({}); using the full mesh.</source>
        <translation>Não foi possível recortar a malha pela área de estudo ({}); usando a malha completa.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="682"/>
        <source>The highway network is empty after clipping.</source>
        <translation>A malha rodoviária ficou vazia após o recorte.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="693"/>
        <source>{} of {} arcs dropped for null or invalid capacity.</source>
        <translation>{} de {} arcos descartados por capacidade nula ou inválida.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="698"/>
        <source>No arc has a valid capacity; check the HCM parameters.</source>
        <translation>Nenhum arco tem capacidade válida; revise os parâmetros HCM.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="716"/>
        <source>No centroid could be connected to the highway network (nearest node farther than {:.0f} m).</source>
        <translation>Nenhum centróide pôde ser conectado à malha rodoviária (nó mais próximo além de {:.0f} m).</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="842"/>
        <source>{} urban arc(s): HCM highway capacity does not apply to urban crossings — read those with care</source>
        <translation>{} arco(s) urbano(s): a capacidade HCM rodoviária não se aplica a travessias urbanas — leia esses trechos com ressalva</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1010"/>
        <source>Computing HCM capacity…</source>
        <translation>Calculando capacidade HCM…</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1033"/>
        <source>Capacity computed for {} directed arcs — {}</source>
        <translation>Capacidade calculada para {} arcos direcionados — {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1055"/>
        <source>The centroids layer has no usable geometry.</source>
        <translation>A camada de centróides não tem geometria utilizável.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1065"/>
        <source>Assigning traffic ({})…</source>
        <translation>Alocando tráfego ({})…</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1094"/>
        <source>No OD pair matches the connected centroids. Check that Origin, Destination and Traffic id use the same id scheme.</source>
        <translation>Nenhum par OD corresponde aos centróides conectados. Verifique se Origem, Destino e Id de tráfego usam o mesmo esquema de identificação.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1109"/>
        <source>Traffic assignment failed: {}</source>
        <translation>Falha ao executar a alocação de tráfego: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1119"/>
        <source>gap: n/a — AoN does not feed capacity back into cost, so v/c above 1 diagnoses overload, not equilibrium</source>
        <translation>gap: n/a — o AoN não realimenta a capacidade no custo, então v/c acima de 1 é diagnóstico de sobrecarga, não equilíbrio</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1123"/>
        <source>final gap: {:.4f} in {} iteration(s)</source>
        <translation>gap final: {:.4f} em {} iteração(ões)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1126"/>
        <source>{} matrix rows had unknown ids</source>
        <translation>{} linha(s) da matriz com ids desconhecidos</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1128"/>
        <source>{} pairs unreachable (disconnected network)</source>
        <translation>{} pares inalcançáveis (rede desconexa)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1134"/>
        <source>{} done: {} pairs allocated over {} arcs — {}</source>
        <translation>{} concluído: {} pares alocados sobre {} arcos — {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Centroid extent (+ radius)</source>
        <translation>Extensão dos centroides (+ raio)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Whole state</source>
        <translation>UF inteira</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Metropolitan area</source>
        <translation>Região Metropolitana</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Micro-region</source>
        <translation>Microrregião</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Meso-region</source>
        <translation>Mesorregião</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="96"/>
        <source>Health macro-region</source>
        <translation>Macrorregião de saúde</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="890"/>
        <source>Could not obtain region extent: {}</source>
        <translation>Não foi possível obter a extensão da região: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="611"/>
        <source>Could not reproject the highway network to a metric CRS: {}</source>
        <translation>Falha ao reprojetar a malha rodoviária para um CRS métrico: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="616"/>
        <source>Highway network reprojected from {} to {} for metric computations.</source>
        <translation>Malha rodoviária reprojetada de {} para {} para os cálculos métricos.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="562"/>
        <source>The {} layer is labelled {} (projected, metres) but its coordinates look like degrees. Set the layer CRS to the geographic one (e.g. EPSG:4326 or EPSG:4674) and run again.</source>
        <translation>A camada {} está rotulada {} (projetado, metros), mas as coordenadas parecem graus. Defina o SRC da camada como o geográfico (ex.: EPSG:4326 ou EPSG:4674) e rode de novo.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="570"/>
        <source>The {} layer is labelled {} (geographic, degrees) but its coordinates are out of the longitude/latitude range. Set the layer CRS to the projected one the coordinates are in and run again.</source>
        <translation>A camada {} está rotulada {} (geográfico, graus), mas as coordenadas estão fora da faixa de longitude/latitude. Defina o SRC da camada como o projetado em que as coordenadas estão e rode de novo.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="585"/>
        <source>highway network</source>
        <translation>malha rodoviária</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="599"/>
        <source>centroids</source>
        <translation>centroides</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="721"/>
        <source>{} centroid(s) not connected to the highway network (nothing within {:.0f} m): zones {}.</source>
        <translation>{} centroide(s) não conectado(s) à malha rodoviária (nada a até {:.0f} m): zonas {}.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="729"/>
        <source>{} connector(s) longer than {:.0f} m: zones {}. Check the centroids or the network clip.</source>
        <translation>{} conector(es) com mais de {:.0f} m: zonas {}. Confira os centroides ou o recorte da malha.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="737"/>
        <source>Zones {} are anchored to the same network node; trips between them use only the connectors.</source>
        <translation>As zonas {} estão ancoradas no mesmo nó da malha; as viagens entre elas usam só os conectores.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="744"/>
        <source>Zones {} are anchored to the same highway link ({}).</source>
        <translation>As zonas {} estão ancoradas no mesmo trecho rodoviário ({}).</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="751"/>
        <source>{} centroid(s) anchored to the nearest node because the nearest link was ambiguous: zones {}.</source>
        <translation>{} centroide(s) ancorado(s) no nó mais próximo porque o trecho mais próximo era ambíguo: zonas {}.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="922"/>
        <source>Could not download the highway network: {}</source>
        <translation>Não foi possível baixar a malha rodoviária: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="944"/>
        <source>Highway network downloaded: {} segment(s) from {} source(s) into {}</source>
        <translation>Malha rodoviária baixada: {} trecho(s) de {} fonte(s) em {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="951"/>
        <source> — per-source report in the Message Log</source>
        <translation> — relatório por fonte no Registro de Mensagens</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="956"/>
        <source>{}: {} segment(s) kept ({} downloaded, {} outside the area, {} removed whole, {} trimmed, {:.0f} m removed)</source>
        <translation>{}: {} trecho(s) mantido(s) ({} baixado(s), {} fora da área, {} removido(s) por inteiro, {} aparado(s), {:.0f} m removidos)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="878"/>
        <source>Could not obtain the boundary of the area: {}</source>
        <translation>Não foi possível obter o limite da área: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="895"/>
        <source>Desire Lines — downloading the highway network ({})</source>
        <translation>Desire Lines — baixando malha rodoviária ({})</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="905"/>
        <source>Downloading the highway network in the background…</source>
        <translation>Baixando a malha rodoviária em segundo plano…</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="919"/>
        <source>Download cancelled</source>
        <translation>Download cancelado</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="930"/>
        <source>Could not load the downloaded network from {}</source>
        <translation>Não foi possível carregar a malha baixada de {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="948"/>
        <source> — {} removed as duplicates, {} trimmed, {} stitched</source>
        <translation> — {} removido(s) por duplicidade, {} aparado(s), {} costurado(s)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="972"/>
        <source>Stitching: {} node-to-node, {} T</source>
        <translation>Costura: {} nó-nó, {} T</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="997"/>
        <source>Phase times: download {}, merge {:.1f}s, stitch {:.1f}s, layer {:.1f}s (total {:.1f}s)</source>
        <translation>Tempos por fase: download {}, junção {:.1f}s, costura {:.1f}s, camada {:.1f}s (total {:.1f}s)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1148"/>
        <source>Calibrating assignment…</source>
        <translation>Calibrando alocação…</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1162"/>
        <source>No valid count posts found.</source>
        <translation>Nenhum posto de contagem válido encontrado.</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1190"/>
        <source>without a link within {} m</source>
        <translation>sem trecho a até {} m</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1197"/>
        <source>met</source>
        <translation>atendido</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1197"/>
        <source>not met</source>
        <translation>não atendido</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1200"/>
        <source>Calibration: {n} posts{sem_link} — A {pct_a:.1f}% · A+B {pct_ab:.1f}% · %RMSE {rmse} — DNIT criterion (≥60% A, ≥95% A+B): {status} (factor {factor})</source>
        <translation>Calibração: {n} postos{sem_link} — A {pct_a:.1f}% · A+B {pct_ab:.1f}% · %RMSE {rmse} — critério DNIT (≥60% A, ≥95% A+B): {status} (fator {factor})</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1179"/>
        <source>Calibration failed: {}</source>
        <translation>Falha na calibração: {}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1216"/>
        <source>{} count posts ignored (null, non-numeric or negative count)</source>
        <translation>{} postos de contagem ignorados (contagem nula, não numérica ou negativa)</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="1223"/>
        <source>Post {}: count {}, modeled {}, GEH {:.2f}</source>
        <translation>Posto {}: contagem {}, modelado {}, GEH {:.2f}</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="171"/>
        <source>Parameter</source>
        <translation>Parâmetro</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="172"/>
        <source>Value where there is no data</source>
        <translation>Valor onde não há dado</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="225"/>
        <source>Fix</source>
        <translation>Fixar</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="174"/>
        <source>Layer field</source>
        <translation>Campo da camada</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="827"/>
        <source>parameters: {} official, {} complementary, {} default, {} set by the user</source>
        <translation>parâmetros: {} oficiais, {} complementares, {} padrão, {} definidos pelo usuário</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="839"/>
        <source>{} links with complementary data</source>
        <translation>{} trechos com dado complementar</translation>
    </message>
    <message>
        <location filename="../traffic_panel.py" line="979"/>
        <source>HCM fields filled from the official data: {}</source>
        <translation>Campos do HCM preenchidos pelo dado oficial: {}</translation>
    </message>
</context>
</TS>
