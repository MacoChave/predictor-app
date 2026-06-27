import json

try:
    with open('encuentros.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    filtered_data = []
    
    for match in data:
        comp = match.get('Competición', '')
        # Only keep competitions that explicitly contain '2026'
        if '2026' in comp:
            filtered_data.append(match)

    with open('encuentros.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=4)
        
    print(f'Filtrado completado. Registros originales: {len(data)}. Registros conservados (solo 2026): {len(filtered_data)}.')
    print(f'Se eliminaron {len(data) - len(filtered_data)} registros.')
except Exception as e:
    print(f"Error: {e}")
