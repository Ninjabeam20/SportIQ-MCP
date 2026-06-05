"""Registers MCP prompts — one-click macros surfaced in the Inspector "Prompts" tab.

Each prompt returns a single ``user`` message that names the exact tool call
sequence for a common intent, mirroring the minimum-call recipes in
``instructions.md``. The AI client expands the prompt, then issues the calls.

The 10 prompts map 1:1 to the 10 minimum-call recipes in ``instructions.md``.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def _clean(value: str, name: str) -> str:
    """Strip a string prompt arg and reject blanks with a clear error.

    Prompt content is natural language read by the model, not shell/SQL, so no
    escaping is needed — but an empty arg would produce a malformed instruction,
    so surface it as a ValueError the Inspector can display.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{name} must not be empty")
    return cleaned


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        title="Dream11 Team Builder",
        description="Build an optimal Dream11 XI for an IPL match.",
    )
    def dream11_team_builder(team_a: str, team_b: str, venue: str) -> list[dict]:
        """Build an optimal Dream11 XI for an IPL match.

        Args:
            team_a: First team code or name (e.g. "MI", "CSK").
            team_b: Second team code or name (e.g. "MI", "CSK").
            venue: Venue key or name (e.g. "wankhede").
        """
        team_a = _clean(team_a, "team_a")
        team_b = _clean(team_b, "team_b")
        venue = _clean(venue, "venue")
        return [
            {
                "role": "user",
                "content": (
                    f"Build the optimal Dream11 XI for {team_a} vs {team_b} at "
                    f"{venue}. Call cricket_build_dream11_team("
                    f'team_a="{team_a}", team_b="{team_b}", venue="{venue}") '
                    "— one call. Report the 11 players, captain, vice-captain, "
                    "and total credits used."
                ),
            }
        ]

    @mcp.prompt(
        title="F1 Pit Strategy",
        description="Predict pit strategy for a driver at a specific Grand Prix.",
    )
    def f1_race_strategy(year: int, country: str, driver_number: int) -> list[dict]:
        """Predict pit strategy for a driver at a specific Grand Prix.

        Args:
            year: Season year (e.g. 2025).
            country: Grand Prix host country (e.g. "Monaco").
            driver_number: Driver's car number (e.g. 1 for Verstappen).
        """
        country = _clean(country, "country")
        return [
            {
                "role": "user",
                "content": (
                    f"Predict the optimal pit strategy for driver number "
                    f"{driver_number} at the {year} {country} Grand Prix. First "
                    f'call f1_get_sessions(year={year}, country="{country}") and '
                    "pick the race session_key, then call "
                    f"f1_predict_pit_strategy(session_key=<key>, "
                    f"driver_number={driver_number}). Report the stop laps and "
                    "compound sequence."
                ),
            }
        ]

    @mcp.prompt(
        title="World Cup Winner Prediction",
        description="Simulate the FIFA World Cup 2026 and predict the winner.",
    )
    def world_cup_winner_prediction() -> list[dict]:
        """Simulate the FIFA World Cup 2026 and predict the winner."""
        return [
            {
                "role": "user",
                "content": (
                    "Predict the FIFA World Cup 2026 winner. Call "
                    "football_simulate_bracket() — one call, default 10,000 "
                    "iterations (±2% stable). Report the top teams by title "
                    "probability."
                ),
            }
        ]

    @mcp.prompt(
        title="Cricket Value Bets",
        description="Find today's value bets across IPL matches.",
    )
    def cricket_value_bets() -> list[dict]:
        """Find today's value bets across IPL matches."""
        return [
            {
                "role": "user",
                "content": (
                    "Find today's value bets across IPL matches. Call "
                    "cricket_find_value_bets() — one call. Report each match with "
                    "edge > 0 and the model vs market probabilities. (Requires "
                    "THEODDS_KEY; if unset the tool returns a clear error.)"
                ),
            }
        ]

    @mcp.prompt(
        title="F1 Driver Comparison",
        description="Compare two F1 drivers' pace at a Grand Prix.",
    )
    def f1_driver_comparison(
        year: int, country: str, driver_a: int, driver_b: int
    ) -> list[dict]:
        """Compare two F1 drivers' pace at a Grand Prix.

        Args:
            year: Season year (e.g. 2025).
            country: Grand Prix host country (e.g. "Monaco").
            driver_a: First driver's car number.
            driver_b: Second driver's car number.
        """
        country = _clean(country, "country")
        return [
            {
                "role": "user",
                "content": (
                    f"Compare the race pace of drivers {driver_a} and {driver_b} "
                    f"at the {year} {country} Grand Prix. First call "
                    f'f1_get_sessions(year={year}, country="{country}") and pick '
                    "the session_key, then call f1_head_to_head_pace("
                    f"session_key=<key>, driver_a={driver_a}, "
                    f"driver_b={driver_b}). Report who is faster and by how much."
                ),
            }
        ]

    @mcp.prompt(
        title="IPL Captain Pick",
        description="Recommend a captain for tonight's live IPL match.",
    )
    def cricket_captain_pick() -> list[dict]:
        """Recommend a captain for tonight's live IPL match."""
        return [
            {
                "role": "user",
                "content": (
                    "Recommend a captain for tonight's IPL match. First call "
                    "cricket_get_live_matches() and pick the relevant match_id, "
                    "then call cricket_captain_recommendation(match_id=<id>) — "
                    "two calls. Report the top-3 captain candidates by projected "
                    "points."
                ),
            }
        ]

    @mcp.prompt(
        title="Predict a Match",
        description="Predict the scoreline and outcome of one World Cup 2026 match.",
    )
    def predict_match(home_team: str, away_team: str) -> list[dict]:
        """Predict the scoreline and outcome of one World Cup 2026 match.

        Args:
            home_team: Home team code (e.g. "ARG").
            away_team: Away team code (e.g. "FRA").
        """
        home_team = _clean(home_team, "home_team")
        away_team = _clean(away_team, "away_team")
        return [
            {
                "role": "user",
                "content": (
                    f"Predict {home_team} vs {away_team}. Call "
                    f'football_match_predictor(home_team="{home_team}", '
                    f'away_team="{away_team}") — one call. Report the most likely '
                    "scoreline plus win/draw/loss probabilities."
                ),
            }
        ]

    @mcp.prompt(
        title="Build an Accumulator",
        description="Build a cross-sport accumulator from the top value bets.",
    )
    def build_accumulator(legs: int = 3) -> list[dict]:
        """Build a cross-sport accumulator from the top value bets.

        Args:
            legs: Number of legs (selections) in the accumulator. Default 3.
        """
        return [
            {
                "role": "user",
                "content": (
                    f"Build a {legs}-leg accumulator across cricket and football. "
                    f"Call cross_sport_build_accumulator(legs={legs}) — one call. "
                    "Report the selected legs, each edge, and the combined odds."
                ),
            }
        ]

    @mcp.prompt(
        title="Server Health",
        description="Report cache backend, adapter status, and remaining API quota.",
    )
    def server_health() -> list[dict]:
        """Report cache backend, adapter status, and remaining API quota."""
        return [
            {
                "role": "user",
                "content": (
                    "Check the SportIQ server health. Call sportiq_health() — one "
                    "call. Report the cache backend, per-adapter status, and "
                    "remaining per-source API quota."
                ),
            }
        ]

    @mcp.prompt(
        title="World Cup Group Situation",
        description="Show the World Cup 2026 group draw and advancement format.",
    )
    def wc_group_situation() -> list[dict]:
        """Show the World Cup 2026 group draw and advancement format."""
        return [
            {
                "role": "user",
                "content": (
                    "Show the World Cup 2026 group-stage situation. Call "
                    "football_get_groups() for the 12-group draw and advancement "
                    "format — one call. Add football_get_standings() only if the "
                    "user wants live standings."
                ),
            }
        ]
