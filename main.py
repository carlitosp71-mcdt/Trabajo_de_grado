import hands
import dds
import pandas as pd
import os

# Definir los partners
partners = {
    'N': 'S',
    'S': 'N',
    'E': 'W',
    'W': 'E'
}


oponente_derecha = {
    'N': 'E',
    'E': 'S',
    'S': 'W',
    'W': 'N'
}

oponente_izquierda = {   
    'N': 'W',    
    'W': 'S',
    'S': 'E', 
    'E': 'N'
}

def CompareTable(table, handno):
    for suit in range(dds.DDS_STRAINS):
        for pl in range(4):
            if table.contents.resTable[suit][pl] != hands.DDtable[handno][4 * suit + pl]:
                return False
    return True

#Genera el dataframe de los resultados de los cálculos
def GenerarDF(table, handno,df):
    # Acceder a los resultados de NT una sola vez
    nt_res = table.contents.resTable[4]  
    all_player_data = [] 
    
    for i, player in enumerate(["N", "E", "S", "W"]):
        player_data = {
            "Tablero": handno + 1,
            "Jugador": player,
            "NT_Bazas": nt_res[i],  # Valor NT para el jugador actual
            "Ss_Bazas": table.contents.resTable[0][i],  # Spades
            "Hs_Bazas": table.contents.resTable[1][i],  # Hearts
            "Ds_Bazas": table.contents.resTable[2][i],  # Diamonds
            "Cs_Bazas": table.contents.resTable[3][i],  # Clubs
        }
        all_player_data.append(player_data)
    df_results = pd.concat([df, pd.DataFrame(all_player_data)], ignore_index=True)
    return df_results

#Merge de dataframe
def UnificarDF(df, df_resultdCon, nombre_csv):
    df_unificado = pd.merge(df, df_resultdCon, on=['Tablero', 'Jugador'], how='inner')
    df_unificado.to_csv(nombre_csv, index=False)
    return df_unificado

def UnificarDFJugador(df, df_resultdCon, nombre_csv):
    df_unificadoJugador = pd.merge(df, df_resultdCon, on=['Tablero', 'Jugador'], how='inner')
    
    # Agregar columnas de conteo de cartas por palo
    df_unificadoJugador['ConteoS'] = df_unificadoJugador['Ss'].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
    df_unificadoJugador['ConteoH'] = df_unificadoJugador['Hs'].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
    df_unificadoJugador['ConteoD'] = df_unificadoJugador['Ds'].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
    df_unificadoJugador['ConteoC'] = df_unificadoJugador['Cs'].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
    
    # Calcular HCP total para cada mano
    def calcular_hcp_total(row):
        valor_honor = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
        hcp_total = 0
        
        # Calcular HCP para cada palo
        for palo in ['Ss', 'Hs', 'Ds', 'Cs']:
            cartas = str(row[palo]) if pd.notna(row[palo]) else ''
            for carta in cartas:
                hcp_total += valor_honor.get(carta.upper(), 0)
        
        return hcp_total
    
    df_unificadoJugador['HCP_Total'] = df_unificadoJugador.apply(calcular_hcp_total, axis=1)
    
    df_unificadoJugador.to_csv(nombre_csv, index=False)
    return df_unificadoJugador

# Función para determinar la vulnerabilidad en función del tablero y el jugador
def Consultar_Vulnerabilidad_Declarante(tablero, jugador):
    """
    Determina si un jugador es vulnerable en un tablero específico.
    tablero: Número del tablero (1, 2, 3, ...).
    jugador: "NS" (Norte-Sur) o "EW" (Este-Oeste).
    """
    declarers = ['N', 'E', 'S', 'W']
    tablero_num = int(tablero)  # Asegurar que sea un número

    residuo = (tablero_num - 1) % 4  # -1 para empezar desde la mano 1
    declarante= declarers[residuo]

    # Definir vulnerabilidad según el patrón de 16 tableros
    vulnerabilidad = {
        1: {"NS": False, "EW": False},
        2: {"NS": False, "EW": True},
        3: {"NS": True, "EW": False},
        4: {"NS": True, "EW": True},
        5: {"NS": False, "EW": True}, #repite el de 2
        6: {"NS": True, "EW": False}, #repite el de 3
        7: {"NS": True, "EW": True}, #repite el de 4
        8: {"NS": False, "EW": False}, #repite el de 1
        9: {"NS": True, "EW": False},#repite el de 3
        10: {"NS": True, "EW": True}, #repite el de 4
        11: {"NS": False, "EW": False},# repite el de 1
        12: {"NS": False, "EW": True}, #epite el de 2
        13: {"NS": True, "EW": True}, #repite el de 4
        14: {"NS": False, "EW": False},# repite el de 1
        15: {"NS": False, "EW": True}, #repite el de 2
        16: {"NS": True, "EW": False}# repite el de 3
    }  

        # Si el tablero es mayor a 16, se repite el patrón
    if tablero_num > 16:
        mano_relativa = ((tablero_num) % 16) + 1
    else:
        mano_relativa = tablero_num
    esVulnerable = vulnerabilidad[mano_relativa][jugador]
    return esVulnerable, declarante


def Calcular_HCP(S, H, D, C):
    import pandas as pd

    valor_honor = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}

    # Si alguno de los palos es NaN o vacío, lo convertimos a cadena vacía segura
    S = S if pd.notna(S) else ''
    H = H if pd.notna(H) else ''
    D = D if pd.notna(D) else ''
    C = C if pd.notna(C) else ''

    # Verificar si todos los palos están vacíos
    if all(len(palo.strip()) == 0 for palo in [S, H, D, C]):
        return {
            "HCP": 0,
            "Distribucion": {"S": 0, "H": 0, "D": 0, "C": 0},
            "TipoMano": "0",
            "PuntosLongitud": 0,
            "TotalPuntos": 0
        }

    # 1. Calcular puntos de honor
    puntos_honor = 0
    for palo in [S, H, D, C]:
        for carta in palo:
            puntos_honor += valor_honor.get(carta.upper(), 0)

    # 2. Evaluar distribución de la mano
    distribucion = {
        'S': len(S),
        'H': len(H),
        'D': len(D),
        'C': len(C)
    }
    max_palo = max(distribucion, key=distribucion.get)
    max_longitud = distribucion[max_palo]

    # 3. Clasificación de la mano
    longitudes = sorted(distribucion.values())
    #Regular: combinaciones comunes en manos balanceadas.
    es_regular = longitudes in [[4, 3, 3, 3], [4, 4, 3, 2], [5, 3, 3, 2]]
    #Bicolor: tiene dos palos con al menos 4 cartas y uno de ellos con mínimo 5.
    es_bicolor = any(v >= 5 for v in distribucion.values()) and len([v for v in distribucion.values() if v >= 4]) == 2
    #Unicolor: tiene 6 o más en un solo palo.
    es_unicolor = max_longitud >= 6
    #Si no cumple nada, es "Otro".
    tipo_mano = "Regular" if es_regular else "Bicolor" if es_bicolor else "Unicolor" if es_unicolor else "Otro"

    # 4. Puntos por longitud
    #Por cada palo con 5 o más cartas, suma 1 punto.
    puntos_longitud = sum(1 for v in distribucion.values() if v >= 5)

    # 5. Total de puntos
    #puntos_totales = puntos_honor + puntos_longitud

    return puntos_honor

# Función para hallar el valor esperado
def Determinar_Vulnerabilidad_HCP():
    archivo_csv = 'df_manosCalcular.csv'
    dfManos = pd.read_csv(archivo_csv, dtype={"Jugador": str})  # Leer CSV
    
    # Convertir "Tablero" a int
    dfManos["Tablero"] = dfManos["Tablero"].astype(int)

    resultados = []
    
    for _, fila in dfManos.iterrows():
        tablero = fila["Tablero"]
        jugador = fila["Jugador"].strip()

        # Determinar si el jugador es Norte-Sur o Este-Oeste
        if jugador in ["N", "S"]:
            grupo_jugador = "NS"
        elif jugador in ["E", "W"]:
            grupo_jugador = "EW"
        else:
            continue  # Si el jugador no es válido, omitir

        # Obtener vulnerabilidad real
        es_vulnerable, declarante = Consultar_Vulnerabilidad_Declarante(tablero, grupo_jugador)
        
        # Obtener cartas del jugador
        S = fila["Ss"]  # Picas
        H = fila["Hs"]  # Corazones
        D = fila["Ds"]  # Diamantes
        C = fila["Cs"]  # Tréboles

        # Calcular puntos de honor
        hcp = Calcular_HCP(S, H, D, C)

        fila_resultado = {
            "Tablero": tablero,
            "Jugador": jugador,
            "Vulnerable": "1" if es_vulnerable else "0",#1: vulnerable , 0: no vulnerable
            "HCP": hcp,
            "Declarante": declarante
        }
        resultados.append(fila_resultado)
 
    df_resultadoManos = pd.DataFrame(resultados)
    return df_resultadoManos


# Función para hallar el valor esperado
def CalcularPuntos_Honor(dealer, vulnerable):
    archivo_csv = 'df_manosCalcular.csv'
    dfManos = pd.read_csv(archivo_csv, dtype={"Jugador": str})  # Leer CSV
    
    # Convertir "Tablero" a int
    dfManos["Tablero"] = dfManos["Tablero"].astype(int)

    resultados = []
    
    for _, fila in dfManos.iterrows():
        tablero = fila["Tablero"]
        jugador = fila["Jugador"].strip()
   
        # Obtener cartas del jugador
        S = fila["Ss"]  # Picas
        H = fila["Hs"]  # Corazones
        D = fila["Ds"]  # Diamantes
        C = fila["Cs"]  # Tréboles

        # Calcular puntos de honor
        hcp = Calcular_HCP(S, H, D, C)

        fila_resultado = {
            "Tablero": tablero,
            "Jugador": jugador,
            "Vulnerable": vulnerable,#"1" if es_vulnerable else "0",#1: vulnerable , 0: no vulnerable
            "HCP": hcp,
            "Dealer": dealer
        }
        resultados.append(fila_resultado)
 
    df_resultadoManos = pd.DataFrame(resultados)

    #df_resultadoManos.to_csv('df_vulnerabilidad.csv', index=False)
    return df_resultadoManos

def GenerarDfManosCalculadas(dealer, vulnerable,jugador):
    # Leer CSV y convertir tipos de datos
    dfManos = pd.read_csv('df_manosCalcular.csv', dtype={"Jugador": str})
    dfManos["Tablero"] = dfManos["Tablero"].astype(int)
    
    # Crear DataFrame directamente con los valores constantes
    df_resultadoManos = pd.DataFrame({
        "Tablero": dfManos["Tablero"],
        "Jugador": dfManos["Jugador"].str.strip(),
        "Vulnerable": vulnerable,
        "Dealer": dealer,
        "Declarante": jugador
    })
    
    return df_resultadoManos

