import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from collections import Counter
from torch.nn.utils.rnn import pad_sequence, pack_padded_sequence
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'Modelo'))

BID_TOKENS = [
    "Pass", "X", "XX",
    "1Tre", "1Dia", "1Cor", "1Pic", "1NT",
    "2Tre", "2Dia", "2Cor", "2Pic", "2NT",
    "3Tre", "3Dia", "3Cor", "3Pic", "3NT",
    "4Tre", "4Dia", "4Cor", "4Pic", "4NT",
    "5Tre", "5Dia", "5Cor", "5Pic", "5NT",
    "6Tre", "6Dia", "6Cor", "6Pic", "6NT",
    "7Tre", "7Dia", "7Cor", "7Pic", "7NT"
]

BID2IDX = {bid: idx for idx, bid in enumerate(BID_TOKENS)}
IDX2BID = {idx: bid for bid, idx in BID2IDX.items()}

def calculate_grilla(bid):
    if bid == "Pass":
        return 0
    elif bid == "X":
        return 171
    elif bid == "XX":
        return 172
    else:
        if len(bid) >= 2:
            level = int(bid[0])
            suit = bid[1:]
            suit_values = {
                "Tre": 10,
                "Dia": 30,
                "Cor": 50,
                "Pic": 70,
                "NT": 90
            }
            suit_value = suit_values.get(suit, 0)
            return level * 100 + suit_value
    return 0

class SimpleVocab:
    def __init__(self):
        self.word2idx = {'<PAD>': 0, '<UNK>': 1}
        self.idx2word = {0: '<PAD>', 1: '<UNK>'}
        self.word_counts = Counter()
        self.next_idx = 2
    
    def add_sentence(self, sentence):
        words = str(sentence).lower().split()
        self.word_counts.update(words)
    
    def build(self, min_count=1):
        for word, count in self.word_counts.items():
            if count >= min_count and word not in self.word2idx:
                self.word2idx[word] = self.next_idx
                self.idx2word[self.next_idx] = word
                self.next_idx += 1
    
    def encode(self, sentence):
        words = str(sentence).lower().split()
        return [self.word2idx.get(word, 1) for word in words]
    
    def __len__(self):
        return len(self.word2idx)

class BridgeLSTMModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_layers, 
                 num_classes, dropout=0.3):
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(hidden_dim * 2, hidden_dim)
        self.relu = nn.ReLU()
        
        self.fc_classification = nn.Linear(hidden_dim, num_classes)
        
        self.fc_regression = nn.Linear(hidden_dim, 128)
        self.fc_regression_dropout = nn.Dropout(dropout)
        
        self.fc_hcp_min = nn.Linear(128, 1)
        self.fc_hcp_max = nn.Linear(128, 1)
        self.fc_s_min = nn.Linear(128, 1)
        self.fc_s_max = nn.Linear(128, 1)
        self.fc_h_min = nn.Linear(128, 1)
        self.fc_h_max = nn.Linear(128, 1)
        self.fc_d_min = nn.Linear(128, 1)
        self.fc_d_max = nn.Linear(128, 1)
        self.fc_c_min = nn.Linear(128, 1)
        self.fc_c_max = nn.Linear(128, 1)
    
    def forward(self, input_ids, lengths, legal_masks):
        embedded = self.embedding(input_ids)
        packed = pack_padded_sequence(embedded, lengths.cpu(), batch_first=True, enforce_sorted=False)
        packed_output, (hidden, cell) = self.lstm(packed)
        
        hidden_fwd = hidden[-2]
        hidden_bwd = hidden[-1]
        hidden_concat = torch.cat([hidden_fwd, hidden_bwd], dim=1)
        
        x = self.dropout(hidden_concat)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.dropout(x)
        
        logits = self.fc_classification(x)
        logits = logits.masked_fill(~legal_masks, -1e9)
        
        reg_features = self.fc_regression(x)
        reg_features = self.relu(reg_features)
        reg_features = self.fc_regression_dropout(reg_features)
        
        hcp_min = self.fc_hcp_min(reg_features).squeeze(-1)
        hcp_max = self.fc_hcp_max(reg_features).squeeze(-1)
        s_min = self.fc_s_min(reg_features).squeeze(-1)
        s_max = self.fc_s_max(reg_features).squeeze(-1)
        h_min = self.fc_h_min(reg_features).squeeze(-1)
        h_max = self.fc_h_max(reg_features).squeeze(-1)
        d_min = self.fc_d_min(reg_features).squeeze(-1)
        d_max = self.fc_d_max(reg_features).squeeze(-1)
        c_min = self.fc_c_min(reg_features).squeeze(-1)
        c_max = self.fc_c_max(reg_features).squeeze(-1)
        
        hcp_min = torch.clamp(hcp_min, 0, 40)
        hcp_max = torch.clamp(hcp_max, 0, 40)
        s_min = torch.clamp(s_min, 0, 13)
        s_max = torch.clamp(s_max, 0, 13)
        h_min = torch.clamp(h_min, 0, 13)
        h_max = torch.clamp(h_max, 0, 13)
        d_min = torch.clamp(d_min, 0, 13)
        d_max = torch.clamp(d_max, 0, 13)
        c_min = torch.clamp(c_min, 0, 13)
        c_max = torch.clamp(c_max, 0, 13)
        
        hcp_max = torch.max(hcp_max, hcp_min)
        s_max = torch.max(s_max, s_min)
        h_max = torch.max(h_max, h_min)
        d_max = torch.max(d_max, d_min)
        c_max = torch.max(c_max, c_min)
        
        regression_outputs = {
            'hcp_min': hcp_min,
            'hcp_max': hcp_max,
            's_min': s_min,
            's_max': s_max,
            'h_min': h_min,
            'h_max': h_max,
            'd_min': d_min,
            'd_max': d_max,
            'c_min': c_min,
            'c_max': c_max
        }
        
        return logits, regression_outputs

