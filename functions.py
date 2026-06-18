import pandas as pd
import hands
import os

def diagnosticar_solver():
    """Diagnostica por qué el solver no respeta las restricciones de HCP"""
    
    print("=== Diagnóstico del Solver de Reparto de Cartas ===")
    
    # Crear un DataFrame de trayectoria con restricciones específicas
    df_trayectoria = pd.DataFrame({
        'Jugador': ['N', 'E', 'S', 'W'],
        'Min_HCP': [10, 15, 5, 8],
        'Max_HCP': [12, 18, 8, 12],
        'Min_S': [3, 0, 0, 0],
        'Max_S': [4, 6, 4, 6],
        'Min_H': [3, 0, 0, 0],
        'Max_H': [4, 6, 4, 6],
        'Min_D': [3, 0, 0, 0],
        'Max_D': [4, 6, 4, 6],
        'Min_C': [0, 2, 0, 0],
        'Max_C': [3, 9, 6, 6]
    })
    
    print("Restricciones configuradas:")
    for _, row in df_trayectoria.iterrows():
        print(f"  {row['Jugador']}: HCP {row['Min_HCP']}-{row['Max_HCP']}")
    
    # Configurar parámetros de prueba
    i = 0
    mano_actual = 2  # Para aplicar restricciones
    jugador_fijo = 'N'
    jugadores = ['N', 'E', 'S', 'W']
    
    # Verificar si existe el archivo de manos
    nombre_archivo = f"df_manosCalcular_{jugador_fijo}.csv"
    if os.path.exists(nombre_archivo):
        print(f"\nArchivo {nombre_archivo} encontrado")
        df_manos = pd.read_csv(nombre_archivo)
        print(f"Total de manos en archivo: {len(df_manos)}")
        
        # Verificar tablero específico
        fila_tablero = df_manos[df_manos['Tablero'] == i + 1]
        if not fila_tablero.empty:
            print(f"Manos encontradas para tablero {i + 1}: {len(fila_tablero)}")
            
            # Obtener las cartas fijas del archivo para el jugador fijo
            fila_jugador = fila_tablero[fila_tablero['Jugador'] == jugador_fijo]
            if not fila_jugador.empty:
                cartas_fijas = hands.reconstruir_mano(fila_jugador.iloc[0])
                print(f"\nCartas fijas para {jugador_fijo} (del archivo): {cartas_fijas}")
                print(f"HCP de cartas fijas: {hands.calculate_hcp_py(cartas_fijas)}")
                
                # Mostrar todas las manos del tablero
                for _, row in fila_tablero.iterrows():
                    jugador_archivo = str(row['Jugador']).strip().upper()
                    print(f"  {jugador_archivo}: {row['Ss']} {row['Hs']} {row['Ds']} {row['Cs']}")
                
                # Probar el solver
                print(f"\n=== Probando Solver ===")
                try:
                    manos_generadas = hands.solver_reparto_cartas(
                        i, mano_actual, cartas_fijas, jugador_fijo, jugadores, df_trayectoria
                    )
                    
                    if manos_generadas:
                        print("✅ Solver encontró solución")
                        print("\n=== Manos Generadas ===")
                        for jugador, mano in manos_generadas.items():
                            hcp = hands.calculate_hcp_py(mano)
                            min_hcp = df_trayectoria[df_trayectoria['Jugador'] == jugador]['Min_HCP'].iloc[0]
                            max_hcp = df_trayectoria[df_trayectoria['Jugador'] == jugador]['Max_HCP'].iloc[0]
                            
                            print(f"\n{jugador}:")
                            print(f"  Mano: {mano}")
                            print(f"  HCP: {hcp} (rango permitido: {min_hcp}-{max_hcp})")
                            
                            # Verificar que cumple las restricciones
                            cumple_min = hcp >= min_hcp
                            cumple_max = hcp <= max_hcp
                            print(f"  Cumple mínimo: {'Sí' if cumple_min else 'No'}")
                            print(f"  Cumple máximo: {'Sí' if cumple_max else 'No'}")
                            
                            if not (cumple_min and cumple_max):
                                print(f"  ❌ ERROR: {jugador} no cumple restricciones de HCP!")
                            else:
                                print(f"  ✅ {jugador} cumple restricciones de HCP")
                    else:
                        print("❌ Solver NO encontró solución (retornó None)")
                        print("Esto puede indicar que las restricciones son muy estrictas o conflictivas")
                        
                except Exception as e:
                    print(f"❌ Error al ejecutar solver: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"No se encontró la mano para el jugador {jugador_fijo} en el tablero {i + 1}")
        else:
            print(f"No se encontraron manos para tablero {i + 1}")
    else:
        print(f"\nArchivo {nombre_archivo} NO encontrado")
        print("Generando manos aleatorias sin restricciones...")
        
        # Probar con manos aleatorias
        cartas_fijas = ['AS', 'KS', 'QS', 'JS', 'AH', 'KH', 'QH', 'JH', 'AD', 'KD', 'QD', 'JD', 'AC']
        print(f"Cartas fijas para {jugador_fijo}: {cartas_fijas}")
        print(f"HCP de cartas fijas: {hands.calculate_hcp_py(cartas_fijas)}")
        
        try:
            manos_generadas = hands.solver_reparto_cartas(
                i, 1, cartas_fijas, jugador_fijo, jugadores, df_trayectoria
            )
            
            if manos_generadas:
                print("✅ Solver encontró solución")
                print("\n=== Manos Generadas ===")
                for jugador, mano in manos_generadas.items():
                    hcp = hands.calculate_hcp_py(mano)
                    print(f"\n{jugador}: HCP {hcp}, Mano: {mano}")
            else:
                print("❌ Solver NO encontró solución")
                
        except Exception as e:
            print(f"❌ Error al ejecutar solver: {e}")

if __name__ == "__main__":
    diagnosticar_solver()