def Calcular_ContratosPuntajes(dfUnificadoManosCal_Vul, dfScores, fila, jugador, palos, columna_score, apuesta, idx):
    """
    Calcula los contratos y puntajes para cada palo y el contrato óptimo global tomando el puntaje maximo de cada palo.
    Versión optimizada para mejor rendimiento.
    """
    mejores_por_palo = []
    
    # Pre-calcular el mapeo de palos para evitar búsquedas repetitivas
    mapeo_palos = {
        9: "NT_Bazas",
        7: "Ss_Bazas",
        5: "Hs_Bazas",
        3: "Ds_Bazas",
        1: "Cs_Bazas"
    }
    
    # Pre-calcular los scores por bazas y contrato para cada palo usando un diccionario
    scores_cache = {}
    for palo_texto, palo_valor in palos.items():
        columna_bazas = f"{palo_texto}_Bazas"
        if columna_bazas not in dfUnificadoManosCal_Vul.columns:
            continue

        bazas = fila[columna_bazas]
        if pd.isnull(bazas):
            bazas = 0

        # Filtrar scores para este palo y bazas una sola vez
        df_filtrado = dfScores[
            (dfScores["Tricks"] == bazas) & 
            (dfScores["Contract"] % 10 == apuesta)
        ].copy()
        
        # Pre-calcular scores para este palo
        df_filtrado["Score"] = df_filtrado[columna_score].fillna(0).astype(int)
        df_filtrado["Nivel"] = df_filtrado["Contract"] // 100
        df_filtrado["Palo"] = (df_filtrado["Contract"] // 10) % 10
        
        # Filtrar por el palo actual
        df_por_palo = df_filtrado[df_filtrado["Palo"] == palo_valor].copy()
        
        if not df_por_palo.empty:
            # Obtener el mejor contrato para este palo de manera vectorizada
            mejor_fila = df_por_palo.sort_values(by=["Score", "Nivel"], ascending=[False, False]).iloc[0]
            mejor_contract = int(mejor_fila["Contract"])
            mejor_score = int(mejor_fila["Score"])

            # Guardar el mejor contrato por palo
            col_contrato = f"{palo_texto}_Contrato_Optimo"
            col_puntaje = f"{palo_texto}_PuntajeContrato_Optimo"
            dfUnificadoManosCal_Vul.at[idx, col_contrato] = mejor_contract
            dfUnificadoManosCal_Vul.at[idx, col_puntaje] = mejor_score

            mejores_por_palo.append((mejor_contract, mejor_score))

            # Actualizar scores para todos los contratos de este palo de manera vectorizada
            for contrato in df_filtrado['Contract'].unique():
                palo_contrato = (contrato // 10) % 10
                
                if palo_contrato in mapeo_palos:
                    columna_bazas = mapeo_palos[palo_contrato]
                    bazas = fila[columna_bazas] if pd.notna(fila[columna_bazas]) else 0
                    
                    if bazas == 0:
                        score = 0
                    else:
                        # Usar el cache de scores si está disponible
                        if bazas in scores_cache and contrato in scores_cache[bazas]:
                            score = scores_cache[bazas][contrato]['vul' if columna_score == 'Score vul' else 'non_vul']
                        else:
                            df_filtrado_score = dfScores[
                                (dfScores["Contract"] == contrato) & 
                                (dfScores["Tricks"] == bazas)
                            ]
                            score = int(df_filtrado_score[columna_score].iloc[0]) if not df_filtrado_score.empty else 0

                    cod_col = str(contrato)
                    if cod_col in dfUnificadoManosCal_Vul.columns:
                        dfUnificadoManosCal_Vul.at[idx, cod_col] = score

    # Obtener el mejor contrato global de manera vectorizada
    if mejores_por_palo:
        df_mejores = pd.DataFrame(mejores_por_palo, columns=["Contract", "Score"])
        df_mejores["Nivel"] = df_mejores["Contract"] // 100
        fila_optima = df_mejores.sort_values(by=["Score", "Nivel"], ascending=[False, False]).iloc[0]

        contrato_optimo = int(fila_optima["Contract"])
        puntaje_optimo = int(fila_optima["Score"])
        
        # Obtener las bazas para el contrato óptimo
        palo_optimo = (contrato_optimo // 10) % 10
        columna_bazas = mapeo_palos.get(palo_optimo)
        tricks = int(fila[columna_bazas]) if columna_bazas and pd.notna(fila[columna_bazas]) else 0

        # Guardar contrato óptimo general
        dfUnificadoManosCal_Vul.at[idx, f"Contrato_Optimo_Mano_{apuesta}"] = contrato_optimo
        #MAXIO VALOR DE LAS COLUMNAS
        dfUnificadoManosCal_Vul.at[idx, f"PuntajeContrato_Optimo_Mano_{apuesta}"] = puntaje_optimo
        dfUnificadoManosCal_Vul.at[idx, f"Tricks_Optimo_Mano_{apuesta}"] = tricks

    return dfUnificadoManosCal_Vul


def Calcular_ContratosPuntajes_Vectorizado(dfUnificadoManosCal_Vul, dfScores, palos, es_vulnerable_por_fila, apuesta):
    """
    Versión vectorizada de Calcular_ContratosPuntajes que elimina el bucle iterrows().
    Procesa todas las filas de forma vectorizada usando operaciones de pandas.
    """
    # Pre-calcular el mapeo de palos
    mapeo_palos = {
        9: "NT_Bazas",
        7: "Ss_Bazas", 
        5: "Hs_Bazas",
        3: "Ds_Bazas",
        1: "Cs_Bazas"
    }
    
    # Generar todos los contratos candidatos para esta apuesta
    contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta)
                        for nivel in range(1, 8)
                        for palo in palos.values()]
    
    # Procesar cada palo de forma vectorizada
    for palo_texto, palo_valor in palos.items():
        columna_bazas = f"{palo_texto}_Bazas"
        if columna_bazas not in dfUnificadoManosCal_Vul.columns:
            continue
            
        # Obtener bazas para todas las filas de una vez
        bazas_series = dfUnificadoManosCal_Vul[columna_bazas].fillna(0)
        
        # Filtrar scores para este palo y todas las bazas de una vez
        # Calcular el palo del contrato dinámicamente como en el código original
        df_filtrado = dfScores[
            (dfScores["Contract"] % 10 == apuesta) &
            ((dfScores["Contract"] // 10) % 10 == palo_valor)
        ].copy()
        
        if df_filtrado.empty:
            continue
            
        # Pre-calcular scores
        df_filtrado["Score_vul"] = df_filtrado["Score vul"].fillna(0).astype(int)
        df_filtrado["Score_non_vul"] = df_filtrado["Score non vul"].fillna(0).astype(int)
        df_filtrado["Nivel"] = df_filtrado["Contract"] // 100
        
        # Para cada fila, encontrar el mejor contrato de forma vectorizada
        mejores_contratos = []
        mejores_puntajes = []
        
        for idx, bazas in enumerate(bazas_series):
            # Filtrar por bazas específicas
            df_bazas = df_filtrado[df_filtrado["Tricks"] == bazas]
            
            if not df_bazas.empty:
                # Obtener el mejor contrato para esta fila
                es_vulnerable = es_vulnerable_por_fila.iloc[idx]
                columna_score = "Score_vul" if es_vulnerable else "Score_non_vul"
                
                mejor_fila = df_bazas.sort_values(by=[columna_score, "Nivel"], ascending=[False, False]).iloc[0]
                mejor_contract = int(mejor_fila["Contract"])
                mejor_score = int(mejor_fila[columna_score])
                
                mejores_contratos.append(mejor_contract)
                mejores_puntajes.append(mejor_score)
            else:
                mejores_contratos.append(0)
                mejores_puntajes.append(0)
        
        # Asignar resultados de forma vectorizada
        col_contrato = f"{palo_texto}_Contrato_Optimo"
        col_puntaje = f"{palo_texto}_PuntajeContrato_Optimo"
        
        dfUnificadoManosCal_Vul[col_contrato] = mejores_contratos
        dfUnificadoManosCal_Vul[col_puntaje] = mejores_puntajes
        
        # Llenar información de cada contrato individual (como en el código original)
        for contrato in df_filtrado['Contract'].unique():
            palo_contrato = (contrato // 10) % 10
            
            if palo_contrato in mapeo_palos:
                columna_bazas_contrato = mapeo_palos[palo_contrato]
                if columna_bazas_contrato in dfUnificadoManosCal_Vul.columns:
                    bazas_contrato = dfUnificadoManosCal_Vul[columna_bazas_contrato].fillna(0)
                    
                    # Calcular scores para cada fila
                    scores_contrato = []
                    for idx, bazas in enumerate(bazas_contrato):
                        if bazas == 0:
                            score = 0
                        else:
                            df_filtrado_score = dfScores[
                                (dfScores["Contract"] == contrato) & 
                                (dfScores["Tricks"] == bazas)
                            ]
                            if not df_filtrado_score.empty:
                                es_vulnerable = es_vulnerable_por_fila.iloc[idx]
                                columna_score = "Score vul" if es_vulnerable else "Score non vul"
                                score = int(df_filtrado_score[columna_score].iloc[0])
                            else:
                                score = 0
                        scores_contrato.append(score)
                    
                    # Asignar scores de forma vectorizada
                    cod_col = str(contrato)
                    if cod_col in dfUnificadoManosCal_Vul.columns:
                        dfUnificadoManosCal_Vul[cod_col] = scores_contrato
    
    # Calcular el contrato óptimo global basado en el puntaje máximo de los contratos individuales de esta apuesta
    # Obtener las columnas de contratos individuales para esta apuesta específica
    contratos_individuales_apuesta = [str(nivel * 100 + palo * 10 + apuesta)
                                    for nivel in range(1, 8)
                                    for palo in palos.values()]
    
    # Filtrar solo las columnas que existen en el DataFrame
    columnas_contratos_existentes = [col for col in contratos_individuales_apuesta if col in dfUnificadoManosCal_Vul.columns]
    
    if columnas_contratos_existentes:
        # Obtener el DataFrame con solo las columnas de contratos individuales de esta apuesta
        df_contratos_individuales = dfUnificadoManosCal_Vul[columnas_contratos_existentes]
        
        # Encontrar el contrato con puntaje máximo para cada fila
        mejor_contrato_idx = df_contratos_individuales.idxmax(axis=1)
        puntaje_maximo = df_contratos_individuales.max(axis=1)
        
        # Asignar el puntaje máximo de los contratos individuales de esta apuesta
        dfUnificadoManosCal_Vul[f"Contrato_Optimo_Mano_{apuesta}"] = puntaje_maximo.astype(int)
        
        # Calcular el promedio de los valores de los contratos individuales de esta apuesta
        promedio_contratos = df_contratos_individuales.mean(axis=1)
        dfUnificadoManosCal_Vul[f"PuntajeContrato_Optimo_Mano_{apuesta}"] = promedio_contratos.astype(int)
    
    return dfUnificadoManosCal_Vul

def Calcular_ContratosPuntajes_Vectorizado_SoloContratos(dfUnificadoManosCal_Vul, dfScores, palos, es_vulnerable_por_fila, apuesta):
    """
    Versión optimizada que solo calcula los contratos individuales (no recalcula contratos óptimos).
    Para apuestas 1 y 2, reutiliza los contratos óptimos calculados con apuesta 0.
    """
    # Pre-calcular el mapeo de palos
    mapeo_palos = {
        9: "NT_Bazas",
        7: "Ss_Bazas", 
        5: "Hs_Bazas",
        3: "Ds_Bazas",
        1: "Cs_Bazas"
    }
    
    # Generar todos los contratos candidatos para esta apuesta
    contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta)
                        for nivel in range(1, 8)
                        for palo in palos.values()]
    
    # Solo calcular contratos individuales, no recalcular contratos óptimos
    for palo_texto, palo_valor in palos.items():
        columna_bazas = f"{palo_texto}_Bazas"
        if columna_bazas not in dfUnificadoManosCal_Vul.columns:
            continue
            
        # Filtrar scores para este palo y todas las bazas de una vez
        df_filtrado = dfScores[
            (dfScores["Contract"] % 10 == apuesta) &
            ((dfScores["Contract"] // 10) % 10 == palo_valor)
        ].copy()
        
        if df_filtrado.empty:
            continue
        
        # Llenar información de cada contrato individual (como en el código original)
        for contrato in df_filtrado['Contract'].unique():
            palo_contrato = (contrato // 10) % 10
            
            if palo_contrato in mapeo_palos:
                columna_bazas_contrato = mapeo_palos[palo_contrato]
                if columna_bazas_contrato in dfUnificadoManosCal_Vul.columns:
                    bazas_contrato = dfUnificadoManosCal_Vul[columna_bazas_contrato].fillna(0)
                    
                    # Calcular scores para cada fila
                    scores_contrato = []
                    for idx, bazas in enumerate(bazas_contrato):
                        if bazas == 0:
                            score = 0
                        else:
                            df_filtrado_score = dfScores[
                                (dfScores["Contract"] == contrato) & 
                                (dfScores["Tricks"] == bazas)
                            ]
                            if not df_filtrado_score.empty:
                                es_vulnerable = es_vulnerable_por_fila.iloc[idx]
                                columna_score = "Score vul" if es_vulnerable else "Score non vul"
                                score = int(df_filtrado_score[columna_score].iloc[0])
                            else:
                                score = 0
                        scores_contrato.append(score)
                    
                    # Asignar scores de forma vectorizada
                    cod_col = str(contrato)
                    if cod_col in dfUnificadoManosCal_Vul.columns:
                        dfUnificadoManosCal_Vul[cod_col] = scores_contrato
    
    # Calcular el contrato óptimo global basado en el puntaje máximo de los contratos individuales de esta apuesta
    # Obtener las columnas de contratos individuales para esta apuesta específica
    contratos_individuales_apuesta = [str(nivel * 100 + palo * 10 + apuesta)
                                    for nivel in range(1, 8)
                                    for palo in palos.values()]
    
    # Filtrar solo las columnas que existen en el DataFrame
    columnas_contratos_existentes = [col for col in contratos_individuales_apuesta if col in dfUnificadoManosCal_Vul.columns]
    
    if columnas_contratos_existentes:
        # Obtener el DataFrame con solo las columnas de contratos individuales de esta apuesta
        df_contratos_individuales = dfUnificadoManosCal_Vul[columnas_contratos_existentes]
        
        # Encontrar el contrato con puntaje máximo para cada fila
        mejor_contrato_idx = df_contratos_individuales.idxmax(axis=1)
        puntaje_maximo = df_contratos_individuales.max(axis=1)
        
        # Asignar el puntaje máximo de los contratos individuales de esta apuesta
        dfUnificadoManosCal_Vul[f"Contrato_Optimo_Mano_{apuesta}"] = puntaje_maximo.astype(int)
        
        # Calcular el promedio de los valores de los contratos individuales de esta apuesta
        promedio_contratos = df_contratos_individuales.mean(axis=1)
        dfUnificadoManosCal_Vul[f"PuntajeContrato_Optimo_Mano_{apuesta}"] = promedio_contratos.astype(int)
    
    return dfUnificadoManosCal_Vul


def DeterminarContratos_OptimoAnt(dfUnificadoManosCal_Vul, apuesta, jugador):
    """
    Versión súper optimizada del método DeterminarContratos_Optimo.
    Procesa las 3 apuestas (0, 1, 2) de forma completamente vectorizada para reducir tiempos de procesamiento.
    Elimina el bucle iterrows() y usa operaciones vectorizadas de pandas.
    """
    # Optimizar la carga del CSV usando tipos específicos y cache
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scores_path = os.path.join(base_dir, "scores.csv")

    # Cache para los scores (cargar una sola vez)
    if not hasattr(DeterminarContratos_Optimo, '_scores_cache'):
        dfScores = pd.read_csv(scores_path, sep=";", dtype={
            'Contract': int,
            'Tricks': int,
            'Score vul': float,
            'Score non vul': float
        })
        dfScores.columns = dfScores.columns.str.strip()
        DeterminarContratos_Optimo._scores_cache = dfScores
    
    dfScores = DeterminarContratos_Optimo._scores_cache

    # Cache para palos
    palos = {'Cs': 1, 'Ds': 3, 'Hs': 5, 'Ss': 7, 'NT': 9}
    
    # Pre-calcular vulnerabilidad por fila (una sola vez)
    es_vulnerable_por_fila = (
        (dfUnificadoManosCal_Vul['Vulnerable'] == 'Both') |
        ((dfUnificadoManosCal_Vul['Vulnerable'] == 'N-S') & 
         (dfUnificadoManosCal_Vul['Jugador'].isin(['N', 'S']))) |
        ((dfUnificadoManosCal_Vul['Vulnerable'] == 'E-W') & 
         (dfUnificadoManosCal_Vul['Jugador'].isin(['E', 'W'])))
    )
    
    # Diccionario para almacenar DataFrames por apuesta
    dataframes_por_apuesta = {}
    
    # Pre-calcular todas las columnas necesarias para las 3 apuestas
    # Las columnas de contratos óptimos son las mismas para todas las apuestas
    columnas_contratos_optimos = [f"{palo}_{tipo}" for palo in palos.keys() 
                                for tipo in ['Contrato_Optimo', 'PuntajeContrato_Optimo']]
    
    todas_contratos_candidatos = []
    todas_columnas_totales = []
    
    for apuesta_actual in [0, 1, 2]:
        contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta_actual)
                            for nivel in range(1, 8)
                            for palo in palos.values()]
        
        columnas_totales = contratos_candidatos + [
            f"Contrato_Optimo_Mano_{apuesta_actual}", 
            f"PuntajeContrato_Optimo_Mano_{apuesta_actual}", 
        ]
        
        todas_contratos_candidatos.extend(contratos_candidatos)
        todas_columnas_totales.extend(columnas_totales)
    
    # Agregar todas las columnas faltantes de una vez (sin duplicar las de contratos óptimos)
    todas_columnas_totales.extend(columnas_contratos_optimos)
    columnas_faltantes = [col for col in todas_columnas_totales if col not in dfUnificadoManosCal_Vul.columns]
    if columnas_faltantes:
        dfUnificadoManosCal_Vul = pd.concat([
            dfUnificadoManosCal_Vul,
            pd.DataFrame(0, index=dfUnificadoManosCal_Vul.index, columns=columnas_faltantes)
        ], axis=1)

    # Procesar las 3 apuestas de forma vectorizada
    for apuesta_actual in [0, 1, 2]:
        #print(f"Procesando apuesta {apuesta_actual} de forma vectorizada...")       
        if apuesta_actual == 0:
            # Para la apuesta 0, calcular contratos óptimos y posicionarlos después de Declarante_y
            dfUnificadoManosCal_Vul = Calcular_ContratosPuntajes_Vectorizado(
                dfUnificadoManosCal_Vul, 
                dfScores, 
                palos, 
                es_vulnerable_por_fila, 
                apuesta_actual
            )
            
            # Reorganizar columnas para posicionar contratos óptimos después de Declarante_y
            if 'Declarante_y' in dfUnificadoManosCal_Vul.columns:
                columnas_contratos_optimos_existentes = [col for col in columnas_contratos_optimos if col in dfUnificadoManosCal_Vul.columns]
                
                if columnas_contratos_optimos_existentes:
                    # Obtener todas las columnas
                    todas_las_columnas = list(dfUnificadoManosCal_Vul.columns)
                    
                    # Encontrar la posición de Declarante_y
                    posicion_declarante_y = todas_las_columnas.index('Declarante_y')
                    
                    # Remover las columnas de contratos óptimos de su posición actual
                    columnas_sin_contratos_optimos = [col for col in todas_las_columnas if col not in columnas_contratos_optimos_existentes]
                    
                    # Reorganizar: antes de Declarante_y + Declarante_y + contratos óptimos + después de Declarante_y
                    columnas_antes = columnas_sin_contratos_optimos[:posicion_declarante_y + 1]
                    columnas_despues = columnas_sin_contratos_optimos[posicion_declarante_y + 1:]
                    
                    # Crear el nuevo orden de columnas
                    nuevas_columnas = columnas_antes + columnas_contratos_optimos_existentes + columnas_despues
                    
                    # Reorganizar el DataFrame
                    dfUnificadoManosCal_Vul = dfUnificadoManosCal_Vul[nuevas_columnas]
        else:
            # Para apuestas 1 y 2, solo calcular contratos individuales (no recalcular contratos óptimos)
            dfUnificadoManosCal_Vul = Calcular_ContratosPuntajes_Vectorizado_SoloContratos(
                dfUnificadoManosCal_Vul, 
                dfScores, 
                palos, 
                es_vulnerable_por_fila, 
                apuesta_actual
            )

        # Verificar que las columnas necesarias existan antes de hacer el groupby
        columnas_requeridas = ['Jugador', 'Tablero', f'Contrato_Optimo_Mano_{apuesta_actual}', f'PuntajeContrato_Optimo_Mano_{apuesta_actual}']
        if not all(col in dfUnificadoManosCal_Vul.columns for col in columnas_requeridas):
            raise ValueError(f"Faltan columnas requeridas en el DataFrame. Columnas necesarias: {columnas_requeridas}")

        # Calcular promedios de manera vectorizada
        promedios_por_jugador_tablero = dfUnificadoManosCal_Vul.groupby(['Jugador', 'Tablero']).agg({
            f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
            f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
        }).reset_index()

        # Calcular promedios de partners y oponentes de manera vectorizada
        for jugador_actual in dfUnificadoManosCal_Vul['Jugador'].unique():
            partner = partners[jugador_actual]
            oponentes = [j for j in dfUnificadoManosCal_Vul['Jugador'].unique() 
                        if j != jugador_actual and j != partner]
            
            # Calcular promedios de partners
            if partner in promedios_por_jugador_tablero['Jugador'].unique():
                df_partners = promedios_por_jugador_tablero[
                    promedios_por_jugador_tablero['Jugador'].isin([jugador_actual, partner])
                ].groupby('Tablero').agg({
                    f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
                    f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
                }).reset_index()
                
            # Calcular promedios de oponentes
            df_oponentes = promedios_por_jugador_tablero[
                promedios_por_jugador_tablero['Jugador'].isin(oponentes)
            ].groupby('Tablero').agg({
                f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
                f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
            }).reset_index()
            
        # Calcular valores esperados de manera vectorizada
        contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta_actual)
                            for nivel in range(1, 8)
                            for palo in palos.values()]
        
        valor_esperado_contratos = {}
        for jugador_actual in dfUnificadoManosCal_Vul['Jugador'].unique():
            df_jugador = dfUnificadoManosCal_Vul[dfUnificadoManosCal_Vul['Jugador'] == jugador_actual]
            promedios_contratos = {}
            
            # Calcular promedios de manera vectorizada
            for contrato in contratos_candidatos:
                if contrato in df_jugador.columns:
                    promedio = df_jugador[contrato].mean()
                    promedios_contratos[contrato] = promedio
            
            valor_esperado_contratos[jugador_actual] = promedios_contratos

        # Crear y retornar el DataFrame de valores esperados
        df_valor_esperado = pd.DataFrame()
        df_valor_esperado = CalcularValorEsperadoFinal(
            df_valor_esperado,
            dfUnificadoManosCal_Vul,
            valor_esperado_contratos,
            apuesta_actual
        )
        
        # Guardar DataFrames por apuesta
        dataframes_por_apuesta[f'dfUnificadoManosCal_Vul_{apuesta_actual}'] = dfUnificadoManosCal_Vul.copy()
        dataframes_por_apuesta[f'df_valor_esperado_{apuesta_actual}'] = df_valor_esperado.copy()
        
        # Generar CSV inmediatamente para dfUnificadoManosCal_Vul
        df_temp = dfUnificadoManosCal_Vul.copy()
        df_temp.fillna(0, inplace=True)
        df_temp.to_csv(f"df_ManosCalculadas_ContratoOptimo_{apuesta_actual}.csv", float_format="%.0f", index=False)
        #print(f"df_ManosCalculadas_ContratoOptimo_{apuesta_actual}.csv generado exitosamente")
        
        #print(f"DataFrames guardados para apuesta {apuesta_actual}")
    
    # Unificar los DataFrames de valor esperado en memoria (más eficiente)
    df_valor_esperado_unificado = UnificarDataFramesValorEsperado(dataframes_por_apuesta)
    
    return df_valor_esperado_unificado


def DeterminarContratos_Optimo(dfUnificadoManosCal_Vul, apuesta, jugador,declarante):
    """
    Versión súper optimizada del método DeterminarContratos_Optimo.
    Procesa las 3 apuestas (0, 1, 2) de forma completamente vectorizada para reducir tiempos de procesamiento.
    Elimina el bucle iterrows() y usa operaciones vectorizadas de pandas.
    """
    # Optimizar la carga del CSV usando tipos específicos y cache
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scores_path = os.path.join(base_dir, "scores.csv")

    # Cache para los scores (cargar una sola vez)
    if not hasattr(DeterminarContratos_Optimo, '_scores_cache'):
        dfScores = pd.read_csv(scores_path, sep=";", dtype={
            'Contract': int,
            'Tricks': int,
            'Score vul': float,
            'Score non vul': float
        })
        dfScores.columns = dfScores.columns.str.strip()
        DeterminarContratos_Optimo._scores_cache = dfScores
    
    dfScores = DeterminarContratos_Optimo._scores_cache

    # Cache para palos
    palos = {'Cs': 1, 'Ds': 3, 'Hs': 5, 'Ss': 7, 'NT': 9}
    
    # Pre-calcular vulnerabilidad por fila (una sola vez)
    es_vulnerable_por_fila = (
        (dfUnificadoManosCal_Vul['Vulnerable'] == 'Both') |
        ((dfUnificadoManosCal_Vul['Vulnerable'] == 'N-S') & 
         (dfUnificadoManosCal_Vul['Jugador'].isin(['N', 'S']))) |
        ((dfUnificadoManosCal_Vul['Vulnerable'] == 'E-W') & 
         (dfUnificadoManosCal_Vul['Jugador'].isin(['E', 'W'])))
    )
    
    # Diccionario para almacenar DataFrames por apuesta
    dataframes_por_apuesta = {}
    
    # Pre-calcular todas las columnas necesarias para las 3 apuestas
    # Las columnas de contratos óptimos son las mismas para todas las apuestas
    columnas_contratos_optimos = [f"{palo}_{tipo}" for palo in palos.keys() 
                                for tipo in ['Contrato_Optimo', 'PuntajeContrato_Optimo']]
    
    todas_contratos_candidatos = []
    todas_columnas_totales = []
    
    for apuesta_actual in [0, 1, 2]:
        contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta_actual)
                            for nivel in range(1, 8)
                            for palo in palos.values()]
        
        columnas_totales = contratos_candidatos + [
            f"Contrato_Optimo_Mano_{apuesta_actual}", 
            f"PuntajeContrato_Optimo_Mano_{apuesta_actual}", 
            #f"Tricks_Optimo_Mano_{apuesta_actual}"
        ]
        
        todas_contratos_candidatos.extend(contratos_candidatos)
        todas_columnas_totales.extend(columnas_totales)
    
    # Agregar todas las columnas faltantes de una vez (sin duplicar las de contratos óptimos)
    todas_columnas_totales.extend(columnas_contratos_optimos)
    columnas_faltantes = [col for col in todas_columnas_totales if col not in dfUnificadoManosCal_Vul.columns]
    if columnas_faltantes:
        dfUnificadoManosCal_Vul = pd.concat([
            dfUnificadoManosCal_Vul,
            pd.DataFrame(0, index=dfUnificadoManosCal_Vul.index, columns=columnas_faltantes)
        ], axis=1)

    # Procesar las 3 apuestas de forma vectorizada
    for apuesta_actual in [0, 1, 2]:   
        if apuesta_actual == 0:
            # Para la apuesta 0, calcular contratos óptimos y posicionarlos después de Declarante_y
            dfUnificadoManosCal_Vul = Calcular_ContratosPuntajes_Vectorizado(
                dfUnificadoManosCal_Vul, 
                dfScores, 
                palos, 
                es_vulnerable_por_fila, 
                apuesta_actual
            )
            
            # Reorganizar columnas para posicionar contratos óptimos después de Declarante_y
            if 'Declarante_y' in dfUnificadoManosCal_Vul.columns:
                columnas_contratos_optimos_existentes = [col for col in columnas_contratos_optimos if col in dfUnificadoManosCal_Vul.columns]
                
                if columnas_contratos_optimos_existentes:
                    # Obtener todas las columnas
                    todas_las_columnas = list(dfUnificadoManosCal_Vul.columns)
                    
                    # Encontrar la posición de Declarante_y
                    posicion_declarante_y = todas_las_columnas.index('Declarante_y')
                    
                    # Remover las columnas de contratos óptimos de su posición actual
                    columnas_sin_contratos_optimos = [col for col in todas_las_columnas if col not in columnas_contratos_optimos_existentes]
                    
                    # Reorganizar: antes de Declarante_y + Declarante_y + contratos óptimos + después de Declarante_y
                    columnas_antes = columnas_sin_contratos_optimos[:posicion_declarante_y + 1]
                    columnas_despues = columnas_sin_contratos_optimos[posicion_declarante_y + 1:]
                    
                    # Crear el nuevo orden de columnas
                    nuevas_columnas = columnas_antes + columnas_contratos_optimos_existentes + columnas_despues
                    
                    # Reorganizar el DataFrame
                    dfUnificadoManosCal_Vul = dfUnificadoManosCal_Vul[nuevas_columnas]
        else:
            # Para apuestas 1 y 2, solo calcular contratos individuales (no recalcular contratos óptimos)
            dfUnificadoManosCal_Vul = Calcular_ContratosPuntajes_Vectorizado_SoloContratos(
                dfUnificadoManosCal_Vul, 
                dfScores, 
                palos, 
                es_vulnerable_por_fila, 
                apuesta_actual
            )

        # Verificar que las columnas necesarias existan antes de hacer el groupby
        columnas_requeridas = ['Jugador', 'Tablero', f'Contrato_Optimo_Mano_{apuesta_actual}', f'PuntajeContrato_Optimo_Mano_{apuesta_actual}']
        if not all(col in dfUnificadoManosCal_Vul.columns for col in columnas_requeridas):
            raise ValueError(f"Faltan columnas requeridas en el DataFrame. Columnas necesarias: {columnas_requeridas}")

        # Calcular promedios de manera vectorizada
        promedios_por_jugador_tablero = dfUnificadoManosCal_Vul.groupby(['Jugador', 'Tablero']).agg({
            f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
            f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
        }).reset_index()

        # Calcular promedios de partners y oponentes de manera vectorizada
        for jugador_actual in dfUnificadoManosCal_Vul['Jugador'].unique():
            partner = partners[jugador_actual]
            oponentes = [j for j in dfUnificadoManosCal_Vul['Jugador'].unique() 
                        if j != jugador_actual and j != partner]
            
            # Calcular promedios de partners
            if partner in promedios_por_jugador_tablero['Jugador'].unique():
                df_partners = promedios_por_jugador_tablero[
                    promedios_por_jugador_tablero['Jugador'].isin([jugador_actual, partner])
                ].groupby('Tablero').agg({
                    f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
                    f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
                }).reset_index()
                
            # Calcular promedios de oponentes
            df_oponentes = promedios_por_jugador_tablero[
                promedios_por_jugador_tablero['Jugador'].isin(oponentes)
            ].groupby('Tablero').agg({
                f'Contrato_Optimo_Mano_{apuesta_actual}': 'mean',
                f'PuntajeContrato_Optimo_Mano_{apuesta_actual}': 'mean'
            }).reset_index()
            
        # Calcular valores esperados de manera vectorizada
        contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta_actual)
                            for nivel in range(1, 8)
                            for palo in palos.values()]
        
        valor_esperado_contratos = {}
        for jugador_actual in dfUnificadoManosCal_Vul['Jugador'].unique():
            df_jugador = dfUnificadoManosCal_Vul[dfUnificadoManosCal_Vul['Jugador'] == jugador_actual]
            promedios_contratos = {}
            
            # Calcular promedios de manera vectorizada
            for contrato in contratos_candidatos:
                if contrato in df_jugador.columns:
                    #genera en el valor esperado final, toma el valor maximo por columna contrato
                   # promedio = df_jugador[contrato].mean()
                    promedio = df_jugador[contrato].max()
                    promedios_contratos[contrato] = df_jugador[contrato].mean()
            
            valor_esperado_contratos[jugador_actual] = promedios_contratos

        # Crear y retornar el DataFrame de valores esperados
        df_valor_esperado = pd.DataFrame()
        df_valor_esperado = CalcularValorEsperadoFinal(
            df_valor_esperado,
            dfUnificadoManosCal_Vul,
            valor_esperado_contratos,
            apuesta_actual,
            declarante
        )
        
        # Guardar DataFrames por apuesta
        dataframes_por_apuesta[f'dfUnificadoManosCal_Vul_{apuesta_actual}'] = dfUnificadoManosCal_Vul.copy()
        dataframes_por_apuesta[f'df_valor_esperado_{apuesta_actual}'] = df_valor_esperado.copy()
        
        # Generar CSV inmediatamente para dfUnificadoManosCal_Vul
        df_temp = dfUnificadoManosCal_Vul.copy()
        df_temp.fillna(0, inplace=True)
        df_temp.to_csv(f"df_ManosCalculadas_ContratoOptimo_{apuesta_actual}.csv", float_format="%.0f", index=False)
    
    # Unificar los DataFrames de valor esperado en memoria (más eficiente)
    df_valor_esperado_unificado = UnificarDataFramesValorEsperado(dataframes_por_apuesta)
    
    return df_valor_esperado_unificado


