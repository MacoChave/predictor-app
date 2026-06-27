import json

try:
    with open('encuentros.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    seen = set()
    cleaned_data = []
    
    for match in data:
        key = (match.get('Equipo 1'), match.get('Equipo 2'), match.get('Competición'))
        if key not in seen:
            seen.add(key)
            cleaned_data.append(match)

    with open('encuentros.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
        
    print(f'Limpieza completada. Registros originales: {len(data)}. Registros después de limpieza: {len(cleaned_data)}.')
    print(f'Se eliminaron {len(data) - len(cleaned_data)} registros duplicados.')
except Exception as e:
    print(f"Error: {e}")
