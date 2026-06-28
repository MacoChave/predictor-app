import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "predictor_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "encuentros")
# Peso por competición — más importante = más peso en la predicción
COMPETITION_WEIGHTS = {
    # Inglés (formato football-data.org)
    "FIFA World Cup": 2.5,
    "UEFA European Championship": 2.3,
    "Copa América": 2.0,
    "UEFA Champions League": 2.0,
    "UEFA Europa League": 1.7,
    "UEFA Europa Conference League": 1.5,
    "Premier League": 1.6,
    "La Liga": 1.6,
    "Bundesliga": 1.5,
    "Serie A": 1.5,
    "Ligue 1": 1.4,
    "Eredivisie": 1.3,
    "Primeira Liga": 1.3,
    "Copa del Rey": 1.4,
    "DFB-Pokal": 1.3,
    "FA Cup": 1.3,
    "Coupe de France": 1.2,
    "Friendly": 0.5,
    # Español (formato encuentros.json)
    "Copa Mundial de la FIFA": 2.5,
    "Eurocopa": 2.3,
    "Copa de Oro de la CONCACAF": 1.8,
    "Copa de Naciones de la OFC": 1.6,
    "Copa Africana de Naciones": 1.8,
    "Copa Asiática de la AFC": 1.8,
    "Nations League": 1.5,
    "Liga de Naciones de la UEFA": 1.5,
    "Liga de Naciones de la CONCACAF": 1.5,
    "Amistoso": 0.5,
    "default": 1.0,
}

RECENCY_DECAY = 0.88        # Cada partido más antiguo pesa un 12% menos
MAX_H2H_MATCHES = 20        # Máximo de partidos H2H a analizar
FETCH_LIMIT = 50            # Partidos a traer por equipo para buscar H2H
RANKING_QUALITY_MAX = 0.5   # Bonus máximo de peso por enfrentar al rival #1 del mundo (+50%)