def UnificarDataFramesValorEsperado(dataframes_por_apuesta):
    """
    Unifica los DataFrames de valor esperado de las 3 apuestas (0, 1, 2) en memoria.
    """
    try:
        # Obtener los DataFrames de valor esperado
        df_0 = dataframes_por_apuesta.get('df_valor_esperado_0')
        df_1 = dataframes_por_apuesta.get('df_valor_esperado_1')
        df_2 = dataframes_por_apuesta.get('df_valor_esperado_2')
        
        if df_0 is None or df_1 is None or df_2 is None:
            #print("Error: No se encontraron todos los DataFrames de valor esperado")
            return None
        
        # Optimización: Usar merge en lugar de set_index/concat/reset_index
        # Esto evita 3 operaciones costosas y reduce el uso de memoria
        df_unificado = df_0.merge(df_1, on='Jugador', suffixes=('', '_1'))
        df_unificado = df_unificado.merge(df_2, on='Jugador', suffixes=('', '_2'))

        # Guardar archivo unificado
        df_unificado.to_csv("df_valor_esperado.csv", index=False)
        #print("Archivo df_valor_esperado.csv generado exitosamente")

        return df_unificado

    except Exception as e:
        print(f"Error al unificar DataFrames: {e}")
        return None

def UnificarArchivosValorEsperado():
    """
    Unifica los archivos df_valor_esperado_0.csv, df_valor_esperado_1.csv y df_valor_esperado_2.csv
    usando la columna Jugador como llave de unión.
    """
    try:
        # Cargar los tres archivos CSV
        # Cargar archivos
        df_0 = pd.read_csv("df_valor_esperado_0.csv").set_index("Jugador")
        df_1 = pd.read_csv("df_valor_esperado_1.csv").set_index("Jugador")
        df_2 = pd.read_csv("df_valor_esperado_2.csv").set_index("Jugador")

        # Concatenar por columnas
        df_unificado = pd.concat([df_0, df_1, df_2], axis=1)

        # Resetear índice
        df_unificado = df_unificado.reset_index()

        # Guardar archivo unificado
        df_unificado.to_csv("df_valor_esperado.csv", index=False)
        print("Archivo df_valor_esperado.csv generado exitosamente")

        return df_unificado

    except FileNotFoundError as e:
        print(f"Error: No se encontró uno de los archivos CSV: {e}")
        return None
    except Exception as e:
        print(f"Error al unificar archivos: {e}")
        return None
        

