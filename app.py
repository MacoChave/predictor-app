from flask import Flask, render_template, request
from src.api_client import FootballAPIClient, FootballAPIError
from src.data_processor import DataProcessor
from src.predictor import FootballPredictor

app = Flask(__name__)

HOSTS = ["Canadá", "Estados Unidos", "México"]

client: FootballAPIClient | None = None
processor = DataProcessor()
predictor_model = FootballPredictor()


def get_client() -> FootballAPIClient:
    global client
    if client is None:
        client = FootballAPIClient()
    return client


@app.route("/")
def index():
    try:
        c = get_client()
        teams = c.unique_teams
        return render_template("index.html", teams=teams, competitions=c.unique_competitions, rankings=c.team_rankings)
    except FootballAPIError as exc:
        return render_template("index.html", teams=[], competitions=[], rankings={}, error=str(exc))


@app.route("/predict", methods=["POST"])
def predict():
    team_a_name = request.form.get("team_a", "").strip()
    team_b_name = request.form.get("team_b", "").strip()

    try:
        c = get_client()
    except FootballAPIError as exc:
        return render_template("index.html", teams=[], competitions=[], rankings={}, error=str(exc))

    if not team_a_name or not team_b_name:
        return render_template("index.html", teams=c.unique_teams, competitions=c.unique_competitions, rankings=c.team_rankings, error="Selecciona dos equipos.")

    if team_a_name == team_b_name:
        return render_template("index.html", teams=c.unique_teams, competitions=c.unique_competitions, rankings=c.team_rankings, error="Selecciona dos equipos distintos.")

    results_a = c.search_teams(team_a_name)
    results_b = c.search_teams(team_b_name)

    if not results_a:
        return render_template("index.html", teams=c.unique_teams, competitions=c.unique_competitions, rankings=c.team_rankings, error=f"Equipo '{team_a_name}' no encontrado.")
    if not results_b:
        return render_template("index.html", teams=c.unique_teams, competitions=c.unique_competitions, rankings=c.team_rankings, error=f"Equipo '{team_b_name}' no encontrado.")

    team_a = results_a[0]
    team_b = results_b[0]

    if team_a["name"] in HOSTS:
        team_a_is_home = True
    elif team_b["name"] in HOSTS:
        team_a_is_home = False
    else:
        team_a_is_home = True

    matches_a = c.get_team_matches(team_a["id"])
    matches_b = c.get_team_matches(team_b["id"])
    all_matches = matches_a + [m for m in matches_b if m not in matches_a]

    stats = processor.build_stats(
        team_a_name=team_a["name"],
        team_b_name=team_b["name"],
        team_a_id=team_a["id"],
        team_b_id=team_b["id"],
        raw_matches=all_matches,
        rank_a=team_a.get("ranking"),
        rank_b=team_b.get("ranking"),
    )

    prediction = predictor_model.predict(stats, team_a_is_home=team_a_is_home)
    home_team = team_a["name"] if team_a_is_home else team_b["name"]

    return render_template(
        "result.html",
        prediction=prediction,
        stats=stats,
        team_a_is_home=team_a_is_home,
        home_team=home_team,
        top_scores=prediction.top_scores,
    )


@app.route("/refresh")
def refresh():
    global client
    try:
        client = FootballAPIClient()
        c = client
        return render_template("index.html", teams=c.unique_teams, competitions=c.unique_competitions, rankings=c.team_rankings, info="Datos recargados desde MongoDB.")
    except FootballAPIError as exc:
        return render_template("index.html", teams=[], competitions=[], rankings={}, error=str(exc))


@app.route("/add_match", methods=["POST"])
def add_match():
    data = request.json
    try:
        c = get_client()
        c.add_match(data)
        return {"status": "success", "message": "Registro guardado correctamente."}
    except FootballAPIError as exc:
        return {"status": "error", "message": str(exc)}, 500
    except Exception as exc:
        return {"status": "error", "message": f"Error inesperado: {exc}"}, 500


if __name__ == "__main__":
    app.run(debug=True)
