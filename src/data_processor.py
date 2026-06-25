from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from config import COMPETITION_WEIGHTS, RECENCY_DECAY, MAX_H2H_MATCHES, RANKING_QUALITY_MAX


@dataclass
class MatchRecord:
    date: datetime
    competition: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    perspective_team: str          # equipo de interés
    perspective_goals_for: int
    perspective_goals_against: int
    result: str                    # "W", "D", "L"
    weight: float = 1.0
    opponent_rank: Optional[int] = None


@dataclass
class TeamStats:
    name: str
    matches_home: list[MatchRecord] = field(default_factory=list)
    matches_away: list[MatchRecord] = field(default_factory=list)
    
    @property
    def avg_goals_scored_home(self) -> float:
        return _weighted_avg(self.matches_home, lambda m: m.home_goals)
    
    @property
    def avg_goals_conceded_home(self) -> float:
        return _weighted_avg(self.matches_home, lambda m: m.away_goals)
        
    @property
    def avg_goals_scored_away(self) -> float:
        return _weighted_avg(self.matches_away, lambda m: m.away_goals)
        
    @property
    def avg_goals_conceded_away(self) -> float:
        return _weighted_avg(self.matches_away, lambda m: m.home_goals)


@dataclass
class H2HStats:
    team_a: str
    team_b: str
    rank_a: Optional[int] = None
    rank_b: Optional[int] = None
    matches: list[MatchRecord] = field(default_factory=list)
    stats_a: Optional[TeamStats] = None
    stats_b: Optional[TeamStats] = None

    # ---- Conteos ----
    @property
    def total(self) -> int:
        return len(self.matches)

    @property
    def wins_a(self) -> int:
        return sum(1 for m in self.matches if _winner(m) == "A")

    @property
    def wins_b(self) -> int:
        return sum(1 for m in self.matches if _winner(m) == "B")

    @property
    def draws(self) -> int:
        return sum(1 for m in self.matches if _winner(m) == "D")

    # ---- Goles ponderados H2H ----
    @property
    def weighted_avg_goals_a(self) -> float:
        return _weighted_avg(self.matches, lambda m: _goals_for(m, self.team_a))

    @property
    def weighted_avg_goals_b(self) -> float:
        return _weighted_avg(self.matches, lambda m: _goals_for(m, self.team_b))

    # ---- Por competición ----
    @property
    def competitions(self) -> list[str]:
        seen: list[str] = []
        for m in self.matches:
            if m.competition not in seen:
                seen.append(m.competition)
        return seen


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _winner(m: MatchRecord) -> str:
    if m.home_goals > m.away_goals:
        return "A" if m.home_team == m.perspective_team else "B"
    if m.home_goals < m.away_goals:
        return "B" if m.away_team == m.perspective_team else "A"
    return "D"


def _goals_for(m: MatchRecord, team: str) -> int:
    if m.home_team == team:
        return m.home_goals
    return m.away_goals


def _weighted_avg(matches: list[MatchRecord], extractor) -> float:
    total_w = sum(m.weight for m in matches)
    if total_w == 0:
        return 0.0
    return sum(extractor(m) * m.weight for m in matches) / total_w


def _ranking_quality_mult(opponent_rank: Optional[int]) -> float:
    """Bonus de peso según ranking del rival: vs #1 → ×1.5, vs #100+ → ×1.0."""
    if opponent_rank is None:
        return 1.0
    quality = max(0.0, 100 - opponent_rank) / 100.0
    return 1.0 + quality * RANKING_QUALITY_MAX


# ------------------------------------------------------------------ #
# Procesador principal                                                 #
# ------------------------------------------------------------------ #

