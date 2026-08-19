# Formatos de entrada

Esta página descreve os requisitos, especificações e convenções de todos os dados de entrada aceitos pelo plugin **Desire Lines**.

---

## 1. Matriz Origem/Destino (CSV)

A matriz OD é o arquivo CSV contendo os volumes de viagens ou fluxos entre pares de zonas.

### Formato Longo (Long Format)

É o **formato padrão** esperado pelas etapas de cálculo e alocação do plugin. Cada linha da tabela representa um único par Origem-Destino.

| Origem | Destino | Passageiros |
|---|---|---|
| 101 | 102 | 450.5 |
| 101 | 103 | 120.0 |
| 102 | 101 | 380.0 |
| 102 | 103 | 95.0 |

* **Origem:** Identificador numérico ou alfanumérico da zona de origem.
* **Destino:** Identificador numérico ou alfanumérico da zona de destino.
* **Valor / Fluxo:** Volume de demanda (passageiros, veículos, toneladas, etc.), representado por valor numérico (inteiro ou decimal).

!!! note "Nomes das colunas"
    Os nomes das colunas no arquivo CSV podem ser arbitrários, pois são selecionados pelos *comboboxes* da interface nas abas do plugin. Caso a matriz passe pela conversão automática a partir do formato largo, o plugin utilizará por padrão os nomes `Origem`, `Destino` e `Passageiros`.

---

### Formato Largo (Wide Format)

O formato largo (ou matricial) é a estrutura de tabela com uma coluna de origem e uma coluna para cada zona de destino.

| OD | 101 | 102 | 103 |
|---|---|---|---|
| **101** | 0 | 450.5 | 120.0 |
| **102** | 380.0 | 0 | 95.0 |
| **103** | 110.0 | 85.0 | 0 |

Para utilizar uma matriz em formato largo:

1. Na aba **Matriz Origem/Destino** ("Origin/Destination Matrix"), marque a opção **Formato da Matriz de Demanda de Viagens** (*Travel Demand Matrix format*).
2. A primeira coluna do CSV deve chamar-se obrigatoriamente **`OD`**.
3. As demais colunas representam os identificadores dos destinos.
4. Ao clicar em **Ler CSV** (*Read CSV*), o plugin realiza a conversão automática para formato longo utilizando a função `pandas.melt`, salva o arquivo `matrix_long.csv` no mesmo diretório do CSV original e carrega este último no GeoPackage de saída.

!!! warning "Dependência da biblioteca pandas"
    A conversão do formato largo para o formato longo depende da biblioteca `pandas` instalada no ambiente Python do QGIS. Se a biblioteca não estiver presente, uma mensagem de erro será exibida solicitando a sua instalação.

---

### Propriedades Técnicas de Leitura

Ao importar o arquivo CSV da matriz, o plugin utiliza o driver de texto delimitado nativo do QGIS com as seguintes configurações fixas:

* **Encoding (Codificação):** `windows-1252` (padrão de exportação CSV em sistemas Windows brasileiros).
* **Delimitador de campos:** Ponto e vírgula (`;`).
* **Tipo de Geometria:** Nenhuma (`geomType=none`).

---

### Tratamento de Inconsistências na Matriz

| Cenário / Inconsistência | Comportamento do Plugin |
|---|---|
| **Par Origem = Destino (Autopares)** | Descartados automaticamente (`WHERE origin != dest` nas consultas SQL e ignorados nos algoritmos de alocação). |
| **Pares duplicados na matriz** | Alocados cumulativamente (os fluxos de linhas repetidas para o mesmo par OD são somados na alocação). |
| **Zona de origem/destino ausente nos centroides** | O par OD não encontra correspondência geográfica, é registrado como não encontrado (`skipped` / `missing`) e contabilizado na barra de avisos ao final da alocação. |
| **Valores nulos ou inválidos no fluxo** | Linhas com valor de fluxo nulo ou não numérico são ignoradas durante o cálculo. |

---

## 2. Zonas de Tráfego e Centroides

### Camada de Zonas de Tráfego (Vetorial de Polígonos)

