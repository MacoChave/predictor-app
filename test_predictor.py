"""Test rápido del modelo de predicción con datos mock (sin API)."""
from datetime import datetime
from src.data_processor import H2HStats, MatchRecord, TeamStats
from src.predictor import FootballPredictor


def make_record(home, away, hg, ag, comp="La Liga", days_ago=0):
    return MatchRecord(
        date=datetime(2024, 1, 1),
        competition=comp,
        home_team=home,
        away_team=away,
        home_goals=hg,
        away_goals=ag,
        perspective_team=home,
        perspective_goals_for=hg,
        perspective_goals_against=ag,
        result="W" if hg > ag else ("L" if hg < ag else "D"),
        weight=1.0,
    )


def test_basic_prediction():
    stats = H2HStats(team_a="Real Madrid", team_b="Barcelona")
    # Real Madrid gana 5 de 8, empate 2, Barcelona gana 1
    matches = [
        make_record("Real Madrid", "Barcelona", 3, 1),
        make_record("Barcelona", "Real Madrid", 0, 2),
        make_record("Real Madrid", "Barcelona", 2, 2),
        make_record("Barcelona", "Real Madrid", 1, 3),
        make_record("Real Madrid", "Barcelona", 1, 0),
        make_record("Barcelona", "Real Madrid", 2, 2),
        make_record("Real Madrid", "Barcelona", 4, 1),
        make_record("Barcelona", "Real Madrid", 1, 0),
    ]
    stats.matches = matches
    
    # Mock stats_a y stats_b
    stats.stats_a = TeamStats(name="Real Madrid")
    stats.stats_a.matches_home = [make_record("Real Madrid", "Other", 2, 0) for _ in range(5)]
    stats.stats_a.matches_away = [make_record("Other", "Real Madrid", 0, 2) for _ in range(5)]
    
    stats.stats_b = TeamStats(name="Barcelona")
    stats.stats_b.matches_home = [make_record("Barcelona", "Other", 1, 1) for _ in range(5)]
    stats.stats_b.matches_away = [make_record("Other", "Barcelona", 2, 1) for _ in range(5)]

    pred = FootballPredictor().predict(stats, team_a_is_home=True)

    assert 0 < pred.prob_win_a < 1
    assert 0 < pred.prob_draw < 1
    assert 0 < pred.prob_win_b < 1
    total = pred.prob_win_a + pred.prob_draw + pred.prob_win_b
    assert abs(total - 1.0) < 0.001, f"Probabilidades no suman 1: {total}"
    assert pred.matches_used == 8
    assert pred.confidence in ["Alta", "Media", "Baja"]

    print(f"  Real Madrid gana: {pred.prob_win_a * 100:.1f}%")
    print(f"  Empate:           {pred.prob_draw * 100:.1f}%")
    print(f"  Barcelona gana:   {pred.prob_win_b * 100:.1f}%")
    print(f"  Marcador probable: {pred.most_likely_score}")
    print(f"  Confianza: {pred.confidence}")
    print("  PASS")


def test_no_data():
    stats = H2HStats(team_a="A", team_b="B")
    stats.stats_a = TeamStats(name="A")
    stats.stats_b = TeamStats(name="B")
    pred = FootballPredictor().predict(stats)
    # Sin datos de goles, el predictor usa valores por defecto
    assert 0 < pred.prob_win_a < 1
    assert pred.matches_used == 0
    print("  No-data prediction: PASS")


if __name__ == "__main__":
    print("Ejecutando tests...")
    test_basic_prediction()
    test_no_data()
    print("Todos los tests pasaron.")
