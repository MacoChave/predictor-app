import json
import time
import hashlib
import requests
from pathlib import Path
from typing import Optional
from config import API_KEY, BASE_URL, CACHE_DIR, FETCH_LIMIT


class FootballAPIError(Exception):
    pass


class FootballAPIClient:
    """Cliente para la API de football-data.org (v4)."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": API_KEY,
            "Accept": "application/json",
        })
        self._last_request_time = 0.0
        self._min_interval = 6.5  # Free tier: 10 req/min → ~6s entre llamadas

    # ------------------------------------------------------------------ #
    # Internos                                                             #
    # ------------------------------------------------------------------ #

    def _cache_path(self, key: str) -> Path:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return CACHE_DIR / f"{hashed}.json"

    def _load_cache(self, key: str) -> Optional[dict]:
        path = self._cache_path(key)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _save_cache(self, key: str, data: dict) -> None:
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, endpoint: str, params: Optional[dict] = None, use_cache: bool = True) -> dict:
        cache_key = f"{endpoint}?{json.dumps(params or {}, sort_keys=True)}"

        if use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        if not API_KEY:
            raise FootballAPIError(
                "No se encontró FOOTBALL_DATA_API_KEY.\n"
                "Copia .env.example a .env y añade tu clave gratuita de "
                "https://www.football-data.org/client/register"
            )

        self._throttle()
        url = f"{BASE_URL}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            raise FootballAPIError(f"Error de red: {exc}") from exc

        if resp.status_code == 429:
            wait = int(resp.headers.get("X-RequestCounter-Reset", 60))
            time.sleep(wait)
            return self._get(endpoint, params, use_cache)

        if resp.status_code == 400:
            raise FootballAPIError(f"Solicitud inválida ({endpoint}): {resp.text[:200]}")
        if resp.status_code == 403:
            raise FootballAPIError("API key inválida o plan insuficiente.")
        if resp.status_code == 404:
            raise FootballAPIError(f"Recurso no encontrado: {endpoint}")
        if not resp.ok:
            raise FootballAPIError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if use_cache:
            self._save_cache(cache_key, data)
        return data

    # ------------------------------------------------------------------ #
    # Métodos públicos                                                     #
    # ------------------------------------------------------------------ #

    def search_teams(self, name: str) -> list[dict]:
        """Busca equipos por nombre. Retorna lista de dicts con id/name/area."""
        data = self._get("/teams", {"name": name, "limit": 10})
        return data.get("teams", [])

    def get_team(self, team_id: int) -> dict:
        return self._get(f"/teams/{team_id}")

    def get_team_matches(self, team_id: int, status: str = "FINISHED") -> list[dict]:
        """
        Devuelve hasta FETCH_LIMIT partidos acabados del equipo.
        Incluye competición, marcador y rivales.
        """
        data = self._get(
            f"/teams/{team_id}/matches",
            {"status": status, "limit": FETCH_LIMIT},
        )
        return data.get("matches", [])

    def clear_cache(self) -> None:
        for f in CACHE_DIR.glob("*.json"):
            f.unlink(missing_ok=True)
