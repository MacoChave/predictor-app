from __future__ import annotations
import math
from dataclasses import dataclass
from scipy.stats import poisson
import numpy as np
from src.data_processor import H2HStats

MAX_GOALS = 8   # Máximo de goles a considerar en la matriz de Poisson


@dataclass
class Prediction:
    team_a: str
    team_b: str
    prob_win_a: float
    prob_draw: float
    prob_win_b: float
    expected_goals_a: float
    expected_goals_b: float
    most_likely_score: tuple[int, int]   # (goles_a, goles_b)
    score_matrix: np.ndarray             # prob[i][j] = P(A marca i, B marca j)
    matches_used: int
    confidence: str                      # "Alta", "Media", "Baja"

    @property
    def outcome_label(self) -> str:
        probs = {
            f"Victoria {self.team_a}": self.prob_win_a,
            "Empate":                  self.prob_draw,
            f"Victoria {self.team_b}": self.prob_win_b,
        }
        return max(probs, key=probs.get)

    @property
    def top_scores(self) -> list[tuple[int, int, float]]:
        """Los 5 resultados más probables: (goles_a, goles_b, probabilidad)."""
        flat = [
            (i, j, float(self.score_matrix[i, j]))
            for i in range(MAX_GOALS + 1)
            for j in range(MAX_GOALS + 1)
        ]
        flat.sort(key=lambda x: x[2], reverse=True)
        return flat[:5]


class FootballPredictor:
    """
    Modelo de Poisson bivariado para predicción de partidos de fútbol.
    """

    HOME_ADVANTAGE = 0.10   # +10 % a los goles esperados del equipo local
    RANKING_FACTOR = 0.006  # Ajuste por cada puesto de diferencia en el ranking FIFA

    def predict(self, stats: H2HStats, team_a_is_home: bool = True) -> Prediction:
        # 1. Base: Promedios generales de goles (Forma reciente)
        if team_a_is_home:
            # A es local, B es visitante
            base_a = (stats.stats_a.avg_goals_scored_home + stats.stats_b.avg_goals_conceded_away) / 2
            base_b = (stats.stats_b.avg_goals_scored_away + stats.stats_a.avg_goals_conceded_home) / 2
        else:
            # A es visitante, B es local
            base_a = (stats.stats_a.avg_goals_scored_away + stats.stats_b.avg_goals_conceded_home) / 2
            base_b = (stats.stats_b.avg_goals_scored_home + stats.stats_a.avg_goals_conceded_away) / 2

        # Si no hay datos suficientes de local/visita, usar promedios combinados
        if base_a == 0: base_a = 1.3
        if base_b == 0: base_b = 1.1

        lambda_a = base_a
        lambda_b = base_b

        # 2. Ajuste por historial H2H (si existe)
        if stats.total > 0:
            h2h_a = stats.weighted_avg_goals_a
            h2h_b = stats.weighted_avg_goals_b
            # Ponderamos la base (forma) con el historial H2H (70% forma, 30% H2H)
            lambda_a = (lambda_a * 0.7) + (h2h_a * 0.3)
            lambda_b = (lambda_b * 0.7) + (h2h_b * 0.3)

        # 3. Ajuste por Ranking FIFA
        if stats.rank_a is not None and stats.rank_b is not None:
            rank_diff = stats.rank_b - stats.rank_a
            adjustment = rank_diff * self.RANKING_FACTOR
            lambda_a *= (1 + adjustment)
            lambda_b *= (1 - adjustment)

        # 4. Ajuste final por ventaja de local (si uno es anfitrión)
        # (Ya se tomó en cuenta en la base, pero damos un extra por el factor anfitrión de WC2026)
        if team_a_is_home:
            lambda_a *= (1 + self.HOME_ADVANTAGE)
        else:
            lambda_b *= (1 + self.HOME_ADVANTAGE)

        # Evitar lambdas de 0
        lambda_a = max(lambda_a, 0.4)
        lambda_b = max(lambda_b, 0.4)

        # Matriz de probabilidades de marcadores
        score_matrix = self._score_matrix(lambda_a, lambda_b)

        # Probabilidades de resultado
        prob_win_a = float(np.sum(np.tril(score_matrix, k=-1)))
        prob_win_b = float(np.sum(np.triu(score_matrix, k=1)))
        prob_draw = float(np.trace(score_matrix))

        idx = np.unravel_index(np.argmax(score_matrix), score_matrix.shape)
        most_likely = (int(idx[0]), int(idx[1]))

        confidence = self._calculate_confidence(stats)

        return Prediction(
            team_a=stats.team_a,
            team_b=stats.team_b,
            prob_win_a=round(prob_win_a, 4),
            prob_draw=round(prob_draw, 4),
            prob_win_b=round(prob_win_b, 4),
            expected_goals_a=round(lambda_a, 2),
            expected_goals_b=round(lambda_b, 2),
            most_likely_score=most_likely,
            score_matrix=score_matrix,
            matches_used=stats.total,
            confidence=confidence,
        )

    def _score_matrix(self, lambda_a: float, lambda_b: float) -> np.ndarray:
        dist_a = [poisson.pmf(i, lambda_a) for i in range(MAX_GOALS + 1)]
        dist_b = [poisson.pmf(j, lambda_b) for j in range(MAX_GOALS + 1)]
        matrix = np.outer(dist_a, dist_b)
        matrix /= matrix.sum()
        return matrix

    def _calculate_confidence(self, stats: H2HStats) -> str:
        n_h2h = stats.total
        n_a = len(stats.stats_a.matches_home) + len(stats.stats_a.matches_away)
        n_b = len(stats.stats_b.matches_home) + len(stats.stats_b.matches_away)
        
        total_data = n_h2h + (n_a + n_b) / 10 # El H2H pesa más para la confianza
        
        if total_data >= 5:
            return "Alta"
        if total_data >= 2:
            return "Media"
        return "Baja"
