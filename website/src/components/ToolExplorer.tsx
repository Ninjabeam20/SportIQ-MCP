"use client";

import { useState } from "react";
import { ChevronDown, Star } from "lucide-react";

type Tool = {
  name: string;
  type: "Free" | "Pro";
  isFlagship?: boolean;
};

const FOOTBALL_TOOLS: Tool[] = [
  { name: "football_get_groups", type: "Free" },
  { name: "football_get_fixtures", type: "Free" },
  { name: "football_get_standings", type: "Free" },
  { name: "football_get_squad", type: "Free" },
  { name: "football_get_match_stats", type: "Free" },
  { name: "football_get_top_scorers", type: "Free" },
  { name: "football_get_odds", type: "Free" },
  { name: "football_xg_model", type: "Pro" },
  { name: "football_match_predictor", type: "Pro" },
  { name: "football_simulate_group", type: "Pro" },
  { name: "football_simulate_bracket", type: "Pro", isFlagship: true },
  { name: "football_knockout_path", type: "Pro" },
  { name: "football_form_trends", type: "Pro" },
  { name: "football_find_value_bets", type: "Pro" },
  { name: "football_build_accumulator", type: "Pro" },
];

const F1_TOOLS: Tool[] = [
  { name: "f1_get_sessions", type: "Free" },
  { name: "f1_get_drivers", type: "Free" },
  { name: "f1_get_lap_times", type: "Free" },
  { name: "f1_get_standings", type: "Free" },
  { name: "f1_get_race_results", type: "Free" },
  { name: "f1_get_weather", type: "Free" },
  { name: "f1_tyre_degradation", type: "Pro" },
  { name: "f1_undercut_window", type: "Pro" },
  { name: "f1_head_to_head_pace", type: "Pro" },
  { name: "f1_weather_strategy_impact", type: "Pro" },
  { name: "f1_qualifying_analysis", type: "Pro" },
  { name: "f1_race_pace_compare", type: "Pro" },
  { name: "f1_predict_pit_strategy", type: "Pro", isFlagship: true },
];

const CRICKET_TOOLS: Tool[] = [
  { name: "cricket_get_live_matches", type: "Free" },
  { name: "cricket_get_scorecard", type: "Free" },
  { name: "cricket_get_points_table", type: "Free" },
  { name: "cricket_get_schedule", type: "Free" },
  { name: "cricket_get_squad", type: "Free" },
  { name: "cricket_get_live_odds", type: "Free" },
  { name: "cricket_build_dream11_team", type: "Pro", isFlagship: true },
  { name: "cricket_captain_recommendation", type: "Pro" },
  { name: "cricket_differential_picks", type: "Pro" },
  { name: "cricket_player_form_index", type: "Pro" },
  { name: "cricket_get_pitch_report", type: "Pro" },
  { name: "cricket_head_to_head", type: "Pro" },
  { name: "cricket_find_value_bets", type: "Pro" },
  { name: "cricket_player_matchup", type: "Pro" },
];

export default function ToolExplorer() {
  const [activeTab, setActiveTab] = useState<"football" | "f1" | "cricket">("football");

  const tools = {
    football: FOOTBALL_TOOLS,
    f1: F1_TOOLS,
    cricket: CRICKET_TOOLS,
  }[activeTab];

  return (
    <section className="py-24">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-4">
            44 Tools. Zero Configuration.
          </h2>
          <p className="text-white/70 max-w-xl mx-auto">
            A complete arsenal of data retrieval and intelligent modeling tools, exposed natively to your AI.
          </p>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-white/10 bg-black/20 overflow-x-auto hide-scrollbar">
            <button
              onClick={() => setActiveTab("football")}
              className={`flex-1 py-4 px-6 font-inter font-medium whitespace-nowrap transition-colors ${
                activeTab === "football" ? "text-sport-football bg-white/5 border-b-2 border-b-sport-football" : "text-white/60 hover:text-white hover:bg-white/5"
              }`}
            >
              ⚽ Football (15)
            </button>
            <button
              onClick={() => setActiveTab("f1")}
              className={`flex-1 py-4 px-6 font-inter font-medium whitespace-nowrap transition-colors ${
                activeTab === "f1" ? "text-sport-f1 bg-white/5 border-b-2 border-b-sport-f1" : "text-white/60 hover:text-white hover:bg-white/5"
              }`}
            >
              🏎️ F1 (13)
            </button>
            <button
              onClick={() => setActiveTab("cricket")}
              className={`flex-1 py-4 px-6 font-inter font-medium whitespace-nowrap transition-colors ${
                activeTab === "cricket" ? "text-sport-cricket bg-white/5 border-b-2 border-b-sport-cricket" : "text-white/60 hover:text-white hover:bg-white/5"
              }`}
            >
              🏏 Cricket (14)
            </button>
          </div>

          {/* Tools List */}
          <div className="p-2 sm:p-6 h-[400px] overflow-y-auto custom-scrollbar">
            <div className="grid gap-2">
              {tools.map((tool) => (
                <div
                  key={tool.name}
                  className="flex items-center justify-between p-4 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5"
                >
                  <div className="flex items-center gap-3">
                    {tool.isFlagship && <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />}
                    <span className="font-mono text-sm text-white/90">{tool.name}</span>
                  </div>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                      tool.type === "Free"
                        ? "bg-white/10 text-white/80"
                        : "bg-action-blue/20 text-action-blue border border-action-blue/30"
                    }`}
                  >
                    {tool.type}
                  </span>
                </div>
              ))}
            </div>
            
            <div className="mt-6 pt-6 border-t border-white/10 text-center text-sm text-white/50">
              + cross-sport accumulator & health diagnostics (44 tools total)
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
