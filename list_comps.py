import json

try:
    with open('encuentros.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    comps = set(match.get('Competición', '') for match in data)
    for c in sorted(comps):
        print(c)
except Exception as e:
    print(f"Error: {e}")
