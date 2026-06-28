import json
import re
import unicodedata
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME, MONGO_COLLECTION

class FootballAPIError(Exception):
    pass


def normalize_string(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def _strip_year(competition: str) -> str:
    """'Copa Mundial de la FIFA (2010)' → 'Copa Mundial de la FIFA'."""
    return re.sub(r'\s*\(\d{4}\)\s*$', '', competition).strip()


class FootballAPIClient:

    def __init__(self):
        self._load_encuentros()

    def _load_encuentros(self) -> None:
        if not MONGO_URI:
            raise FootballAPIError(
                "No se configuró MONGO_URI. Agrega MONGO_URI=<url> en el archivo .env"
            )
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client[MONGO_DB_NAME]
            collection = db[MONGO_COLLECTION]
            self.encuentros = list(collection.find({}, {"_id": 0}))
        except Exception as exc:
            raise FootballAPIError(f"Error al conectar con MongoDB o leer colección: {exc}")

        teams_set = set()
        comps_set = set()
        self.team_rankings = {}
        for match in self.encuentros:
            t1 = match.get("Equipo 1")
            t2 = match.get("Equipo 2")
            r1 = match.get("Ranking Equipo 1")
            r2 = match.get("Ranking Equipo 2")
            comp = match.get("Competición")

            if t1:
                teams_set.add(t1)
                if r1 is not None:
                    self.team_rankings[t1] = r1
            if t2:
                teams_set.add(t2)
                if r2 is not None:
                    self.team_rankings[t2] = r2
            if comp:
                comps_set.add(comp)

        self.unique_teams = sorted(list(teams_set))
        self.unique_competitions = sorted(list(comps_set))
        self.team_to_id = {name: i + 1 for i, name in enumerate(self.unique_teams)}
        self.id_to_team = {i + 1: name for i, name in enumerate(self.unique_teams)}

    def search_teams(self, name: str) -> list[dict]:
        query_norm = normalize_string(name)
        results = []
        for t_name in self.unique_teams:
            if query_norm in normalize_string(t_name):
                results.append({
                    "id": self.team_to_id[t_name],
                    "name": t_name,
                    "ranking": self.team_rankings.get(t_name),
                    "area": {"name": "Copa Mundial 2026"}
                })
        return results

    def get_team(self, team_id: int) -> dict:
        name = self.id_to_team.get(team_id)
        if not name:
            raise FootballAPIError(f"Equipo con ID {team_id} no encontrado.")
        return {
            "id": team_id,
            "name": name,
            "ranking": self.team_rankings.get(name),
            "area": {"name": "Copa Mundial 2026"}
        }

    def get_team_matches(self, team_id: int, status: str = "FINISHED") -> list[dict]:
        team_name = self.id_to_team.get(team_id)
        if not team_name:
            return []

        matches = []
        for match in self.encuentros:
            t1 = match.get("Equipo 1")
            t2 = match.get("Equipo 2")
            if t1 != team_name and t2 != team_name:
                continue

            g1 = match.get("Gol Equipo 1")
            g2 = match.get("Gol Equipo 2")
            if g1 is None or g2 is None:
                continue

            comp_raw = match.get("Competición", "Unknown")
            comp = _strip_year(comp_raw)

            year_match = re.search(r"\((\d{4})\)", comp_raw)
            utc_date = f"{year_match.group(1)}-01-01T00:00:00Z" if year_match else "1970-01-01T00:00:00Z"

            r1 = match.get("Ranking Equipo 1")
            r2 = match.get("Ranking Equipo 2")

            matches.append({
                "homeTeam": {"id": self.team_to_id.get(t1, 0), "name": t1},
                "awayTeam": {"id": self.team_to_id.get(t2, 0), "name": t2},
                "score": {"fullTime": {"home": g1, "away": g2}},
                "utcDate": utc_date,
                "competition": {"name": comp},
                "rankingHome": r1,
                "rankingAway": r2,
            })
        return matches

    def reload(self) -> None:
        """Recarga los datos desde MongoDB."""
        self._load_encuentros()

    def clear_cache(self) -> None:
        pass

    def add_match(self, match_data: dict) -> None:
        if not MONGO_URI:
            raise FootballAPIError("MONGO_URI no configurado.")
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client[MONGO_DB_NAME]
            collection = db[MONGO_COLLECTION]
            
            filter_query = {
                "Equipo 1": match_data.get("Equipo 1"),
                "Equipo 2": match_data.get("Equipo 2"),
                "Competición": match_data.get("Competición")
            }
            
            # Upsert
            collection.update_one(filter_query, {"$set": match_data}, upsert=True)
            self._load_encuentros()
        except Exception as exc:
            raise FootballAPIError(f"Error al guardar registro en MongoDB: {exc}")
