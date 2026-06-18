import pandas as pd
import functions

# Cargar los archivos necesarios
df_manos = pd.read_csv('df_manosCalcular_E.csv')
df_trayectoria = pd.read_csv('trayectoria_subasta.csv', sep=';')

print("=== PRUEBA DE FUNCIONES CORREGIDAS ===")
print(f"Manos cargadas: {len(df_manos)}")
print(f"Restricciones cargadas: {len(df_trayectoria)}")

# Probar la función ProcesarJugador
print("\n=== PROBANDO ProcesarJugador ===")
df_prueba, total_manos = functions.ProcesarJugador('E', df_trayectoria)

if df_prueba is not None:
    print(f"Procesamiento exitoso: {total_manos} manos procesadas")
    print(f"Columnas en resultado: {df_prueba.columns.tolist()}")
    
    # Mostrar algunas filas de resultado
    print("\nPrimeras 3 filas del resultado:")
    print(df_prueba[['Tablilla', 'Jugador', 'Cumple_Min', 'Cumple_Max']].head(3))
    
    # Verificar si hay manos con "No aplica"
    manos_no_aplica = df_prueba[df_prueba['Cumple_Min'] == 'No aplica']
    print(f"\nManos con 'No aplica': {len(manos_no_aplica)}")
    
    if len(manos_no_aplica) > 0:
        print("Primeras manos con 'No aplica':")
        print(manos_no_aplica[['Tablilla', 'Jugador', 'Cumple_Min']].head(3))
else:
    print("Error en el procesamiento")