def CalcularValorEsperadoFinal(df_valor_esperado, dfUnificadoManosCal_Vul, valor_esperado_contratos, apuesta,dealer):
    # Cache de palos
    palos = {'Cs': 1, 'Ds': 3, 'Hs': 5, 'Ss': 7, 'NT': 9}

    # Calcular contratos candidatos
    contratos_candidatos = [str(nivel * 100 + palo * 10 + apuesta)
                            for nivel in range(1, 8)
                            for palo in palos.values()]

    # Agregar valores esperados por contrato al DataFrame
    for jugador in valor_esperado_contratos:
        fila = {'Jugador': jugador}
        for contrato, valor in valor_esperado_contratos[jugador].items():
            fila[f'{contrato}'] = valor
        df_valor_esperado = pd.concat([df_valor_esperado, pd.DataFrame([fila])], ignore_index=True)

    # Calcular el promedio de puntaje por jugador
    promedios = dfUnificadoManosCal_Vul.groupby('Jugador')[f'PuntajeContrato_Optimo_Mano_{apuesta}'].mean()
    promedioPuntaje_por_jugador = promedios

    # --------------------------
    # Buscar el mejor contrato por jugador según el promedio ya calculado
    # --------------------------
    mejorContrato = {}
    mejorContrato_por_jugador = {}

    # Filtramos las columnas de contratos válidas
    contratos_filtrados = [c for c in contratos_candidatos if c.endswith(str(apuesta))]

    for jugador in df_valor_esperado['Jugador'].unique():
        # Verificar si el jugador tiene datos válidos en df_valor_esperado
        fila_jugador = df_valor_esperado[df_valor_esperado['Jugador'] == jugador]

        if not fila_jugador.empty:
            # Solo tomar columnas de contratos que existan en el dataframe
            columnas_validas = [c for c in contratos_filtrados if c in fila_jugador.columns]

            if columnas_validas:
                # Buscar la columna (contrato) que tenga el valor promedio más alto
                serie_valores = fila_jugador[columnas_validas].iloc[0]
                mejor_contrato = serie_valores.idxmax()
                mejor_valor = serie_valores.max()

                mejorContrato[jugador] = mejor_contrato
                mejorContrato_por_jugador[jugador] = mejor_valor

    # --------------------------
    # Asignar resultados al df_valor_esperado
    # --------------------------
    for jugador in df_valor_esperado['Jugador'].unique():
        if jugador in mejorContrato:
            contrato = mejorContrato[jugador]
            puntaje = float(promedioPuntaje_por_jugador.get(jugador, 0))

            if pd.notna(contrato):
                # Extraer solo el número del contrato (columna -> código)
                df_valor_esperado.loc[df_valor_esperado['Jugador'] == jugador,
                                      f'Contrato_Optimo_Mano_{apuesta}'] = int(contrato)

            if pd.notna(puntaje):
                df_valor_esperado.loc[df_valor_esperado['Jugador'] == jugador,
                                      f'PromedioPuntajeContrato_Optimo_Mano_{apuesta}'] = int(round(puntaje))

    # --------------------------
    # Limpieza de tipos y promedios de pareja y oponentes
    # --------------------------
    columnas_enteras = [
        f'Contrato_Optimo_Mano_{apuesta}',
        f'PromedioPuntajeContrato_Optimo_Mano_{apuesta}',
       # f'PromedioContrato_Optimo_Mano_Partner_{apuesta}',
       # f'PromedioPuntaje_Optimo_Mano_Partner_{apuesta}',
       # f'PromedioContrato_Optimo_Mano_Oponentes_{apuesta}',
       # f'PromedioPuntaje_Optimo_Mano_Oponentes_{apuesta}',
    ]

    for columna in columnas_enteras:
        if columna in df_valor_esperado.columns:
            df_valor_esperado[columna] = df_valor_esperado[columna].fillna(0).astype(int)

    df_valor_esperado['Declarante'] = dealer

    return df_valor_esperado


