import json
import os
import sys

# Agregamos el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

def main():
    if not MONGO_URI:
        print("Error: MONGO_URI no está definido en el archivo .env")
        sys.exit(1)

    print(f"Conectando a MongoDB: {MONGO_URI}")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Probamos la conexión
        client.admin.command('ping')
        print("Conexión exitosa a MongoDB!")
    except Exception as e:
        print(f"Error al conectar con MongoDB: {e}")
        sys.exit(1)

    db = client[MONGO_DB_NAME]
    collection = db[MONGO_COLLECTION]

    try:
        with open('encuentros.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró 'encuentros.json' en la raíz del proyecto.")
        sys.exit(1)

    if not data:
        print("No hay datos en encuentros.json.")
        sys.exit(0)

    print(f"Se encontraron {len(data)} registros en encuentros.json.")
    print(f"Insertando en la base de datos '{MONGO_DB_NAME}', colección '{MONGO_COLLECTION}'...")
    
    # Limpiamos la colección antes de insertar para evitar duplicados en la migración
    collection.delete_many({})
    
    result = collection.insert_many(data)
    print(f"Migración completada. Se insertaron {len(result.inserted_ids)} documentos.")

if __name__ == '__main__':
    main()
