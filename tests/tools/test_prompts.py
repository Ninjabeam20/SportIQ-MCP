"""MCP prompts register and render valid user messages.

Prompts are one-click macros surfaced in the Inspector "Prompts" tab. Each must
render to a non-empty list of ``user`` messages with non-empty text content so a
client can expand it into a usable instruction.
"""

from __future__ import annotations

import asyncio

import pytest

from sportiq import server

_EXPECTED = {
    "dream11_team_builder",
    "f1_race_strategy",
    "world_cup_winner_prediction",
    "cricket_value_bets",
    "f1_driver_comparison",
    "cricket_captain_pick",
    "predict_match",
    "build_accumulator",
    "server_health",
    "wc_group_situation",
}

# Arguments for prompts that declare required parameters.
_ARGS: dict[str, dict] = {
    "dream11_team_builder": {"team_a": "MI", "team_b": "CSK", "venue": "wankhede"},
    "f1_race_strategy": {"year": 2025, "country": "Monaco", "driver_number": 1},
    "world_cup_winner_prediction": {},
    "cricket_value_bets": {},
    "f1_driver_comparison": {
        "year": 2025,
        "country": "Monaco",
        "driver_a": 1,
        "driver_b": 16,
    },
    "cricket_captain_pick": {},
    "predict_match": {"home_team": "ARG", "away_team": "FRA"},
    "build_accumulator": {},
    "server_health": {},
    "wc_group_situation": {},
}

_PROMPTS = asyncio.run(server.mcp.list_prompts())


def test_all_expected_prompts_registered():
    names = {p.name for p in _PROMPTS}
    assert names >= _EXPECTED


@pytest.mark.parametrize("name", sorted(_EXPECTED))
async def test_prompt_renders_nonempty_user_message(name):
    result = await server.mcp.get_prompt(name, _ARGS[name])
    assert result.messages, f"{name} rendered no messages"
    first = result.messages[0]
    assert first.role == "user"
    assert first.content.text.strip()


async def test_prompt_rejects_blank_string_arg():
    with pytest.raises(Exception):  # noqa: B017 — FastMCP wraps the ValueError
        await server.mcp.get_prompt(
            "predict_match", {"home_team": "  ", "away_team": "FRA"}
        )