def DefinirSiSubastarAnt(jugador, dfTrayectoria, dfValorEsperado):

    repuestaSubastar = ""
    oponente_derecha_dict = {
    'N': 'E',
    'E': 'S',
    'S': 'W',
    'W': 'N'
}
    # Oponente de la derecha (último registro)
    jugador_derecha = oponente_derecha_dict[jugador]
    df_oponente_derecha = dfTrayectoria[dfTrayectoria['Jugador'] == jugador_derecha]
    oponente_derecha = df_oponente_derecha.iloc[-1] if not df_oponente_derecha.empty else None
        # Oponente de la izquierda (es el oponente del oponente de la derecha)
    jugador_izquierda = partners[jugador_derecha]
    df_oponente_izquierda = dfTrayectoria[dfTrayectoria['Jugador'] == jugador_izquierda]
    oponente_izquierda = df_oponente_izquierda.iloc[-1] if not df_oponente_izquierda.empty else None
    
    # Verificar si hay registros en la trayectoria
    # Verificar si la trayectoria está vacía
    if dfTrayectoria.empty:
        # Nadie ha subastado aún
        respuestaSubastar = ConsultarSiSubastaJugador(jugador, dfValorEsperado)
        return respuestaSubastar
    # Consultar el último declarante
    ultimoDeclarante = dfTrayectoria[dfTrayectoria['Grilla'] != 0]

    # Determinar partner y oponentes
    partner = partners[jugador]
    derecha = oponente_derecha_dict[jugador]
    izquierda = partners[derecha]  # oponente del oponente de la derecha

    if ultimoDeclarante.empty:
        respuestaSubastar = ConsultarSiSubastaJugador(jugador, dfValorEsperado)
    else:
        if ultimoDeclarante == partner:
            # El último en declarar fue el compañero
            respuestaSubastar = ConsultarDeclarantePartner(jugador, dfValorEsperado, dfTrayectoria)
        elif ultimoDeclarante in [izquierda, derecha]:
            # El último en declarar fue un oponente izquierda o derecha
            respuestaSubastar = ConsultarDeclaranteOponente(jugador, dfValorEsperado, dfTrayectoria)
        else:
            # Caso raro: jugador no identificado o error de datos,, Valor esperado puntaje promedio del agente actual subastar es > 0 "si subastar" si es  <= 0 "no subastar"
            respuestaSubastar = ConsultarSiSubastaJugador(jugador, dfValorEsperado)
            
    # Si no hay registros en la trayectoria, no es el partner o Subasta es 0
    return repuestaSubastar

def DefinirSiSubastar(jugador, dfTrayectoria, dfValorEsperado,apuesta):
    respuestaSubastar = ""

    # Validar que el jugador sea válido
    if jugador not in partners:
        raise ValueError(f"Jugador inválido: {jugador}")

    # Si la trayectoria está vacía, es la primera subasta
    if dfTrayectoria is None or dfTrayectoria.empty:
        return ConsultarSiSubastaJugador(jugador, dfValorEsperado)

    # Determinar partner y oponentes
    partner = partners[jugador]
    derecha = oponente_derecha[jugador]
    izquierda = partners[derecha]  # el oponente del oponente de la derecha

    df_subastas = dfTrayectoria[dfTrayectoria['Grilla'] != 0]

    if df_subastas.empty:
        # Nadie ha declarado aún
        return ConsultarSiSubastaJugador(jugador, dfValorEsperado)

    # Extraer el último declarante (cadena, no DataFrame) cuya voz no pass
    ultima_fila = df_subastas.iloc[-1]
    ultimoDeclarante = ultima_fila['Jugador']

    # Lógica principal
    if ultimoDeclarante == partner:
        # El último en declarar fue el compañero
        respuestaSubastar = ConsultarDeclarantePartner(jugador, dfValorEsperado, dfTrayectoria,apuesta)
    elif ultimoDeclarante in [izquierda, derecha]:
        # El último en declarar fue un oponente (izquierda o derecha)
        respuestaSubastar = ConsultarDeclaranteOponente(jugador, dfValorEsperado, dfTrayectoria)
    else:
        # Caso atípico: jugador desconocido o datos inconsistentes
        respuestaSubastar = ConsultarSiSubastaJugador(jugador, dfValorEsperado)

    return respuestaSubastar


#Valor esperado contrato máximo del agente actual subastar es > 0 "si subastar" si es  <= 0 "no subastar"
def ConsultarSiSubastaJugador(jugador, dfValorEsperado):
    fila = dfValorEsperado.loc[dfValorEsperado['Jugador'] == jugador]

    if fila.empty:
        raise ValueError(f"No existe el jugador {jugador} en dfValorEsperado")

    promedioEsperado = fila['PromedioPuntajeContrato_Optimo_Mano_0'].iloc[0]

    # El valor del contrato óptimo (que es el nombre de la columna a consultar)
    contratoOptimo = fila['Contrato_Optimo_Mano_0'].iloc[0]

    # --- VALIDACIÓN CLAVE ---
    if not isinstance(contratoOptimo, str):
        contratoOptimo = str(contratoOptimo)

    contratoOptimo = contratoOptimo.strip()  # limpiar espacios

    if contratoOptimo not in dfValorEsperado.columns:
        raise KeyError(f"El valor '{contratoOptimo}' no existe como columna en dfValorEsperado")

    # Acceder a la columna dinámica
    valorContratoOptimo = fila[contratoOptimo].iloc[0]
    #Se consulta el valor del contrato optimo en lugar del promedio esperado
    if valorContratoOptimo > 0:
        return "SI"
    else:
        return "NO"


#consultar el declarante
def ObtenerMaximoVE(contrato_recibido, dfValorEsperado, jugador, partner, oponente_derecha, oponente_izquierda):
    """
    Obtiene el jugador, contrato máximo y valor del contrato con mayor valor esperado
    entre los contratos mayores al contrato recibido, considerando declarante, partner y oponentes.
    
    Args:
        contrato_recibido: Contrato base para buscar contratos mayores
        dfValorEsperado: DataFrame con los valores esperados por contrato y jugador
        jugador: Jugador declarante actual
        partner: Partner del jugador declarante
        oponente_derecha: Oponente de la derecha
        oponente_izquierda: Oponente de la izquierda
    
    Returns:
        tuple: (jugador_maximo, contrato_maximo, valor_maximo)
    """
    contrato_maximo = 0
    valor_maximo = 0
    jugador_maximo = None
    
    # Lista de jugadores a considerar: declarante, partner y oponentes
    jugadores_considerar = [jugador, partner, oponente_derecha, oponente_izquierda]
    
    # Obtener todos los contratos disponibles en el DataFrame
    contratos_disponibles = []
    for columna in dfValorEsperado.columns:
        if columna.isdigit() and len(columna) == 3:
            contrato = int(columna)
            if contrato > contrato_recibido:
                contratos_disponibles.append(contrato)
    
    # Buscar el contrato con mayor valor esperado entre los jugadores considerados
    for contrato in contratos_disponibles:
        # Buscar el valor esperado para este contrato
        if str(contrato) in dfValorEsperado.columns:
            valores_contrato = dfValorEsperado[str(contrato)]
            
            # Encontrar el jugador con mayor valor esperado para este contrato
            # Solo considerar los jugadores especificados
            for idx, valor in valores_contrato.items():
                jugador_actual = dfValorEsperado.iloc[idx]['Jugador']
                
                # Solo considerar si el jugador está en la lista de jugadores a considerar
                if jugador_actual in jugadores_considerar and pd.notna(valor) and valor > valor_maximo:
                    valor_maximo = valor
                    contrato_maximo = contrato
                    jugador_maximo = jugador_actual
    
    return jugador_maximo, contrato_maximo, valor_maximo



def ConsultarDeclarantePartner(jugador, dfValorEsperado, dfTrayectoria,apuesta):
    # Obtener el partner del jugador
    partner = partners[jugador]
    #    HECHAS POR EL PARTNER
    df_partner_con_voz = dfTrayectoria[
        (dfTrayectoria['Grilla'] != 0) & 
        (dfTrayectoria['Jugador'] == partner) # Filtramos solo por la posición del partner
    ]
    #Obtener el último registro del DataFrame filtrado y su valor
    if not df_partner_con_voz.empty:
        # Obtener el último registro (es una Serie de pandas)
        registro_partner = df_partner_con_voz.iloc[-1]
        
        # Obtener el valor específico de la columna 'Grilla'
        contrato_partner = int(registro_partner['Grilla'])
    else:
        # Manejar el caso donde el partner nunca hizo una subasta real (solo pasó)
        contrato_partner = 0 
        # Extraer la apuesta del contrato del partner (último dígito)
    try:
        apuestaPartner = int(str(contrato_partner)[-1])
    except ValueError:
        apuestaPartner = 0
   # valorEsperadoPartner = dfValorEsperado.loc[dfValorEsperado['Jugador'] == jugador, 'PromedioPuntajeContrato_Optimo_Mano_Partner_{apuesta_actual}'].iloc[0]
    valorEsperadoPartner = dfValorEsperado.loc[dfValorEsperado['Jugador'] == partner, f'PromedioPuntajeContrato_Optimo_Mano_{apuestaPartner}'].iloc[0]
    valorEsperadoJugador = dfValorEsperado.loc[dfValorEsperado['Jugador'] == jugador, f'PromedioPuntajeContrato_Optimo_Mano_{apuesta}'].iloc[0]
    oponente_derecha_jugador = oponente_derecha[jugador]
    oponente_izquierda_jugador = oponente_izquierda[jugador]
    # -----------------------------------------------------------
    ## 1. Oponente de la Derecha
    # -----------------------------------------------------------
    
    # Filtrar solo las subastas reales (Grilla != 0) del Oponente de la Derecha
    df_oponente_derecha_con_voz = dfTrayectoria[
        (dfTrayectoria['Grilla'] != 0) & 
        (dfTrayectoria['Jugador'] == oponente_derecha_jugador)
    ]
    
    # Obtener el último registro
    if not df_oponente_derecha_con_voz.empty:
        registro_oponente_derecha = df_oponente_derecha_con_voz.iloc[-1]
    else:
        # Crea una Serie vacía si no hay subastas reales (para evitar errores)
        registro_oponente_derecha = None # O puedes inicializar con valores predeterminados
        
    # -----------------------------------------------------------
    ## 2. Oponente de la Izquierda
    # -----------------------------------------------------------
    
    # Filtrar solo las subastas reales (Grilla != 0) del Oponente de la Izquierda
    df_oponente_izquierda_con_voz = dfTrayectoria[
        (dfTrayectoria['Grilla'] != 0) & 
        (dfTrayectoria['Jugador'] == oponente_izquierda_jugador)
    ]
    
    # Obtener el último registro
    if not df_oponente_derecha_con_voz.empty:
        registro_oponente_derecha = df_oponente_derecha_con_voz.iloc[-1]
        contratoOponente_derecha = registro_oponente_derecha['Grilla']
        apuestaOponente_derecha = int(str(contratoOponente_derecha)[-1])
    else:
        registro_oponente_derecha = None
        contratoOponente_derecha = 0
        apuestaOponente_derecha = 0
    
        # Obtener el último registro
    if not df_oponente_izquierda_con_voz.empty:
        registro_oponente_izquierda = df_oponente_izquierda_con_voz.iloc[-1]
        contratoOponente_izquierda = registro_oponente_izquierda['Grilla']
        apuestaOponente_izquierda = int(str(contratoOponente_izquierda)[-1])
    else:
        registro_oponente_izquierda = None
        contratoOponente_izquierda = 0
        apuestaOponente_izquierda = 0           
    # Obtener el contrato del partner como entero
    contrato_partner_int = int(contrato_partner)
    
    # Obtener información del máximo valor esperado para el jugador actual
    jugador_maximo_actual, contrato_maximo_actual, valor_maximo_actual = ObtenerMaximoVE(
        contrato_partner_int, dfValorEsperado, jugador, partner, oponente_derecha, oponente_izquierda
    )
    
    # Obtener información del máximo valor esperado para el partner
    jugador_maximo_partner, contrato_maximo_partner, valor_maximo_partner = ObtenerMaximoVE(
        contrato_partner_int, dfValorEsperado, partner, jugador, oponente_derecha, oponente_izquierda
    )
    
    # Obtener información del máximo valor esperado para el oponente derecha
    jugador_maximo_oponente_derecha, contrato_maximo_oponente_derecha, valor_maximo_oponente_derecha = ObtenerMaximoVE(
        contrato_partner_int, dfValorEsperado, oponente_derecha, oponente_izquierda, jugador, partner
    )
    
    # Obtener información del máximo valor esperado para el oponente izquierda
    jugador_maximo_oponente_izquierda, contrato_maximo_oponente_izquierda, valor_maximo_oponente_izquierda = ObtenerMaximoVE(
        contrato_partner_int, dfValorEsperado, oponente_izquierda, oponente_derecha, jugador, partner
    )

    veContratoMaximoPartherDoblado = ObtenerMaximoVEContratosDespues(partner, contrato_partner, 1)

    #La voz del partner es forcing
    #si es forcing la voz del partner   
    if registro_partner['Force'] == "Si":  
        #Consultar si el oponente pasó
        if contratoOponente_derecha== '0':
            return "SI"
        #si el opononente a la derecha o izquierda dobló
        elif apuestaOponente_derecha == 1 or apuestaOponente_izquierda == 1:
            return "OPCIONAL"
    else:
        #2.2 La voz del partner no es forcing
        #Consultar si el oponente de la derecha pasó
        if contratoOponente_derecha == '0':
            contratoPartner = registro_partner['Grilla']
    # caso 1. El VE del mejor contrato de la pareja es mayor  o igual que el VE del contrato actual promediopuntajeContratoActual = dfValorEsperado.loc[dfValorEsperado['Jugador'] == jugador, contratoPartner].iloc[0]
            if valorEsperadoPartner >= valorEsperadoJugador:
                return "SI"
    # caso 3. El VE del mejor contrato de la pareja es menor o igual que el VE del contrato actual y no hay un contrato superior con mejor VE que el de los oponentes          
            elif (valorEsperadoPartner <= valorEsperadoJugador) and (valorEsperadoPartner <= valor_maximo_oponente_derecha) and (valorEsperadoPartner <= valor_maximo_oponente_izquierda):
                return "NO"
    #caso 2. Existe un contrato más alto, cuyo valor esperado es mejor que el VE de los oponentes "SI" 
            elif (valorEsperadoPartner > valor_maximo_oponente_derecha) and (valorEsperadoPartner > valor_maximo_oponente_izquierda):
                return "SI"
    #caso 4. El oponente de la derecha  o izquierda dobló
            elif apuestaOponente_derecha == 1 or apuestaOponente_izquierda == 1:           
                return "OPCIONAL"
    #caso 2.3 El partner dobla
        elif apuestaPartner == 1:
            #El VE esperado de dejar el doblo es inferior al VE del mejor contrato de la pareja
            if veContratoMaximoPartherDoblado < valorEsperadoJugador:
                return "SI"
            else:
                #El VE esperado de dejar el doblo es el mejor resultado
                return "NO"
        
                        