def construir_vocabulario_desde_datos():
    vocab = SimpleVocab()
    
    archivos_csv = [
        'Modelo/Base_de_trayectorias_entrenadas00.csv',
        'Modelo/Base_de_trayectorias_entrenadas1.csv'
    ]
    
    textos_procesados = 0
    for archivo in archivos_csv:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo, sep=',', encoding='iso-8859-1', nrows=5000)
                
                for _, row in df.iterrows():
                    try:
                        jugador = str(row.get('Jugador', 'N'))
                        hcp_min = row.get('Min_HCP', row.get('Min HCP', 0))
                        hcp_max = row.get('Max_HCP', row.get('Max HCP', 0))
                        hcp_avg = (float(hcp_min) + float(hcp_max)) / 2 if pd.notna(hcp_min) and pd.notna(hcp_max) else 0
                        
                        spades_min = row.get('Min_S', row.get('S_min', 0))
                        spades_max = row.get('Max_S', row.get('S_max', 0))
                        spades_avg = (float(spades_min) + float(spades_max)) / 2 if pd.notna(spades_min) and pd.notna(spades_max) else 0
                        
                        hearts_min = row.get('Min_H', row.get('H_min', 0))
                        hearts_max = row.get('Max_H', row.get('H_max', 0))
                        hearts_avg = (float(hearts_min) + float(hearts_max)) / 2 if pd.notna(hearts_min) and pd.notna(hearts_max) else 0
                        
                        diamonds_min = row.get('Min_D', row.get('D_min', 0))
                        diamonds_max = row.get('Max_D', row.get('D_max', 0))
                        diamonds_avg = (float(diamonds_min) + float(diamonds_max)) / 2 if pd.notna(diamonds_min) and pd.notna(diamonds_max) else 0
                        
                        clubs_min = row.get('Min_C', row.get('C_min', 0))
                        clubs_max = row.get('Max_C', row.get('C_max', 0))
                        clubs_avg = (float(clubs_min) + float(clubs_max)) / 2 if pd.notna(clubs_min) and pd.notna(clubs_max) else 0
                        
                        text = f"Jugador {jugador} con {hcp_avg:.1f} puntos promedio. "
                        text += f"Distribución promedio: {spades_avg:.1f} Picas, {hearts_avg:.1f} Corazones, "
                        text += f"{diamonds_avg:.1f} Diamantes, {clubs_avg:.1f} Tréboles. "
                        text += "Primera voz de la subasta. "
                        
                        vocab.add_sentence(text)
                        textos_procesados += 1
                    except Exception:
                        continue
            except Exception as e:
                print(f"Error al cargar {archivo}: {e}")
    
    # AÑADIR TOKENS DE SUBASTA EXPLÍCITAMENTE
    for token in BID_TOKENS:
        vocab.add_sentence(token)
        
    vocab.build(min_count=1)
    if textos_procesados > 0:
        print(f"Vocabulario construido con {textos_procesados} textos, tamaño: {len(vocab)}")
    return vocab

