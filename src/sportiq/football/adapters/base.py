"""Shared constants for football adapters.

Every adapter in a given chain returns the SAME output shape (the lesson from
F1 audit finding #2): fixtures -> {"fixtures": [...]}, standings ->
{"standings": [...]}, squad -> {"squad": [...]}, team_stats ->
{"team_stats": {...}}, scorers -> {"scorers": [...]}.
"""
_APIFOOTBALL_BASE = "https://v3.football.api-sports.io"
_FOOTBALLDATA_BASE = "https://api.football-data.org/v4"

# API-Football: FIFA World Cup league id + 2026 edition.
_WC_LEAGUE_ID = 1
_WC_SEASON = 2026
# football-data.org competition code for the World Cup.
_FD_COMPETITION = "WC"