def ObtenerMaximoVEContratosDespues(jugador, contrato, apuesta):
    """
    Obtiene el valor esperado máximo de los contratos superiores al contrato recibido
    que tengan la misma apuesta especificada, usando el archivo df_valor_esperado.csv.
    
    Args:
        jugador: Jugador actual
        contrato: Contrato de referencia (formato de 3 dígitos)
        apuesta: Apuesta a filtrar (0=sin doblar, 1=doblado, 2=redoblado)
    
    Returns:
        float: Valor esperado máximo de los contratos superiores con la misma apuesta
    """
    # Leer el archivo df_valor_esperado.csv
    dfValorEsperado = pd.read_csv('df_valor_esperado.csv')
    
    # Filtrar por el jugador actual en df_valor_esperado
    df_jugador = dfValorEsperado[dfValorEsperado['Jugador'] == jugador]
    
    if df_jugador.empty:
        return 0
    
    # Convertir el contrato a entero para comparaciones
    contrato_int = int(contrato)
    
    # Obtener todas las columnas de contratos que tengan la misma apuesta y sean superiores
    columnas_contratos = []
    for columna in dfValorEsperado.columns:
        if columna.isdigit() and len(columna) == 3:
            contrato_actual = int(columna)
            # Verificar si tiene la misma apuesta y es superior al contrato recibido
            if int(columna[-1]) == apuesta and contrato_actual > contrato_int:
                columnas_contratos.append(contrato_actual)
    
    # Si no hay contratos superiores, retornar 0
    if not columnas_contratos:
        return 0
    
    # Obtener el valor esperado máximo de los contratos superiores
    valores_contratos = []
    for contrato_superior in columnas_contratos:
        columna_contrato = str(contrato_superior)
        if columna_contrato in df_jugador.columns:
            valor = df_jugador[columna_contrato].iloc[0]
            if pd.notna(valor):
                valores_contratos.append(valor)
    
    # Retornar el valor máximo encontrado
    if valores_contratos:
        return max(valores_contratos)
    else:
        return 0




def ConsultarDeclaranteOponente(jugador, dfValorEsperado, dfTrayectoria):
    """
    Consulta las condiciones cuando el último declarante es un oponente.
    
    Condiciones:
    - El contrato subastado es mayor o igual a 470:
        * El VE de doblar es >= 100 y mayor o igual que el VE del mejor contrato de la pareja: Si
        * El VE de doblar es <= 100 y el VE del mejor contrato de la pareja es menor o igual que el VE del contrato de los oponentes: No
        * El VE del mejor contrato de la pareja es mayor que el VE del contrato de los oponentes y que el de doblar: Si
    
    - El contrato subastado es menor a 470:
        * El VE del mejor contrato de la pareja es menor que el VE del contrato actual de los oponentes: No
        * El VE del mejor contrato de la pareja es mayor o igual que el VE del contrato actual de los oponentes: Si
    
    Args:
        jugador: Jugador actual
        dfValorEsperado: DataFrame con los valores esperados
    
    Returns:
        str: "SI", "NO" o "OPCIONAL"
    """
    # Obtener el partner del jugador
    partner = partners[jugador]

        # Usar los diccionarios globales correctos
    oponente_derecha_jugador = oponente_derecha[jugador]
    oponente_izquierda_jugador = oponente_izquierda[jugador]
    posiciones_oponentes = [oponente_derecha_jugador, oponente_izquierda_jugador]
      
    # Obtener el último registro de la trayectoria (el oponente declarante)
    #Filtrar la trayectoria para obtener SOLO las subastas reales (Grilla != 0) 
    #    HECHAS POR LOS OPONENTES
    df_oponentes_con_voz = dfTrayectoria[
        (dfTrayectoria['Grilla'] != 0) & 
        (dfTrayectoria['Jugador'].isin(posiciones_oponentes))
    ]
    registro_oponente_final = df_oponentes_con_voz.iloc[-1]   
    # Obtener el valor específico de la columna 'Grilla'
    # 3. Obtener el último registro y su valor
    if not df_oponentes_con_voz.empty:
        # Obtener el último registro (es una Serie de pandas)
        registro_oponente_final = df_oponentes_con_voz.iloc[-1]      
        # Obtener el valor específico de la columna 'Grilla'
        contrato_oponente = int(registro_oponente_final['Grilla'])
    else:
        # Manejar el caso donde los oponentes solo pasaron (el DataFrame está vacío)
        contrato_oponente = 0   
    
    # Extraer la apuesta del contrato del oponente (último dígito) 
    try:
        apuesta_oponente = int(str(contrato_oponente)[-1])
    except ValueError:
        apuesta_oponente = 0

    veContratoMaximojugadorDoblado = ObtenerMaximoVEContratosDespues(partner, contrato_oponente, 1)
    veContratoMaximoPartner = ObtenerMaximoVEContratosDespues(partner, contrato_oponente, apuesta_oponente)
    veContratoMaximoPartherDoblado = ObtenerMaximoVEContratosDespues(partner, contrato_oponente, 1)
    veContratoMaximoOponenteDerecha = ObtenerMaximoVEContratosDespues(oponente_derecha_jugador, contrato_oponente, apuesta_oponente)
    veContratoMaximoOponenteIzquierda = ObtenerMaximoVEContratosDespues(oponente_izquierda_jugador, contrato_oponente, apuesta_oponente)
    veContratoMaximoOponenteDerechaDoblado = ObtenerMaximoVEContratosDespues(oponente_derecha_jugador, contrato_oponente, 1)
    veContratoMaximoOponenteIzquierdaDoblado = ObtenerMaximoVEContratosDespues(oponente_izquierda_jugador, contrato_oponente, 1)

        #obtener el valor esperado del contrato maximo entreo los oponentes
    veContratoMaximoOponentes = max(veContratoMaximoOponenteDerecha, veContratoMaximoOponenteIzquierda)
        #obtener el valor esperado maximo del contrato doblado entre los oponentes
    veContratoMaximoOponentesDoblado = max(veContratoMaximoOponenteDerechaDoblado, veContratoMaximoOponenteIzquierdaDoblado)

    # Verificar si el contrato subastado es mayor o igual a 470
    if contrato_oponente >= 470:
        # El contrato subastado es mayor o igual a 470     

        #3.1.1 El VE de doblar es >= 100 y mayor o igual que el VE del mejor contrato de la pareja
        if veContratoMaximojugadorDoblado >= 100 and (veContratoMaximojugadorDoblado >= veContratoMaximoPartherDoblado):
            return "SI"
        #3.1.2 El VE de doblar es <= 100 y el VE del mejor contrato de la pareja es menor o igual que el VE del contrato de los oponentes
        elif veContratoMaximojugadorDoblado <= 100 and (veContratoMaximoPartner <= veContratoMaximoOponentes):
            return "NO"
        #3.1.3 El VE del partner es > que el VE de los oponentes y que el de doblar
        if (veContratoMaximoPartner > veContratoMaximoOponentes) and (veContratoMaximoPartherDoblado > veContratoMaximoOponentesDoblado):
            return "SI"
        else:
            return "NO"
    else:
        # El contrato subastado es menor a 470
        # El VE del mejor contrato de la pareja es menor que el VE del contrato actual de los oponentes
        if veContratoMaximoPartner < veContratoMaximoOponentes:
            return "NO"
        # El VE del mejor contrato de la pareja es mayor o igual que el VE del contrato actual de los oponentes
        else:
            return "SI"
    
    # Por defecto, no subastar si no se cumple ninguna condición específica
    return "NO"


def AnalizarSubastaOponente(jugador, dfValorEsperado, apuesta):
    return "OPONENTE", apuesta

def CargarTrayectoriaSubasta():
    """
    Carga el archivo de trayectoria de subasta desde CSV
    
    Returns:
        pandas.DataFrame: DataFrame con la información de trayectoria de subasta
        None: Si ocurre un error al cargar el archivo
    
    Archivo esperado:
        - trayectoria_subasta.csv: Contiene restricciones por tablero y jugador
        - Separador: punto y coma (;)
        - Columnas: Tablero, Jugador, Min_HCP, Max_HCP, Min_S, Max_S, etc.
    """
    try:
        # Cargar archivo CSV con separador punto y coma
        df_trayectoria = pd.read_csv('trayectoria_subasta.csv', sep=';')
        print("Archivo trayectoria_subasta.csv cargado correctamente")
        return df_trayectoria
    except Exception as e:
        # Manejar errores de lectura del archivo
        print(f"Error al cargar trayectoria_subasta.csv: {e}")
        return None

