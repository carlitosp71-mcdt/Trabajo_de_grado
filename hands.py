import pandas as pd
import functions

print("=== DIAGNÓSTICO ESPECÍFICO PARA JUGADOR W ===")

# Cargar los archivos necesarios
df_trayectoria = pd.read_csv('trayectoria_subasta.csv', sep=';')

# Verificar restricciones disponibles para W
print("1. Restricciones disponibles para jugador W:")
w_restrictions = df_trayectoria[df_trayectoria['Jugador'] == 'W']
print(f"   Total restricciones para W: {len(w_restrictions)}")
print(w_restrictions[['Tablero', 'Jugador', 'Min_HCP', 'Max_HCP']])

# Verificar restricciones para Tablero=3 y Jugador=W
print("\n2. Restricciones específicas para Tablero=3, Jugador=W:")
w_tablero3 = df_trayectoria[(df_trayectoria['Tablero'] == 3) & (df_trayectoria['Jugador'] == 'W')]
print(f"   Restricciones encontradas: {len(w_tablero3)}")
if len(w_tablero3) > 0:
    print(w_tablero3[['Tablero', 'Jugador', 'Min_HCP', 'Max_HCP', 'Min_S', 'Max_S']].iloc[0])

# Cargar archivo de manos y verificar manos del jugador W
print("\n3. Manos del jugador W en df_manosCalcular_E.csv:")
df_manos = pd.read_csv('df_manosCalcular_E.csv')
w_manos = df_manos[df_manos['Jugador'] == 'W']
print(f"   Total manos W: {len(w_manos)}")
print("   Primeras 3 manos W:")
print(w_manos[['Tablilla', 'Jugador']].head(3))

# Simular la búsqueda de restricciones para las primeras manos W
print("\n4. Simulación de búsqueda de restricciones:")
for idx, mano in w_manos.head(3).iterrows():
    tablilla = mano['Tablilla']
    jugador_mano = mano['Jugador']
    
    print(f"   Mano {idx}: Tablilla={tablilla}, Jugador={jugador_mano}")
    
    # Buscar restricciones como lo hace la función
    restricciones = df_trayectoria[
        (df_trayectoria['Tablero'] == tablilla) & 
        (df_trayectoria['Jugador'] == jugador_mano)
    ]
    
    print(f"     Restricciones encontradas: {len(restricciones)}")
    if len(restricciones) > 0:
        print(f"     Restricciones: Min_HCP={restricciones.iloc[0]['Min_HCP']}, Max_HCP={restricciones.iloc[0]['Max_HCP']}")
    else:
        print(f"     NO se encontraron restricciones!")
        print(f"     Valores únicos en df_trayectoria['Tablero']: {df_trayectoria['Tablero'].unique()}")
        print(f"     Valores únicos en df_trayectoria['Jugador']: {df_trayectoria['Jugador'].unique()}")

# Probar la función ProcesarJugador para W
print("\n5. Probar función ProcesarJugador para W:")
df_prueba, total_manos = functions.ProcesarJugador('W', df_trayectoria)

if df_prueba is not None:
    print(f"   Procesamiento exitoso: {total_manos} manos procesadas")
    
    # Verificar manos del jugador W específicamente
    w_manos_resultado = df_prueba[df_prueba['Jugador'] == 'W']
    print(f"   Manos del jugador W en resultado: {len(w_manos_resultado)}")
    
    # Verificar si hay manos W con "No aplica"
    w_no_aplica = w_manos_resultado[w_manos_resultado['Cumple_Min'] == 'No aplica']
    print(f"   Manos W con 'No aplica': {len(w_no_aplica)}")
    
    if len(w_no_aplica) > 0:
        print("   Primeras manos W con 'No aplica':")
        print(w_no_aplica[['Tablilla', 'Jugador', 'Min_HCP', 'Max_HCP', 'Cumple_Min']].head(3))
    
    # Verificar manos W que SÍ tienen restricciones
    w_con_restricciones = w_manos_resultado[w_manos_resultado['Cumple_Min'] != 'No aplica']
    print(f"   Manos W con restricciones: {len(w_con_restricciones)}")
    
    if len(w_con_restricciones) > 0:
        print("   Primeras manos W con restricciones:")
        print(w_con_restricciones[['Tablilla', 'Jugador', 'Min_HCP', 'Max_HCP', 'Cumple_Min', 'Cumple_Max']].head(3))
else:
    print("   Error en el procesamiento")
