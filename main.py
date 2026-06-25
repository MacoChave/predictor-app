"""
Predictor de resultados de fútbol.

Uso:
    python main.py

Se pedirá el nombre de los dos equipos de forma interactiva.
Requiere una API key gratuita de https://www.football-data.org/client/register
configurada en un archivo .env (ver .env.example).
"""
from __future__ import annotations
import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.api_client import FootballAPIClient, FootballAPIError
from src.data_processor import DataProcessor
from src.predictor import FootballPredictor
from src import display

console = Console()
client = FootballAPIClient()
processor = DataProcessor()
predictor = FootballPredictor()


# ------------------------------------------------------------------ #
# Selección interactiva de equipo                                     #
# ------------------------------------------------------------------ #

def choose_team(label: str) -> dict:
    """Busca y devuelve el equipo elegido por el usuario."""
    while True:
        query = Prompt.ask(f"\n[bold cyan]Buscar {label}[/bold cyan]").strip()
        if not query:
            continue

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(f"Buscando '{query}'…", total=None)
            try:
                teams = client.search_teams(query)
            except FootballAPIError as exc:
                console.print(f"[red]Error al buscar:[/red] {exc}")
                continue

        display.print_team_results(teams, query)

        if not teams:
            retry = Confirm.ask("¿Buscar de nuevo?", default=True)
            if not retry:
                sys.exit(0)
            continue

        if len(teams) == 1:
            chosen = teams[0]
            console.print(f"[green]Equipo seleccionado:[/green] [bold]{chosen['name']}[/bold]")
            return chosen

        idx_str = Prompt.ask(
            "Elige el número del equipo [dim](0 = buscar de nuevo)[/dim]",
            default="1",
        )
        try:
            idx = int(idx_str)
        except ValueError:
            continue

        if idx == 0:
            continue
        if 1 <= idx <= len(teams):
            chosen = teams[idx - 1]
            console.print(f"[green]Equipo seleccionado:[/green] [bold]{chosen['name']}[/bold]")
            return chosen


# ------------------------------------------------------------------ #
# Flujo principal                                                      #
# ------------------------------------------------------------------ #

def main() -> None:
    display.print_header()

    # 1. Seleccionar equipos
    team_a = choose_team("Equipo A (local)")
    team_b = choose_team("Equipo B (visitante)")

    if team_a["id"] == team_b["id"]:
        console.print("[red]Los dos equipos son el mismo. Inténtalo de nuevo.[/red]")
        sys.exit(1)

    # 2. Filtro de competición (opcional) - REMOVIDO según solicitud
    comp_filter: str | None = None
    # if Confirm.ask("\n¿Filtrar por competición específica?", default=False):
    #     comp_filter = Prompt.ask("Nombre (o parte del nombre) de la competición").strip() or None

    # 3. ¿Quién juega en casa? - AUTOMATIZADO según solicitud
    hosts = ["Canadá", "Estados Unidos", "México"]
    team_a_is_home = True
    
    if team_a["name"] in hosts:
        team_a_is_home = True
        console.print(f"\n[dim][bold]{team_a['name']}[/bold] es anfitrión y juega como [bold]local[/bold].[/dim]")
    elif team_b["name"] in hosts:
        team_a_is_home = False
        console.print(f"\n[dim][bold]{team_b['name']}[/bold] es anfitrión y juega como [bold]local[/bold].[/dim]")
    else:
        # Si ninguno es anfitrión (caso raro en este contexto), se asume Team A por defecto
        team_a_is_home = True
        console.print(f"\n[dim]Se asume que [bold]{team_a['name']}[/bold] juega como local.[/dim]")

    # 4. Obtener partidos históricos
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task_a = progress.add_task(
            f"Obteniendo historial de {team_a['name']}…", total=None
        )
        try:
            matches_a = client.get_team_matches(team_a["id"])
        except FootballAPIError as exc:
            console.print(f"[red]Error al obtener partidos de {team_a['name']}:[/red] {exc}")
            sys.exit(1)
            
        task_b = progress.add_task(
            f"Obteniendo historial de {team_b['name']}…", total=None
        )
        try:
            matches_b = client.get_team_matches(team_b["id"])
        except FootballAPIError as exc:
            console.print(f"[red]Error al obtener partidos de {team_b['name']}:[/red] {exc}")
            sys.exit(1)

    all_matches = matches_a + [m for m in matches_b if m not in matches_a]

    # 5. Construir estadísticas (H2H + Forma reciente)
    stats = processor.build_stats(
        team_a_name=team_a["name"],
        team_b_name=team_b["name"],
        team_a_id=team_a["id"],
        team_b_id=team_b["id"],
        raw_matches=all_matches,
        rank_a=team_a.get("ranking"),
        rank_b=team_b.get("ranking"),
    )

    # 6. Mostrar historial
    display.print_h2h_summary(stats)

    if stats.total == 0:
        console.print(
            "\n[yellow]No hay encuentros directos registrados en el historial disponible.\n"
            "La predicción se basará en valores por defecto.[/yellow]"
        )

    # 7. Predecir
    prediction = predictor.predict(stats, team_a_is_home=team_a_is_home)
    display.print_prediction(prediction, team_a_is_home)

    # 8. ¿Otra predicción?
    if Confirm.ask("¿Realizar otra predicción?", default=False):
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Saliendo…[/dim]")
        sys.exit(0)
