<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1">
<context>
    <name>DesireLines</name>
    <message>
        <location filename="../desirelines.py" line="178"/>
        <source>&amp;Desire Lines</source>
        <translation>&amp;Desire Lines</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="166"/>
        <source>Desire Lines</source>
        <translation>Desire Lines</translation>
    </message>
</context>
<context>
    <name>DesireLinesDialog</name>
    <message>
        <location filename="../desirelines_dialog.py" line="166"/>
        <source>Layer {!r} not found. {}</source>
        <translation>Camada {!r} não encontrada. {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="187"/>
        <source>Select a CSV matrix file first.</source>
        <translation>Selecione primeiro um arquivo CSV de matriz.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="192"/>
        <source>pandas is required for wide-to-long conversion. Install it in the QGIS Python environment and reload the plugin.</source>
        <translation>O pandas é necessário para a conversão de formato largo para longo. Instale-o no ambiente Python do QGIS e recarregue o plugin.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="220"/>
        <source>Select a vector file first.</source>
        <translation>Selecione primeiro um arquivo vetorial.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="225"/>
        <source>Layer failed to load!</source>
        <translation>Falha ao carregar a camada!</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="309"/>
        <source>Invalid layer or field name: {!r}. Use letters (including accents), digits, spaces, underscores, dots or hyphens — no quotes or semicolons.</source>
        <translation>Nome de camada ou campo inválido: {!r}. Use letras (inclusive acentuadas), dígitos, espaços, sublinhados, pontos ou hífens — sem aspas ou ponto e vírgula.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="349"/>
        <source>Generating desire lines…</source>
        <translation>Gerando linhas de desejo…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="482"/>
        <source>Need at least 3 valid centroids to build a Delaunay network.</source>
        <translation>São necessários pelo menos 3 centroides válidos para construir uma rede de Delaunay.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="494"/>
        <source>source CRS is already metric</source>
        <translation>o SRC de origem já é métrico</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="496"/>
        <source>auto UTM zone {} (EPSG:{})</source>
        <translation>zona UTM automática {} (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="499"/>
        <source>Brazil Albers (EPSG:{})</source>
        <translation>Albers Brasil (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="502"/>
        <source>could not determine a metric CRS automatically; reproject the centroids to a metric system (UTM) and try again</source>
        <translation>não foi possível determinar um SRC métrico automaticamente; reprojete os centroides para um sistema métrico (UTM) e tente novamente</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="534"/>
        <source>No OD pairs matched the centroid ids. Check that Origin, Destination and Traffic ID refer to the same id scheme.</source>
        <translation>Nenhum par OD correspondeu aos ids dos centroides. Verifique se Origem, Destino e ID de Tráfego usam o mesmo esquema de id.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="541"/>
        <source>Allocating (AoN over Delaunay)…</source>
        <translation>Alocando (AoN sobre Delaunay)…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="561"/>
        <source>{} unreachable (disconnected graph)</source>
        <translation>{} inacessível(is) (grafo desconectado)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1052"/>
        <source>{} matrix rows had unknown ids</source>
        <translation>{} linha(s) da matriz com ids desconhecidos</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="566"/>
        <source>{} skipped</source>
        <translation>{} ignorado(s)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="568"/>
        <source>AoN done: {} pairs allocated over {} edges using {}{}</source>
        <translation>AoN concluído: {} pares alocados em {} arestas usando {}{}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="635"/>
        <source>no</source>
        <translation>não</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="635"/>
        <source>yes</source>
        <translation>sim</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="652"/>
        <source>field:</source>
        <translation>campo:</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="800"/>
        <source>Could not fetch the highway network from GisBR: {}</source>
        <translation>Falha ao obter a malha rodoviária do GisBR: {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="833"/>
        <source>The highway network is empty after clipping.</source>
        <translation>A malha rodoviária ficou vazia após o recorte.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="844"/>
        <source>{} of {} arcs dropped for null or invalid capacity.</source>
        <translation>{} de {} arcos descartados por capacidade nula ou inválida.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="849"/>
        <source>No arc has a valid capacity; check the HCM parameters.</source>
        <translation>Nenhum arco tem capacidade válida; revise os parâmetros HCM.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="866"/>
        <source>No centroid could be connected to the highway network (nearest node farther than {:.0f} m).</source>
        <translation>Nenhum centróide pôde ser conectado à malha rodoviária (nó mais próximo além de {:.0f} m).</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="871"/>
        <source>{} centroid(s) not connected to the highway network.</source>
        <translation>{} centróide(s) não conectados à malha rodoviária.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="928"/>
        <source>parameters: {} official, {} default, {} set by the user</source>
        <translation>parâmetros: {} de dado oficial, {} do padrão, {} definidos pelo usuário</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="933"/>
        <source>{} urban arc(s): HCM highway capacity does not apply to urban crossings — read those with care</source>
        <translation>{} arco(s) urbano(s): a capacidade HCM rodoviária não se aplica a travessias urbanas — leia esses trechos com ressalva</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="944"/>
        <source>Computing HCM capacity…</source>
        <translation>Calculando capacidade HCM…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="964"/>
        <source>Capacity computed for {} directed arcs — {}</source>
        <translation>Capacidade calculada para {} arcos direcionados — {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="986"/>
        <source>The centroids layer has no usable geometry.</source>
        <translation>A camada de centróides não tem geometria utilizável.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="997"/>
        <source>Assigning traffic ({})…</source>
        <translation>Alocando tráfego ({})…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1022"/>
        <source>No OD pair matches the connected centroids. Check that Origin, Destination and Traffic id use the same id scheme.</source>
        <translation>Nenhum par OD corresponde aos centróides conectados. Verifique se Origem, Destino e Id de tráfego usam o mesmo esquema de identificação.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1035"/>
        <source>Traffic assignment failed: {}</source>
        <translation>Falha ao executar a alocação de tráfego: {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1045"/>
        <source>gap: n/a — AoN does not feed capacity back into cost, so v/c above 1 diagnoses overload, not equilibrium</source>
        <translation>gap: n/a — o AoN não realimenta a capacidade no custo, então v/c acima de 1 é diagnóstico de sobrecarga, não equilíbrio</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1049"/>
        <source>final gap: {:.4f} in {} iteration(s)</source>
        <translation>gap final: {:.4f} em {} iteração(ões)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1054"/>
        <source>{} pairs unreachable (disconnected network)</source>
        <translation>{} pares inalcançáveis (rede desconexa)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="1056"/>
        <source>{} done: {} pairs allocated over {} arcs — {}</source>
        <translation>{} concluído: {} pares alocados sobre {} arcos — {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="817"/>
        <source>Could not clip the network to the study area ({}); using the full mesh.</source>
        <translation>Não foi possível recortar a malha pela área de estudo ({}); usando a malha completa.</translation>
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
        <location filename="../desirelines_dialog_base.ui" line="704"/>
        <source>Centroids</source>
        <translation>Centroides</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="674"/>
        <source>Origin</source>
        <translation>Origem</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="434"/>
        <source>Traffic ID</source>
        <translation>ID de Tráfego</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="684"/>
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
    <message>
        <location filename="../desirelines_dialog_base.ui" line="550"/>
        <source>Alocação em rodovias</source>
        <translation>Alocação em rodovias</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="556"/>
        <source>The GisBR plugin is required to download the official highway network.</source>
        <translation>O plugin GisBR é necessário para baixar a malha rodoviária oficial.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="566"/>
        <source>Scope: rural/interurban highways (HCM ch. 12 and 15). Urban stretches are flagged escopo='urbano' — urban capacity follows a different procedure and is out of scope.</source>
        <translation>Escopo: rodovias rurais/interurbanas (HCM cap. 12 e 15). Trechos urbanos são marcados com escopo='urbano' — a capacidade em área urbana segue outro procedimento e está fora do escopo.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="576"/>
        <source>Network</source>
        <translation>Rede</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="582"/>
        <source>Use an existing layer</source>
        <translation>Usar uma camada existente</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="592"/>
        <source>Highway layer</source>
        <translation>Camada da malha rodoviária</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="602"/>
        <source>Link id field (optional)</source>
        <translation>Campo de id do link (opcional)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="616"/>
        <source>Download via GisBR (official SNV/DER network)</source>
        <translation>Baixar via GisBR (malha oficial SNV/DER)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="623"/>
        <source>State (UF)</source>
        <translation>Estado (UF)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="637"/>
        <source>Clip to the centroids extent (plus buffer)</source>
        <translation>Recortar pela extensão dos centróides (mais buffer)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="650"/>
        <source>HCM parameters (default, or override globally / by field)</source>
        <translation>Parâmetros HCM (padrão, ou sobrescritos globalmente / por campo)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="658"/>
        <source>Assignment</source>
        <translation>Alocação</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="664"/>
        <source>OD matrix</source>
        <translation>Matriz OD</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="694"/>
        <source>Demand (veh/h)</source>
        <translation>Demanda (veíc/h)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="714"/>
        <source>Traffic id</source>
        <translation>Id de tráfego</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="724"/>
        <source>Max connector (m)</source>
        <translation>Conector máx. (m)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="747"/>
        <source>Method</source>
        <translation>Método</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="755"/>
        <source>All-or-Nothing (no capacity restraint)</source>
        <translation>All-or-Nothing (sem restrição de capacidade)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="760"/>
        <source>Equilibrium MSA + BPR</source>
        <translation>Equilíbrio MSA + BPR</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="768"/>
        <source>Iterations</source>
        <translation>Iterações</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="788"/>
        <source>Gap tolerance</source>
        <translation>Tolerância de gap</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="832"/>
        <source>Compute capacity</source>
        <translation>Calcular capacidade</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog_base.ui" line="839"/>
        <source>Assign</source>
        <translation>Alocar</translation>
    </message>
</context>
</TS>