A camada de zonas de tráfego representa a divisão territorial da área de estudo em polígonos.

* **Tipo de Geometria:** Polígono (`Polygon`) ou Multipolígono (`MultiPolygon`).
* **Formatos Suportados:** GeoPackage (`.gpkg`), ESRI Shapefile (`.shp`) ou qualquer camada de polígono suportada pelo QGIS.
* **Atributo Obrigatório:** Pelo menos uma coluna contendo o identificador único da zona (*Traffic ID*).
* **Sistema de Referência de Coordenadas (CRS):** Qualquer CRS válido (geográfico ou projetado).

---

### Camada de Centroides (Vetorial de Pontos)

Os centroides são a representação pontual de cada zona de tráfego, servindo de nós de origem e destino nos cálculos de linhas de desejo e alocação de rede.

* **Tipo de Geometria:** Ponto (`Point`) ou Multiponto (`MultiPoint`).
* **Geração Automática:** Ao clicar em **Adicionar Centroides às Zonas de Tráfego** (*Add Centroids to Traffic Zones*) na primeira aba, o plugin executa o algoritmo nativo `native:centroids` com `ALL_PARTS=True` (gerando um centroide para cada parte de multipolígonos e herdando a tabela de atributos da camada de zonas).
* **Atributo Obrigatório:** Deve possuir o campo *Traffic ID* com valores coincidentes aos IDs presentes na matriz OD.

---

## 3. Malha Rodoviária (Aba 4 — Alocação em Rodovias)

Para a alocação de tráfego sobre redes reais (aba **Alocação em rodovias**), a camada de vias possui requisitos geométricos e de atributos específicos.

* **Tipo de Geometria:** Linha (`LineString`) ou Multilinhar (`MultiLineString`).
* **Origem dos Dados:** Camada vetorial de rodovias carregada no QGIS (ex.: SNV/DER) ou baixada diretamente via integração com o plugin **GISBR**.
* **Atributos de Entrada (Regra D7 — Proveniência):**
    * Os atributos da malha (número de faixas, tipo de pista, velocidade de fluxo livre, etc.) podem ser mapeados a partir de colunas existentes na camada.
    * Caso a camada não possua esses campos, o plugin aplica automaticamente parâmetros padrão alinhados às normas do DNIT e HCM, registrando a proveniência dos dados nos campos `src_*` da camada resultante.
* **Classificação de Escopo:** O procedimento calcula a capacidade rodoviária para trechos rurais/interurbanos. Segmentos inseridos em travessias urbanas são mantidos na rede mas marcados com `escopo = 'urbano'`.

Para mais detalhes sobre a proveniência dos parâmetros da malha viária, consulte a página [Parâmetros HCM](parametros-hcm.md).

---

## 4. Normalização de IDs de Zonas (`_zone_key`)

Uma causa comum de falha na associação entre tabelas de dados é a divergência de tipos de atributos (ex.: a matriz trazer o ID como número inteiro `101` e a camada de centroides carregar o ID como texto `"101"` ou flutuante `"101.0"`).

Para garantir compatibilidade total sem exigir conversão manual prévia pelo usuário, o plugin aplica internamente a função de normalização **`_zone_key`**:

```python
@staticmethod
def _zone_key(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return str(value).strip()
```

### Regras de Conversão do `_zone_key`:

1. **Valores nulos (`None`):** Retorna `None`.
2. **Inteiro ou String Numérica Inteira:** Tenta converter diretamente para `int` (ex.: `101` ou `"101"` vira `101`).
3. **Flutuante ou String com Ponto Decimal:** Se a conversão simples falhar, tenta converter para `float` e em seguida para `int` (ex.: `101.0` ou `"101.0"` vira `101`).
4. **Códigos Alfanuméricos:** Se não for possível converter para número, converte o valor para `string` e remove espaços em branco nas extremidades (ex.: `" ZONA_A "` vira `"ZONA_A"`).

Dessa forma, a comparação entre a chave da matriz e a chave dos centroides sempre funciona, independentemente de como o provedor de dados do QGIS ou o arquivo CSV interpretaram o tipo de dado.