def VerificarRestriccionesMano(mano, restricciones):
    """
    Verifica si una mano cumple con las restricciones mínimas y máximas definidas
    
    Args:
        mano (pandas.Series): Serie con la información de una mano (S, H, D, C)
        restricciones (pandas.Series): Serie con las restricciones (Min_HCP, Max_HCP, Min_S, Max_S, etc.)
    
    Returns:
        tuple: (cumple_min, cumple_max) donde cada valor es True/False
        
    Restricciones verificadas:
        - HCP (High Card Points): Puntos de honor totales de la mano
        - S (Spades): Número de cartas de picas
        - H (Hearts): Número de cartas de corazones  
        - D (Diamonds): Número de cartas de diamantes
        - C (Clubs): Número de cartas de tréboles
    """
    # Debug: mostrar información de la mano
    print(f"      Verificando mano: Ss='{mano['Ss'] if pd.notna(mano['Ss']) else 'NaN'}', Hs='{mano['Hs'] if pd.notna(mano['Hs']) else 'NaN'}', Ds='{mano['Ds'] if pd.notna(mano['Ds']) else 'NaN'}', Cs='{mano['Cs'] if pd.notna(mano['Cs']) else 'NaN'}'")
    
    # Calcular HCP de la mano actual usando la función existente
    hcp_actual = Calcular_HCP(
        mano['Ss'] if pd.notna(mano['Ss']) else '',  # Picas
        mano['Hs'] if pd.notna(mano['Hs']) else '',  # Corazones
        mano['Ds'] if pd.notna(mano['Ds']) else '',  # Diamantes
        mano['Cs'] if pd.notna(mano['Cs']) else ''   # Tréboles
    )
    
    print(f"      HCP calculado: {hcp_actual}")
    print(f"      Restricciones: Min_HCP={restricciones['Min_HCP']}, Max_HCP={restricciones['Max_HCP']}")
    
    # Verificar restricciones de HCP (puntos de honor)
    cumple_min_hcp = hcp_actual >= restricciones['Min_HCP']  # Debe tener al menos Min_HCP puntos
    cumple_max_hcp = hcp_actual <= restricciones['Max_HCP']  # Debe tener máximo Max_HCP puntos
    
    # Verificar restricciones por palo - cantidad mínima de cartas
    cumple_min_s = len(mano['Ss']) >= restricciones['Min_S'] if pd.notna(mano['Ss']) else False
    cumple_min_h = len(mano['Hs']) >= restricciones['Min_H'] if pd.notna(mano['Hs']) else False
    cumple_min_d = len(mano['Ds']) >= restricciones['Min_D'] if pd.notna(mano['Ds']) else False
    cumple_min_c = len(mano['Cs']) >= restricciones['Min_C'] if pd.notna(mano['Cs']) else False
    
    # Verificar restricciones por palo - cantidad máxima de cartas
    cumple_max_s = len(mano['Ss']) <= restricciones['Max_S'] if pd.notna(mano['Ss']) else False
    cumple_max_h = len(mano['Hs']) <= restricciones['Max_H'] if pd.notna(mano['Hs']) else False
    cumple_max_d = len(mano['Ds']) <= restricciones['Max_D'] if pd.notna(mano['Ds']) else False
    cumple_max_c = len(mano['Cs']) <= restricciones['Max_C'] if pd.notna(mano['Cs']) else False
    
    # Debug: mostrar verificaciones por palo
    print(f"      Verificaciones por palo:")
    print(f"        S: {len(mano['Ss']) if pd.notna(mano['Ss']) else 0} >= {restricciones['Min_S']} = {cumple_min_s}, {len(mano['Ss']) if pd.notna(mano['Ss']) else 0} <= {restricciones['Max_S']} = {cumple_max_s}")
    print(f"        H: {len(mano['Hs']) if pd.notna(mano['Hs']) else 0} >= {restricciones['Min_H']} = {cumple_min_h}, {len(mano['Hs']) if pd.notna(mano['Hs']) else 0} <= {restricciones['Max_H']} = {cumple_max_h}")
    print(f"        D: {len(mano['Ds']) if pd.notna(mano['Ds']) else 0} >= {restricciones['Min_D']} = {cumple_min_d}, {len(mano['Ds']) if pd.notna(mano['Ds']) else 0} <= {restricciones['Max_D']} = {cumple_max_d}")
    print(f"        C: {len(mano['Cs']) if pd.notna(mano['Cs']) else 0} >= {restricciones['Min_C']} = {cumple_min_c}, {len(mano['Cs']) if pd.notna(mano['Cs']) else 0} <= {restricciones['Max_C']} = {cumple_max_c}")
    
    # Determinar si cumple TODAS las restricciones mínimas (AND lógico)
    cumple_min = (cumple_min_hcp and cumple_min_s and cumple_min_h and 
                  cumple_min_d and cumple_min_c)
    
    # Determinar si cumple TODAS las restricciones máximas (AND lógico)
    cumple_max = (cumple_max_hcp and cumple_max_s and cumple_max_h and 
                  cumple_max_d and cumple_max_c)
    
    print(f"      Resultados finales: Cumple_Min={cumple_min}, Cumple_Max={cumple_max}")
    
    return cumple_min, cumple_max