class DataProcessor:
    """
    Recibe los partidos en bruto de la API y construye el objeto H2HStats
    con pesos por recencia y competición.
    """

    def build_stats(
        self,
        team_a_name: str,
        team_b_name: str,
        team_a_id: int,
        team_b_id: int,
        raw_matches: list[dict],
        rank_a: Optional[int] = None,
        rank_b: Optional[int] = None,
    ) -> H2HStats:
        stats = H2HStats(
            team_a=team_a_name, 
            team_b=team_b_name,
            rank_a=rank_a,
            rank_b=rank_b
        )
        
        # 1. Estadísticas de equipo (Forma reciente)
        stats.stats_a = self._get_team_form(team_a_name, team_a_id, raw_matches)
        stats.stats_b = self._get_team_form(team_b_name, team_b_id, raw_matches)

        # 2. Partidos H2H
        h2h_raw = [
            m for m in raw_matches
            if self._involves_both(m, team_a_id, team_b_id)
        ]

        # Ordenar de más reciente a más antiguo
        h2h_raw.sort(key=lambda m: m.get("utcDate", ""), reverse=True)
        h2h_raw = h2h_raw[:MAX_H2H_MATCHES]

        for idx, raw in enumerate(h2h_raw):
            record = self._parse_match(raw, team_a_name, team_b_name, team_a_id)
            if record is None:
                continue
            # Recency weight
            record.weight *= (RECENCY_DECAY ** idx)
            # Competition weight
            comp_w = COMPETITION_WEIGHTS.get(
                record.competition,
                COMPETITION_WEIGHTS["default"],
            )
            record.weight *= comp_w
            # Ranking quality weight (H2H: usa el ranking promedio de ambos rivales)
            avg_rank = None
            r_home = raw.get("rankingHome")
            r_away = raw.get("rankingAway")
            if r_home is not None and r_away is not None:
                avg_rank = (r_home + r_away) / 2
            elif r_home is not None:
                avg_rank = r_home
            elif r_away is not None:
                avg_rank = r_away
            record.weight *= _ranking_quality_mult(int(avg_rank) if avg_rank is not None else None)
            stats.matches.append(record)

        return stats

    def _get_team_form(self, name: str, team_id: int, raw_matches: list[dict]) -> TeamStats:
        ts = TeamStats(name=name)
        
        team_matches = [
            m for m in raw_matches
            if m.get("homeTeam", {}).get("id") == team_id or m.get("awayTeam", {}).get("id") == team_id
        ]
        
        # Ordenar por fecha
        team_matches.sort(key=lambda m: m.get("utcDate", ""), reverse=True)
        
        for idx, raw in enumerate(team_matches):
            record = self._parse_match(raw, name, "Opponent", team_id)
            if record is None:
                continue

            # Recency weight
            record.weight *= (RECENCY_DECAY ** idx)
            # Competition weight
            comp_w = COMPETITION_WEIGHTS.get(record.competition, COMPETITION_WEIGHTS["default"])
            record.weight *= comp_w
            # Ranking quality weight (usa el ranking del rival, ya extraído en _parse_match)
            record.weight *= _ranking_quality_mult(record.opponent_rank)

            if raw.get("homeTeam", {}).get("id") == team_id:
                ts.matches_home.append(record)
            else:
                ts.matches_away.append(record)
                
        return ts

    def _involves_both(self, match: dict, id_a: int, id_b: int) -> bool:
        home_id = match.get("homeTeam", {}).get("id")
        away_id = match.get("awayTeam", {}).get("id")
        return {home_id, away_id} == {id_a, id_b}

    def _parse_match(
        self,
        raw: dict,
        team_a_name: str,
        team_b_name: str,
        team_a_id: int,
    ) -> Optional[MatchRecord]:
        score = raw.get("score", {})
        ft = score.get("fullTime", {})
        home_goals = ft.get("home")
        away_goals = ft.get("away")

        if home_goals is None or away_goals is None:
            return None

        home_team = raw.get("homeTeam", {}).get("name", "")
        away_team = raw.get("awayTeam", {}).get("name", "")
        competition = raw.get("competition", {}).get("name", "Unknown")

        date_str = raw.get("utcDate", "1970-01-01T00:00:00Z")
        try:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            date = datetime(1970, 1, 1)

        home_id = raw.get("homeTeam", {}).get("id")
        is_a_home = home_id == team_a_id
        perspective = team_a_name if is_a_home else team_b_name

        if is_a_home:
            goals_for = home_goals
            goals_against = away_goals
            opponent_rank = raw.get("rankingAway")
        else:
            goals_for = away_goals
            goals_against = home_goals
            opponent_rank = raw.get("rankingHome")

        if goals_for > goals_against:
            result = "W"
        elif goals_for < goals_against:
            result = "L"
        else:
            result = "D"

        return MatchRecord(
            date=date,
            competition=competition,
            home_team=home_team,
            away_team=away_team,
            home_goals=home_goals,
            away_goals=away_goals,
            perspective_team=perspective,
            perspective_goals_for=goals_for,
            perspective_goals_against=goals_against,
            result=result,
            weight=1.0,
            opponent_rank=opponent_rank,
        )
