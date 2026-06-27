import json
from collections import defaultdict

try:
    with open('encuentros.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    counts = defaultdict(list)
    for i, match in enumerate(data):
        # We also want to treat Equipo 1 vs Equipo 2 same as Equipo 2 vs Equipo 1? 
        # The prompt says: "en base a Equipo 1, Equipo 2 y Competición"
        # I'll just use them strictly as written first.
        key = (match.get('Equipo 1'), match.get('Equipo 2'), match.get('Competición'))
        counts[key].append((i, match))

    duplicates = {k: v for k, v in counts.items() if len(v) > 1}

    if not duplicates:
        print('No se encontraron registros duplicados con esa combinación.')
    else:
        print(f'Se encontraron {len(duplicates)} combinaciones duplicadas:\n')
        for k, v in duplicates.items():
            print(f'Equipo 1: {k[0]} | Equipo 2: {k[1]} | Competición: {k[2]}')
            for i, match in v:
                print(f'  - Índice {i}: {match.get("Equipo 1")} {match.get("Gol Equipo 1")} - {match.get("Gol Equipo 2")} {match.get("Equipo 2")}')
            print()
except Exception as e:
    print(f"Error: {e}")
