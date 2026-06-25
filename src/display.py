from __future__ import annotations
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.rule import Rule
from rich import box
from src.data_processor import H2HStats, _winner
from src.predictor import Prediction

console = Console()


def print_header() -> None:
    console.print()
    console.print(Panel.fit(
        "[bold cyan]PREDICTOR DE FÚTBOL[/bold cyan]\n"
        "[dim]Modelo de Poisson con historial H2H ponderado por competición[/dim]",
        border_style="cyan",
    ))
    console.print()


def print_team_results(teams: list[dict], query: str) -> None:
    if not teams:
        console.print(f"[yellow]No se encontraron equipos para '[bold]{query}[/bold]'.[/yellow]")
        return
    table = Table(title=f"Resultados para '{query}'", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Equipo", style="bold white")
    table.add_column("País / Área", style="cyan")
    table.add_column("ID", style="dim")
    for i, t in enumerate(teams, 1):
        area = t.get("area", {}).get("name", "—")
        table.add_row(str(i), t.get("name", "?"), area, str(t.get("id", "?")))
    console.print(table)


def print_h2h_summary(stats: H2HStats) -> None:
    console.print()
    console.print(Rule(f"[bold]Historial {stats.team_a}  vs  {stats.team_b}[/bold]", style="cyan"))
    console.print()

    if not stats.matches and stats.rank_a is None:
        console.print("[yellow]No se encontraron partidos entre estos equipos en el historial disponible.[/yellow]")
        return

    # Panel de resumen global
    total = stats.total
    wins_a = stats.wins_a
    wins_b = stats.wins_b
    draws = stats.draws

    bar_a = _pct_bar(wins_a, total, "[green]")
    bar_b = _pct_bar(wins_b, total, "[red]")
    bar_d = _pct_bar(draws, total, "[yellow]")

    summary = (
        f"[bold]{stats.team_a}[/bold] [dim](Rank: {stats.rank_a or '?'})[/dim]  [green]{wins_a}V[/green] · "
        f"[yellow]{draws}E[/yellow] · "
        f"[red]{wins_b}D[/red]  [bold]{stats.team_b}[/bold] [dim](Rank: {stats.rank_b or '?'})[/dim]\n\n"
        f"[dim]Partidos analizados:[/dim] [bold]{total}[/bold]   "
        f"[dim]Competiciones:[/dim] {len(stats.competitions)}\n\n"
        f"{bar_a} Victorias {stats.team_a}\n"
        f"{bar_d} Empates\n"
        f"{bar_b} Victorias {stats.team_b}"
    )
    console.print(Panel(summary, title="Resumen H2H", border_style="blue", expand=False))
    console.print()

    if not stats.matches:
        return

    # Tabla de partidos
    table = Table(box=box.SIMPLE_HEAVY, show_lines=False, expand=True)
    table.add_column("Fecha", style="dim", width=12)
    table.add_column("Competición", style="cyan", min_width=20)
    table.add_column(stats.team_a, justify="right", style="bold white", min_width=14)
    table.add_column("Resultado", justify="center", width=9)
    table.add_column(stats.team_b, justify="left", style="bold white", min_width=14)

    for m in stats.matches:
        winner = _winner(m)
        if winner == "A":
            score_style = "[bold green]"
        elif winner == "B":
            score_style = "[bold red]"
        else:
            score_style = "[bold yellow]"

        home_goals_str = str(m.home_goals)
        away_goals_str = str(m.away_goals)

        if m.home_team == stats.team_a:
            goals_a, goals_b = home_goals_str, away_goals_str
        else:
            goals_a, goals_b = away_goals_str, home_goals_str

        result_text = f"{score_style}{goals_a} - {goals_b}[/]"
        date_str = m.date.strftime("%d/%m/%Y")

        table.add_row(date_str, m.competition, m.home_team if m.home_team == stats.team_a else m.away_team,
                      result_text,
                      m.away_team if m.home_team == stats.team_a else m.home_team)

    console.print(table)


def print_prediction(pred: Prediction, team_a_is_home: bool) -> None:
    console.print()
    console.print(Rule("[bold magenta]PREDICCIÓN[/bold magenta]", style="magenta"))
    console.print()

    home_label = "[dim](Local)[/dim]" if team_a_is_home else "[dim](Visitante)[/dim]"
    away_label = "[dim](Visitante)[/dim]" if team_a_is_home else "[dim](Local)[/dim]"

    # Probabilidades con barras visuales
    p_a = pred.prob_win_a
    p_d = pred.prob_draw
    p_b = pred.prob_win_b

    bar_width = 30
    bar_a = _visual_bar(p_a, bar_width, "green")
    bar_d = _visual_bar(p_d, bar_width, "yellow")
    bar_b = _visual_bar(p_b, bar_width, "red")

    prob_text = (
        f"[bold green]{pred.team_a}[/bold green] {home_label}\n"
        f"  {bar_a} [bold green]{p_a * 100:.1f}%[/bold green]\n\n"
        f"[bold yellow]Empate[/bold yellow]\n"
        f"  {bar_d} [bold yellow]{p_d * 100:.1f}%[/bold yellow]\n\n"
        f"[bold red]{pred.team_b}[/bold red] {away_label}\n"
        f"  {bar_b} [bold red]{p_b * 100:.1f}%[/bold red]"
    )
    console.print(Panel(prob_text, title="Probabilidades", border_style="magenta", expand=False))

    # Marcador más probable y goles esperados
    g_a, g_b = pred.most_likely_score
    score_panel = (
        f"[dim]Resultado más probable:[/dim]  "
        f"[bold cyan]{pred.team_a} {g_a} – {g_b} {pred.team_b}[/bold cyan]\n\n"
        f"[dim]Goles esperados:[/dim]  "
        f"[green]{pred.team_a}[/green] {pred.expected_goals_a:.2f}  ·  "
        f"[red]{pred.team_b}[/red] {pred.expected_goals_b:.2f}\n\n"
        f"[dim]Veredicto:[/dim]  [bold white]{pred.outcome_label}[/bold white]\n\n"
        f"[dim]Confianza del modelo:[/dim]  "
        f"{_confidence_color(pred.confidence)}{pred.confidence}[/]  "
        f"[dim]({pred.matches_used} partidos H2H)[/dim]"
    )
    console.print(Panel(score_panel, title="Análisis", border_style="cyan", expand=False))

    # Top 5 marcadores
    console.print()
    top_table = Table(title="Top 5 marcadores más probables", box=box.ROUNDED)
    top_table.add_column("Marcador", justify="center", style="bold white")
    top_table.add_column("Probabilidad", justify="right")
    top_table.add_column("", min_width=20)
    for g_a2, g_b2, prob in pred.top_scores:
        bar = _visual_bar(prob, 20, "blue")
        top_table.add_row(
            f"{pred.team_a} {g_a2} – {g_b2} {pred.team_b}",
            f"{prob * 100:.2f}%",
            bar,
        )
    console.print(top_table)
    console.print()


# ------------------------------------------------------------------ #
# Helpers internos                                                     #
# ------------------------------------------------------------------ #

def _pct_bar(value: int, total: int, color: str) -> str:
    if total == 0:
        return f"{color}{'░' * 10}[/]  0.0%"
    pct = value / total
    filled = round(pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{color}{bar}[/]  {pct * 100:.1f}%"


def _visual_bar(prob: float, width: int, color: str) -> str:
    filled = round(prob * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{color}]{bar}[/{color}]"


def _confidence_color(level: str) -> str:
    colors = {"Alta": "[bold green]", "Media": "[bold yellow]", "Baja": "[bold red]"}
    return colors.get(level, "[white]")
