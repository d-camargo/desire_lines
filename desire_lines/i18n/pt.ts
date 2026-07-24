<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1">
<context>
    <name>DesireLines</name>
    <message>
        <location filename="../desirelines.py" line="180"/>
        <source>&amp;Desire Lines</source>
        <translation>&amp;Desire Lines</translation>
    </message>
    <message>
        <location filename="../desirelines.py" line="168"/>
        <source>Desire Lines</source>
        <translation>Desire Lines</translation>
    </message>
</context>
<context>
    <name>DesireLinesDialog</name>
    <message>
        <location filename="../desirelines_dialog.py" line="136"/>
        <source>Layer {!r} not found. {}</source>
        <translation>Camada {!r} não encontrada. {}</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="157"/>
        <source>Select a CSV matrix file first.</source>
        <translation>Selecione primeiro um arquivo CSV de matriz.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="162"/>
        <source>pandas is required for wide-to-long conversion. Install it in the QGIS Python environment and reload the plugin.</source>
        <translation>O pandas é necessário para a conversão de formato largo para longo. Instale-o no ambiente Python do QGIS e recarregue o plugin.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="190"/>
        <source>Select a vector file first.</source>
        <translation>Selecione primeiro um arquivo vetorial.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="195"/>
        <source>Layer failed to load!</source>
        <translation>Falha ao carregar a camada!</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="279"/>
        <source>Invalid layer or field name: {!r}. Use letters (including accents), digits, spaces, underscores, dots or hyphens — no quotes or semicolons.</source>
        <translation>Nome de camada ou campo inválido: {!r}. Use letras (inclusive acentuadas), dígitos, espaços, sublinhados, pontos ou hífens — sem aspas ou ponto e vírgula.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="319"/>
        <source>Generating desire lines…</source>
        <translation>Gerando linhas de desejo…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="452"/>
        <source>Need at least 3 valid centroids to build a Delaunay network.</source>
        <translation>São necessários pelo menos 3 centroides válidos para construir uma rede de Delaunay.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="464"/>
        <source>source CRS is already metric</source>
        <translation>o SRC de origem já é métrico</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="466"/>
        <source>auto UTM zone {} (EPSG:{})</source>
        <translation>zona UTM automática {} (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="469"/>
        <source>Brazil Albers (EPSG:{})</source>
        <translation>Albers Brasil (EPSG:{})</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="472"/>
        <source>could not determine a metric CRS automatically; reproject the centroids to a metric system (UTM) and try again</source>
        <translation>não foi possível determinar um SRC métrico automaticamente; reprojete os centroides para um sistema métrico (UTM) e tente novamente</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="504"/>
        <source>No OD pairs matched the centroid ids. Check that Origin, Destination and Traffic ID refer to the same id scheme.</source>
        <translation>Nenhum par OD correspondeu aos ids dos centroides. Verifique se Origem, Destino e ID de Tráfego usam o mesmo esquema de id.</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="511"/>
        <source>Allocating (AoN over Delaunay)…</source>
        <translation>Alocando (AoN sobre Delaunay)…</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="531"/>
        <source>{} unreachable (disconnected graph)</source>
        <translation>{} inacessível(is) (grafo desconectado)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="534"/>
        <source>{} matrix rows had unknown ids</source>
        <translation>{} linha(s) da matriz com ids desconhecidos</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="536"/>
        <source>{} skipped</source>
        <translation>{} ignorado(s)</translation>
    </message>
    <message>
        <location filename="../desirelines_dialog.py" line="538"/>
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
        <location filename="../test/test_translations.py" line="44"/>
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
</TS>
