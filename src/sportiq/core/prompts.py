"""Registers MCP prompts — one-click macros surfaced in the Inspector "Prompts" tab.

Each prompt returns a single ``user`` message that names the exact tool call
sequence for a common intent, mirroring the minimum-call recipes in
``instructions.md``. The AI client expands the prompt, then issues the calls.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt(
        title="Dream11 Team Builder",
        description="Build an optimal Dream11 XI for an IPL match.",
    )
    def dream11_team_builder(team_a: str, team_b: str, venue: str) -> list[dict]:
        """Build an optimal Dream11 XI for an IPL match."""
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
        """Predict pit strategy for a driver at a specific Grand Prix."""
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
        """Compare two F1 drivers' pace at a Grand Prix."""
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
