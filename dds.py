
import dds
import ctypes
import hands
import functions
import csv
import pandas as pd
from collections import defaultdict

DDdeals = dds.ddTableDeals()
tableRes = dds.ddTablesRes()
pres = dds.allParResults()

mode = 0
# Probably the definition of trumpFilter should go to dds.py
tFilter = ctypes.c_int * dds.DDS_STRAINS
trumpFilter = tFilter(0, 0, 0, 0, 0)
line = ctypes.create_string_buffer(80)

dds.SetMaxThreads(0)

DDdeals.noOfTables = hands.noOfTables
# Verificación de duplicados antes de asignar las manos
card_counts = defaultdict(int)  # Diccionario para contar cartas

# Definir las columnas del DataFrame
columnas = ["Tablero", "Jugador", "NT_Bazas", "Ss_Bazas", "Hs_Bazas", "Ds_Bazas", "Cs_Bazas"]
# Crear un DataFrame vacío con esas columnas
df_manosCalculadas = pd.DataFrame(columns=columnas)


   
#Genera las manos en la estructura DDdeals.deals para realizar los calculos	
def Generar_Manos_ManoN(holdings):
    for handno in range(DDdeals.noOfTables):
        for h in range(dds.DDS_HANDS):  # Número de manos (normalmente 4)
            for s in range(dds.DDS_SUITS):  # Número de palos (4)
                # Copia las cartas generadas en la estructura DDdeals.deals
                DDdeals.deals[handno].cards[h][s] = holdings[handno][h][s]



def GenerarManosCalculos(apuesta, jugador, vulnerable, declarante,mano_actual):
    global df_manosCalculadas  # Declare df_results as global within the function
    df_manosCalculadas = pd.DataFrame()  # Vaciar el DataFrame
    # Reinicializar tableRes para limpiar resultados anteriores
    tableRes = dds.ddTablesRes()
    res = dds.CalcAllTables(ctypes.pointer(DDdeals), mode, trumpFilter, ctypes.pointer(tableRes), ctypes.pointer(pres))

    if res != dds.RETURN_NO_FAULT:
        dds.ErrorMessage(res, line)
        #print("DDS error: {}".format(line.value.decode("utf-8")))
        return  # Or return df_manosCalculadas

    else:  # Si no hay error, continuar con el procesamiento
        for handno in range(DDdeals.noOfTables):
            match = functions.CompareTable(ctypes.pointer(tableRes.results[handno]), handno)

            line = "CalcDDtable, hand {}: {}".format(
                handno + 1, "OK" if res == dds.RETURN_NO_FAULT else "ERROR")

#genera dataframe de las manos calculadas
            df_manosCalculadas = functions.GenerarDF(ctypes.pointer(tableRes.results[handno]), handno, df_manosCalculadas)
            # mostrar el número de filas que tiene el dataframe
#guardar el dataframe de las manos calculadas
    dfManos= GuardarManosDF(hands.PBN,tableRes,mano_actual, jugador)   

    dfUnificado = functions.UnificarDF(dfManos, df_manosCalculadas,'df_manosCalcular.csv')
    dfUnificadoJugador = functions.UnificarDFJugador(dfManos, df_manosCalculadas,'df_manosCalcular_'+ jugador +'.csv')
    
    df_resultadoVuln= functions.GenerarDfManosCalculadas(declarante,vulnerable, jugador)
    
    #unificar el dataframe de las manos calculadas con el dataframe de la vulnerabilidad
    dfUnificadoManosCal_Vul = pd.merge(dfUnificado, df_resultadoVuln, on=['Tablero', 'Jugador'], how='inner')
    #dfUnificadoManosCal_Vul.to_csv("dfUnificadoManosCal_Vul.csv", index=False)
    print("Determinar contratos optimos de las manos calculadas")
    #Generar los contratos óptimos de las manos calculadas, se envía el jugador principal  
    #retorna el mejor contrato y el mejor puntaje del jugador principal
    df_valor_esperado  = functions.DeterminarContratos_Optimo(dfUnificadoManosCal_Vul,apuesta,jugador,declarante)
   
    return df_valor_esperado


#Guarda las manos en un dataframe
def GuardarManosDF(pbn_hands, table_results,mano_actual, jugador):
#Crea un DataFrame con manos PBN y resultados de la tabla.
    data = []

    for board_index, board in enumerate(pbn_hands):
        board_str = board.decode('utf-8') if isinstance(board, bytes) else board
        parts = board_str.strip().split(" ")
        hands = parts[0].split(":")[1:] + parts[1:]  # Separar las manos
        jugadores = ["N", "E", "S", "W"]

        for player_index, hand in enumerate(hands):
            suit_cards = hand.split('.')

            # Obtener resultados de la tabla
            table_res = table_results.results[board_index]
            nt = table_res.resTable[4]  # NT (No Trump)
            suit_res = [table_res.resTable[s] for s in range(dds.DDS_SUITS)]

            # Crear diccionario con los datos del jugador
            row = {
                "Tablilla": mano_actual,
                "Tablero": board_index + 1,
                "Declarante": jugador,
                "Jugador":  jugadores[player_index],
                "Ss": suit_cards[0],
                "Hs": suit_cards[1],
                "Ds": suit_cards[2],
                "Cs": suit_cards[3]
            }
            data.append(row)

    df = pd.DataFrame(data)  # Crear el DataFrame directamente
    return df  # Devolver el DataFrame