vocab = construir_vocabulario_desde_datos()

# Las bases de datos de trayectorias ya no son necesarias para la predicción del modelo.
# Se deja el código de vocabulario por si es necesario reconstruirlo, pero la predicción principal
# ahora se basa en el modelo de PyTorch.
df_trayectorias_entrenamiento = pd.DataFrame()



device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

modelo_path = 'Modelo/best_bridge_real_model.pt'
if not os.path.exists(modelo_path):
    modelo_path = 'best_bridge_real_model.pt'

if os.path.exists(modelo_path):
    try:
        print(f"Cargando modelo desde: {modelo_path}")
        checkpoint = torch.load(modelo_path, map_location=device)
        
        if isinstance(checkpoint, nn.Module):
            modelo = checkpoint
            modelo.eval()
            print("Modelo completo cargado - usando pesos guardados")
        else:
            state_dict = checkpoint.get('state_dict', checkpoint) if isinstance(checkpoint, dict) else checkpoint
            
            vocab_size_modelo = len(vocab)
            if 'embedding.weight' in state_dict:
                vocab_size_modelo = state_dict['embedding.weight'].shape[0]
                print(f"Tamaño de vocabulario del modelo guardado: {vocab_size_modelo}")
                if vocab_size_modelo != len(vocab):
                    print(f"Vocabulario actual: {len(vocab)} palabras (el modelo usará {vocab_size_modelo})")
            
            modelo = BridgeLSTMModel(
                vocab_size=vocab_size_modelo,
                embedding_dim=128,
                hidden_dim=256,
                num_layers=2,
                num_classes=len(BID_TOKENS),
                dropout=0.4
            ).to(device)
            
            modelo.load_state_dict(state_dict, strict=False)
            modelo.eval()
            print("Pesos del modelo cargados desde best_bridge_real_model.pt")
            print("El modelo está listo para hacer predicciones (HCP, grilla, subasta)")
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
        print("Creando modelo nuevo con pesos aleatorios")
        modelo = BridgeLSTMModel(
            vocab_size=len(vocab),
            embedding_dim=128,
            hidden_dim=256,
            num_layers=2,
            num_classes=len(BID_TOKENS),
            dropout=0.4
        ).to(device)
else:
    print(f"No se encontró el archivo del modelo en {modelo_path}")
    print("Creando modelo nuevo con pesos aleatorios")
    modelo = BridgeLSTMModel(
        vocab_size=len(vocab),
        embedding_dim=128,
        hidden_dim=256,
        num_layers=2,
        num_classes=len(BID_TOKENS),
        dropout=0.4
    ).to(device)