def ProcesarJugador(jugador, df_trayectoria):
    """
    Procesa y verifica todas las manos de un jugador específico contra las restricciones
    
    Args:
        jugador (str): Identificador del jugador ('E', 'N', 'S', 'W')
        df_trayectoria (pandas.DataFrame): DataFrame con las restricciones de trayectoria
    
    Returns:
        tuple: (df_prueba, total_manos) donde:
            - df_prueba: DataFrame con las manos verificadas y resultados
            - total_manos: Número total de manos procesadas
            - (None, None): Si ocurre un error o no se encuentra el archivo
    
    Archivos generados:
        - df_pruebaManosCalcular_{jugador}.csv: Archivo con resultados de verificación
        
    Proceso:
        1. Carga archivo de manos calculadas del jugador
        2. Crea DataFrame de prueba con columnas adicionales
        3. Verifica cada mano contra las restricciones
        4. Guarda resultados en archivo CSV
    """
    # Definir nombres de archivos de entrada y salida
    archivo_manos = f'df_manosCalcular_{jugador}.csv'      # Archivo de entrada con manos
    archivo_prueba = f'df_pruebaManosCalcular_{jugador}.csv'  # Archivo de salida con resultados
    
    # Verificar que existe el archivo de manos del jugador
    if not os.path.exists(archivo_manos):
        print(f"Archivo {archivo_manos} no encontrado, saltando...")
        return None, None
    
    try:
        # Cargar manos calculadas del jugador desde CSV
        df_manos = pd.read_csv(archivo_manos)
        print(f"Verificando {len(df_manos)} manos para jugador {jugador}")
        
        # Crear DataFrame de prueba copiando las manos originales
        df_prueba = df_manos.copy()
        
        # Agregar columnas de conteo de cartas por palo y HCP_Total
        df_prueba['ConteoS'] = df_prueba['Ss'].apply(lambda x: len(str(x)) if pd.notna(x) and str(x) != '' else 0)
        df_prueba['ConteoH'] = df_prueba['Hs'].apply(lambda x: len(str(x)) if pd.notna(x) and str(x) != '' else 0)
        df_prueba['ConteoD'] = df_prueba['Ds'].apply(lambda x: len(str(x)) if pd.notna(x) and str(x) != '' else 0)
        df_prueba['ConteoC'] = df_prueba['Cs'].apply(lambda x: len(str(x)) if pd.notna(x) and str(x) != '' else 0)
        
        # Calcular HCP total para cada mano
        def calcular_hcp_total(row):
            valor_honor = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
            hcp_total = 0
            
            # Calcular HCP para cada palo
            for palo in ['Ss', 'Hs', 'Ds', 'Cs']:
                cartas = str(row[palo]) if pd.notna(row[palo]) and str(row[palo]) != '' else ''
                for carta in cartas:
                    hcp_total += valor_honor.get(carta.upper(), 0)
            
            return hcp_total
        
        df_prueba['HCP_Total'] = df_prueba.apply(calcular_hcp_total, axis=1)
        
        # Agregar columnas de restricciones y resultados
        columnas_restricciones = [
            'Min_HCP', 'Max_HCP', 
            'Min_S', 'Max_S', 'Min_H', 'Max_H', 'Min_D', 'Max_D', 'Min_C', 'Max_C',
            'Cumple_Min_HCP', 'Cumple_Max_HCP',
            'Cumple_Min_S', 'Cumple_Max_S', 'Cumple_Min_H', 'Cumple_Max_H',
            'Cumple_Min_D', 'Cumple_Max_D', 'Cumple_Min_C', 'Cumple_Max_C'
        ]
        
        # Inicializar columnas: valores numéricos para restricciones, 'No' para resultados
        for col in columnas_restricciones:
            if 'Min' in col or 'Max' in col:
                if 'Cumple' not in col:
                    df_prueba[col] = 0  # Restricciones numéricas
                else:
                    df_prueba[col] = 'No'  # Resultados de verificación
            else:
                df_prueba[col] = 'No'  # Resultados generales
        
        # Debug: mostrar columnas agregadas
        print(f"Columnas agregadas: {[col for col in df_prueba.columns if col not in df_manos.columns]}")
        
        # Verificar cada mano individualmente
        manos_con_restricciones = 0
        manos_sin_restricciones = 0
        
        for idx, mano in df_prueba.iterrows():
            tablilla = mano['Tablilla']      # Número de la tablilla (corresponde a Tablero en trayectoria_subasta.csv)
            jugador_mano = mano['Jugador']   # Jugador de la mano
            
            # Debug: mostrar información de la mano actual
            if idx > 1 and idx <= 3:  # Solo mostrar las manos 2 y 3 para debug
                print(f"  Mano {idx}: Tablilla={tablilla}, Jugador={jugador_mano}")
            
            # Buscar restricciones correspondientes en trayectoria_subasta.csv
            # Tomar el último registro del jugador correspondiente (no filtrar por tablero)
            restricciones = df_trayectoria[df_trayectoria['Jugador'] == jugador_mano]
            
            # Si hay registros, tomar el último (más reciente)
            if not restricciones.empty:
                restricciones = restricciones.iloc[[-1]]  # Último registro
            
            # Debug: mostrar restricciones encontradas
            if idx > 1 and idx <= 3:
                print(f"    Restricciones encontradas: {len(restricciones)}")
                if not restricciones.empty:
                    print(f"    Restricciones: Min_HCP={restricciones.iloc[0]['Min_HCP']}, Max_HCP={restricciones.iloc[0]['Max_HCP']}")
                    print(f"    Restricciones: Min_S={restricciones.iloc[0]['Min_S']}, Max_S={restricciones.iloc[0]['Max_S']}")
                    print(f"    Restricciones: Min_H={restricciones.iloc[0]['Min_H']}, Max_H={restricciones.iloc[0]['Max_H']}")
                    print(f"    Restricciones: Min_D={restricciones.iloc[0]['Min_D']}, Max_D={restricciones.iloc[0]['Max_D']}")
                    print(f"    Restricciones: Min_C={restricciones.iloc[0]['Min_C']}, Max_C={restricciones.iloc[0]['Max_C']}")
                else:
                    print(f"    No se encontraron restricciones para Jugador={jugador_mano}")
                    print(f"    Valores únicos en df_trayectoria['Jugador']: {df_trayectoria['Jugador'].unique()}")
            
            # Si se encontraron restricciones para este tablero/jugador
            if not restricciones.empty:
                manos_con_restricciones += 1
                rest = restricciones.iloc[0]  # Tomar la primera (y única) fila de restricciones
                
                # Asignar valores de restricciones al DataFrame de prueba
                columnas_restricciones_numericas = ['Min_HCP', 'Max_HCP', 'Min_S', 'Max_S', 
                                                  'Min_H', 'Max_H', 'Min_D', 'Max_D', 'Min_C', 'Max_C']
                for col in columnas_restricciones_numericas:
                    df_prueba.at[idx, col] = rest[col]
                
                # Verificar si la mano cumple con las restricciones usando función auxiliar
                cumple_min, cumple_max = VerificarRestriccionesMano(mano, rest)
                
                # Debug: mostrar resultados de verificación
                if idx > 1 and idx <= 3:
                    print(f"    Resultado verificación: Cumple_Min={cumple_min}, Cumple_Max={cumple_max}")
                
                # Calcular HCP total para esta mano
                hcp_actual = Calcular_HCP(
                    mano['Ss'] if pd.notna(mano['Ss']) else '',  # Picas
                    mano['Hs'] if pd.notna(mano['Hs']) else '',  # Corazones
                    mano['Ds'] if pd.notna(mano['Ds']) else '',  # Diamantes
                    mano['Cs'] if pd.notna(mano['Cs']) else ''   # Tréboles
                )
                
                # Asignar resultados de verificación generales ('Sí' o 'No')
                df_prueba.at[idx, 'Cumple_Min_HCP'] = 'Si' if hcp_actual >= rest['Min_HCP'] else 'No'
                df_prueba.at[idx, 'Cumple_Max_HCP'] = 'Si' if hcp_actual <= rest['Max_HCP'] else 'No'
                # Verificar restricciones por palo individual
                # Spades (Ss) - asignar 0 si no hay cartas
                cartas_s = len(mano['Ss']) if pd.notna(mano['Ss']) and mano['Ss'] != '' else 0
                df_prueba.at[idx, 'Cumple_Min_S'] = 'Si' if cartas_s >= rest['Min_S'] else 'No'
                df_prueba.at[idx, 'Cumple_Max_S'] = 'Si' if cartas_s <= rest['Max_S'] else 'No'
                
                # Hearts (Hs) - asignar 0 si no hay cartas
                cartas_h = len(mano['Hs']) if pd.notna(mano['Hs']) and mano['Hs'] != '' else 0
                df_prueba.at[idx, 'Cumple_Min_H'] = 'Si' if cartas_h >= rest['Min_H'] else 'No'
                df_prueba.at[idx, 'Cumple_Max_H'] = 'Si' if cartas_h <= rest['Max_H'] else 'No'
                
                # Diamonds (Ds) - asignar 0 si no hay cartas
                cartas_d = len(mano['Ds']) if pd.notna(mano['Ds']) and mano['Ds'] != '' else 0
                df_prueba.at[idx, 'Cumple_Min_D'] = 'Si' if cartas_d >= rest['Min_D'] else 'No'
                df_prueba.at[idx, 'Cumple_Max_D'] = 'Si' if cartas_d <= rest['Max_D'] else 'No'
                
                # Clubs (Cs) - asignar 0 si no hay cartas
                cartas_c = len(mano['Cs']) if pd.notna(mano['Cs']) and mano['Cs'] != '' else 0
                df_prueba.at[idx, 'Cumple_Min_C'] = 'Si' if cartas_c >= rest['Min_C'] else 'No'
                df_prueba.at[idx, 'Cumple_Max_C'] = 'Si' if cartas_c <= rest['Max_C'] else 'No'
            else:
                manos_sin_restricciones += 1
                # Si no hay restricciones, marcar como 'No aplica'
                df_prueba.at[idx, 'Cumple_Min_HCP'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Max_HCP'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Min_S'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Max_S'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Min_H'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Max_H'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Min_D'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Max_D'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Min_C'] = 'No aplica'
                df_prueba.at[idx, 'Cumple_Max_C'] = 'No aplica'
        
        # Mostrar resumen de procesamiento
        print(f"  Manos con restricciones: {manos_con_restricciones}")
        print(f"  Manos sin restricciones: {manos_sin_restricciones}")
        
        # Guardar archivo de prueba con todos los resultados
        df_prueba.to_csv(archivo_prueba, index=False)
        print(f"Archivo de prueba guardado: {archivo_prueba}")
        
        # Retornar DataFrame de prueba y total de manos procesadas
        return df_prueba, len(df_manos)
        
    except Exception as e:
        # Manejar errores durante el procesamiento
        print(f"Error procesando jugador {jugador}: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def MostrarResumenJugador(jugador, df_prueba, total_manos):
    """
    Muestra un resumen estadístico detallado de la verificación de restricciones para un jugador
    
    Args:
        jugador (str): Identificador del jugador ('E', 'N', 'S', 'W')
        df_prueba (pandas.DataFrame): DataFrame con los resultados de verificación
        total_manos (int): Número total de manos procesadas
    
    Returns:
        None: Solo imprime el resumen en consola
        
    Estadísticas mostradas:
        - Total de manos verificadas
        - Cumplimiento general de restricciones mínimas y máximas
        - Cumplimiento por palo individual (S, H, D, C)
        - Porcentajes de cumplimiento para cada restricción
        
    Nota:
        Si df_prueba o total_manos son None, la función no muestra nada
    """
    # Verificar que tenemos datos válidos para mostrar
    if df_prueba is None or total_manos is None:
        return
    
    # Calcular estadísticas de cumplimiento HCP
    manos_cumplen_min = len(df_prueba[df_prueba['Cumple_Min_HCP'] == 'Sí'])
    manos_cumplen_max = len(df_prueba[df_prueba['Cumple_Max_HCP'] == 'Sí'])
    
    # Calcular estadísticas por palo individual
    # Spades (S)
    manos_cumplen_min_s = len(df_prueba[df_prueba['Cumple_Min_S'] == 'Sí'])
    manos_cumplen_max_s = len(df_prueba[df_prueba['Cumple_Max_S'] == 'Sí'])
    
    # Hearts (H)
    manos_cumplen_min_h = len(df_prueba[df_prueba['Cumple_Min_H'] == 'Sí'])
    manos_cumplen_max_h = len(df_prueba[df_prueba['Cumple_Max_H'] == 'Sí'])
    
    # Diamonds (D)
    manos_cumplen_min_d = len(df_prueba[df_prueba['Cumple_Min_D'] == 'Sí'])
    manos_cumplen_max_d = len(df_prueba[df_prueba['Cumple_Max_D'] == 'Sí'])
    
    # Clubs (C)
    manos_cumplen_min_c = len(df_prueba[df_prueba['Cumple_Min_C'] == 'Sí'])
    manos_cumplen_max_c = len(df_prueba[df_prueba['Cumple_Max_C'] == 'Sí'])
    
    # Mostrar resumen general del jugador
    print(f"\n=== Resumen para jugador {jugador} ===")
    print(f"Total manos verificadas: {total_manos}")
    
    # Mostrar cumplimiento general
    porcentaje_min = (manos_cumplen_min / total_manos) * 100
    porcentaje_max = (manos_cumplen_max / total_manos) * 100
    print(f"\n--- Cumplimiento General ---")
    print(f"  Restricciones mínimas: {manos_cumplen_min}/{total_manos} ({porcentaje_min:.1f}%)")
    print(f"  Restricciones máximas: {manos_cumplen_max}/{total_manos} ({porcentaje_max:.1f}%)")
    
    # Mostrar cumplimiento por palo
    print(f"\n--- Cumplimiento por Palo ---")
    
    # Spades
    porcentaje_min_s = (manos_cumplen_min_s / total_manos) * 100
    porcentaje_max_s = (manos_cumplen_max_s / total_manos) * 100
    print(f"  Spades (S): Min {manos_cumplen_min_s}/{total_manos} ({porcentaje_min_s:.1f}%) | Max {manos_cumplen_max_s}/{total_manos} ({porcentaje_max_s:.1f}%)")
    
    # Hearts
    porcentaje_min_h = (manos_cumplen_min_h / total_manos) * 100
    porcentaje_max_h = (manos_cumplen_max_h / total_manos) * 100
    print(f"  Hearts (H): Min {manos_cumplen_min_h}/{total_manos} ({porcentaje_min_h:.1f}%) | Max {manos_cumplen_max_h}/{total_manos} ({porcentaje_max_h:.1f}%)")
    
    # Diamonds
    porcentaje_min_d = (manos_cumplen_min_d / total_manos) * 100
    porcentaje_max_d = (manos_cumplen_max_d / total_manos) * 100
    print(f"  Diamonds (D): Min {manos_cumplen_min_d}/{total_manos} ({porcentaje_min_d:.1f}%) | Max {manos_cumplen_max_d}/{total_manos} ({porcentaje_max_d:.1f}%)")
    
    # Clubs
    porcentaje_min_c = (manos_cumplen_min_c / total_manos) * 100
    porcentaje_max_c = (manos_cumplen_max_c / total_manos) * 100
    print(f"  Clubs (C): Min {manos_cumplen_min_c}/{total_manos} ({porcentaje_min_c:.1f}%) | Max {manos_cumplen_max_c}/{total_manos} ({porcentaje_max_c:.1f}%)")

def ProbarGenerarManosCalculadas(jugador):
    """
    Función que verifica que las manos generadas cumplan con las restricciones para un jugador específico
    
    Esta función orquesta el proceso de verificación para un jugador:
    1. Carga el archivo de trayectoria de subasta con las restricciones
    2. Procesa solo el jugador especificado
    3. Verifica cada mano contra las restricciones correspondientes
    4. Genera archivo de prueba con resultados detallados
    5. Muestra resumen estadístico del jugador
    
    Args:
        jugador (str): Identificador del jugador ('E', 'N', 'S', 'W')
    
    Archivos de entrada esperados:
        - trayectoria_subasta.csv: Contiene restricciones por tablero y jugador
        - df_manosCalcular_{jugador}.csv: Manos calculadas para el jugador especificado
    
    Archivos de salida generados:
        - df_pruebaManosCalcular_{jugador}.csv: Resultados de verificación para el jugador
    
    Returns:
        None: Solo ejecuta la verificación e imprime resultados
        
    Nota:
        Esta función se llama automáticamente desde main.py después de generar manos calculadas
    """
    
    # PASO 1: Cargar el archivo de trayectoria de subasta con las restricciones
    print(f"=== Iniciando verificación de manos calculadas para jugador {jugador} ===")
    df_trayectoria = CargarTrayectoriaSubasta()
    
    # Si no se pudo cargar la trayectoria, terminar la verificación
    if df_trayectoria is None:
        print("No se pudo cargar la trayectoria de subasta. Verificación cancelada.")
        return
    
    # PASO 2: Procesar solo el jugador especificado
    print(f"Verificando restricciones para jugador {jugador}...")
    print(f"\n--- Procesando jugador {jugador} ---")
    
    # Procesar y verificar todas las manos del jugador
    df_prueba, total_manos = ProcesarJugador(jugador, df_trayectoria)

    # PASO 3: Confirmar finalización del proceso
    print(f"\n=== Verificación de manos calculadas completada para jugador {jugador} ===")
    print(f"Se ha generado archivo de prueba: df_pruebaManosCalcular_{jugador}.csv")


def ValidarCondicionesNoEvaluar(jugador, dfTrayectoria):
    # Leer el archivo df_valor_esperado.csv
    dfValorEsperado = pd.read_csv('df_valor_esperado.csv')

     # Partner (último registro del compañero)
    jugador_partner = partners[jugador]
    df_partner = dfTrayectoria[dfTrayectoria['Jugador'] == jugador_partner]
    registro_partner = df_partner.iloc[-1] if not df_partner.empty else None
    # Oponente de la derecha (último registro)
    jugador_derecha = oponente_derecha[jugador]
    df_oponente_derecha = dfTrayectoria[dfTrayectoria['Jugador'] == jugador_derecha]
    registro_oponente_derecha = df_oponente_derecha.iloc[-1] if not df_oponente_derecha.empty else None
        # Oponente de la izquierda (es el oponente del oponente de la derecha)
    jugador_izquierda = partners[jugador_derecha]
    df_oponente_izquierda = dfTrayectoria[dfTrayectoria['Jugador'] == jugador_izquierda]
    registro_oponente_izquierda = df_oponente_izquierda.iloc[-1] if not df_oponente_izquierda.empty else None

    contratoOponente_derecha = (
        str(registro_oponente_derecha['Grilla'])
        if registro_oponente_derecha is not None
        else "0"
    )
    contratoOponente_izquierda = str(registro_oponente_izquierda['Grilla'])
      # Si tiene más de un dígito, toma solo el último
    if len(contratoOponente_derecha) > 1:
        contratoOponente_derecha = contratoOponente_derecha[-1]
    elif len(contratoOponente_derecha) == 1:
        contratoOponente_derecha = -1

    if len(contratoOponente_izquierda) > 1:
        contratoOponente_izquierda = contratoOponente_izquierda[-1]
    elif len(contratoOponente_izquierda) == 1:
        contratoOponente_izquierda = -1
      
        #si contratoOponente_derecha o contratoOponente_izquierda tiene mas de un digito cada valor se obtendra el ultimo digito para cada uno        
    apuestaOponente_derecha = int(contratoOponente_derecha)
    apuestaOponente_izquierda = int(contratoOponente_izquierda)
        #La voz del partner es forcing
        #si es forcing la voz del partner   
    if registro_partner is not None and 'Force' in registro_partner and registro_partner['Force'] == "Si":  
            #Consultar si el oponente pasó
        if registro_oponente_derecha is not None and registro_oponente_derecha['Grilla'] == '0':
            return "SI"
            #si el opononente de la derecha o izquierda dobló
        elif apuestaOponente_derecha == 1 or apuestaOponente_izquierda == 1:
            return "OPCIONAL"
        else:
            return "EVALUAR"
    else:
            #2.2 La voz del partner no es forcing
            #El oponente de la derecha  o izquierda dobló
        if apuestaOponente_derecha == 1 or apuestaOponente_izquierda == 1:           
            return "OPCIONAL"
        else:
            return "EVALUAR"
        

def BorrarDatosArchivoManosGeneradas():
    jugadores = ["N", "E", "S", "W"]

    for jugador in jugadores:
        nombre_archivo = f"df_manosCalcular_{jugador}.csv"

        if os.path.exists(nombre_archivo):
            try:
                # Leer archivo existente
                df = pd.read_csv(nombre_archivo)

                # Mantener solo la fila de encabezados → DataFrame vacío con mismas columnas
                df_vacio = df.iloc[0:0]

                # Guardar de nuevo el archivo sin borrar la fila de encabezados
                df_vacio.to_csv(nombre_archivo, index=False)
            except Exception as e:
                print(f"Error leyendo el archivo {nombre_archivo}: {e}")
        else:
            print(f"Archivo no encontrado (no se vacía): {nombre_archivo}")