def ejecutar_modelo(df_HCP_jugador, df_trayectoria_board=None):
    if df_HCP_jugador is None or df_HCP_jugador.empty:
        print("Error: El DataFrame de HCP está vacío o es nulo.")
        return None

    # --- 1. OBTENER DATOS DEL JUGADOR Y CONSTRUIR TEXTO DE ENTRADA ---
    jugador = df_HCP_jugador['Jugador'].iloc[0]
    hcp_avg = (float(df_HCP_jugador['Min_HCP'].iloc[0]) + float(df_HCP_jugador['Max_HCP'].iloc[0])) / 2
    
    auction_history = []
    if df_trayectoria_board is not None and not df_trayectoria_board.empty and 'Subasta' in df_trayectoria_board.columns:
        auction_history = [str(s).strip() for s in df_trayectoria_board['Subasta'].tolist() if pd.notna(s) and str(s).strip() != '']

    # Extraer distribución de palos del DataFrame
    # Asumimos que las columnas son 'Min_S', 'Max_S' o similar. Usamos el promedio.
    s_avg = (float(df_HCP_jugador['Min_S'].iloc[0]) + float(df_HCP_jugador['Max_S'].iloc[0])) / 2
    h_avg = (float(df_HCP_jugador['Min_H'].iloc[0]) + float(df_HCP_jugador['Max_H'].iloc[0])) / 2
    d_avg = (float(df_HCP_jugador['Min_D'].iloc[0]) + float(df_HCP_jugador['Max_D'].iloc[0])) / 2
    c_avg = (float(df_HCP_jugador['Min_C'].iloc[0]) + float(df_HCP_jugador['Max_C'].iloc[0])) / 2

    text = f"Jugador {jugador} con {hcp_avg:.1f} puntos promedio. "
    text += f"Distribución promedio: {s_avg:.1f} Picas, {h_avg:.1f} Corazones, "
    text += f"{d_avg:.1f} Diamantes, {c_avg:.1f} Tréboles. "

    if auction_history:
        text += f"Subasta previa: {' - '.join(auction_history)}. "
    else:
        text += "Primera voz de la subasta. "
    
    tokens = vocab.encode(text)
    tokens_tensor = torch.tensor([tokens], dtype=torch.long).to(device)
    length_tensor = torch.tensor([len(tokens)], dtype=torch.long).to(device)

    # --- 2. CALCULAR MÁSCARA DE SUBASTAS LEGALES ---
    max_grilla_actual = 0
    if auction_history:
        for bid in auction_history:
            max_grilla_actual = max(max_grilla_actual, calculate_grilla(bid))

    legal_mask = np.zeros(len(BID_TOKENS), dtype=bool)
    for i, bid in enumerate(BID_TOKENS):
        # 'Pass' es siempre legal.
        # Un 'X' es legal si la última subasta no fue un Pass, no fue un XX, y no fue hecha por el compañero.
        # Un 'XX' es legal si la última subasta fue un X y no fue hecha por el compañero.
        # Otras subastas son legales si su grilla es mayor a la máxima actual.
        if bid == "Pass":
            legal_mask[i] = True
            continue
        
        # Lógica simplificada para determinar legalidad. Una implementación real requiere más contexto.
        # Por ahora, consideramos cualquier subasta con grilla mayor como legal.
        if calculate_grilla(bid) > max_grilla_actual:
            legal_mask[i] = True

    legal_mask_tensor = torch.tensor([legal_mask], dtype=torch.bool).to(device)

    # --- 3. EJECUTAR EL MODELO ---
    with torch.no_grad():
        logits, regression_outputs = modelo(tokens_tensor, length_tensor, legal_mask_tensor)
        probabilities = F.softmax(logits, dim=-1)
        _, predicted_idx = torch.max(probabilities, 1)
        predicted_bid = IDX2BID[predicted_idx.item()]

    print(f"Predicción del modelo: {predicted_bid}")

    # --- 4. EXTRAER RESULTADOS DE REGRESIÓN ---
    hcp_min_pred = regression_outputs['hcp_min'].item()
    hcp_max_pred = regression_outputs['hcp_max'].item()
    s_min_pred = regression_outputs['s_min'].item()
    s_max_pred = regression_outputs['s_max'].item()
    h_min_pred = regression_outputs['h_min'].item()
    h_max_pred = regression_outputs['h_max'].item()
    d_min_pred = regression_outputs['d_min'].item()
    d_max_pred = regression_outputs['d_max'].item()
    c_min_pred = regression_outputs['c_min'].item()
    c_max_pred = regression_outputs['c_max'].item()

    # --- 5. CONSTRUIR Y RETORNAR EL RESULTADO ---
    # Los valores de Desc_o_Pre, Force, Alert, Conv no son predecibles por este modelo, se dejan en blanco/default.
    resultado = [
        0,  # Placeholder para Board
        0,  # Placeholder para Mano
        predicted_bid,
        int(calculate_grilla(predicted_bid)),
        '',  # Desc_o_Pre
        'No', # Force
        'No', # Alert
        '',   # Conv
        int(hcp_min_pred),
        int(hcp_max_pred),
        int(s_min_pred),
        int(s_max_pred),
        int(h_min_pred),
        int(h_max_pred),
        int(d_min_pred),
        int(d_max_pred),
        int(c_min_pred),
        int(c_max_pred)
    ]
    
    return resultado
