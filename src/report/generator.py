"""HTML Report Generator.

Produces a single self-contained HTML file with all 12 sections.
Uses Jinja2 templating with inline Tailwind CSS + Chart.js.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Template

from src.config import settings
from src.models import FinalAppRecord, InsightsSummary, OpportunityScore

logger = logging.getLogger(__name__)


def generate_html_report(
    records: list[FinalAppRecord],
    insights: InsightsSummary,
    opportunity_scores: list[OpportunityScore] | None = None,
) -> Path:
    """Generate the final self-contained HTML report."""
    output_path = settings.get_output_path(settings.html_report_file)

    # Prepare template data
    data = _prepare_template_data(records, insights, opportunity_scores)

    # Render template
    template = Template(HTML_TEMPLATE)
    html = template.render(**data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"HTML report generated: {output_path}")
    return output_path


def _prepare_template_data(
    records: list[FinalAppRecord],
    insights: InsightsSummary,
    opportunity_scores: list[OpportunityScore] | None = None,
) -> dict:
    """Prepare all data needed by the HTML template."""
    # Sort records by app_id for consistent table display
    sorted_records = sorted(records, key=lambda r: r.app_id)

    # Opportunity data
    opp_high = []
    opp_medium = []
    opp_low = []
    if opportunity_scores:
        for score in opportunity_scores:
            item = {
                "name": score.app_name,
                "category": score.category,
                "score": score.total_score,
                "rationale": score.rationale,
                "has_toolkit": score.composio_has_toolkit,
                "is_new": score.is_new_opportunity,
            }
            if score.level.value == "High":
                opp_high.append(item)
            elif score.level.value == "Medium":
                opp_medium.append(item)
            else:
                opp_low.append(item)

    # Chart data (JSON serialized for Chart.js)
    auth_labels = json.dumps(list(insights.auth_distribution.keys()))
    auth_values = json.dumps(list(insights.auth_distribution.values()))

    access_labels = json.dumps(list(insights.access_distribution.keys()))
    access_values = json.dumps(list(insights.access_distribution.values()))

    api_labels = json.dumps(list(insights.api_type_distribution.keys()))
    api_values = json.dumps(list(insights.api_type_distribution.values()))

    mcp_labels = json.dumps(list(insights.mcp_distribution.keys()))
    mcp_values = json.dumps(list(insights.mcp_distribution.values()))

    cat_labels = json.dumps(list(insights.category_distribution.keys()))
    cat_values = json.dumps(list(insights.category_distribution.values()))

    verdict_labels = json.dumps(list(insights.verdict_distribution.keys()))
    verdict_values = json.dumps(list(insights.verdict_distribution.values()))

    return {
        "records": sorted_records,
        "records_json": json.dumps(
            [r.model_dump() for r in sorted_records], default=str
        ),
        "insights": insights,
        "opp_high": opp_high,
        "opp_medium": opp_medium,
        "opp_low": opp_low,
        "auth_labels": auth_labels,
        "auth_values": auth_values,
        "access_labels": access_labels,
        "access_values": access_values,
        "api_labels": api_labels,
        "api_values": api_values,
        "mcp_labels": mcp_labels,
        "mcp_values": mcp_values,
        "cat_labels": cat_labels,
        "cat_values": cat_values,
        "verdict_labels": verdict_labels,
        "verdict_values": verdict_values,
        "total_apps": insights.total_apps,
    }


# ─── HTML Template (inline, self-contained) ──────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Composio App Research — AI Product Ops Case Study</title>
    <meta name="description" content="AI-driven research of 100 applications for Composio toolkit integration opportunities. Includes verification framework, confidence scoring, and product insights.">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'] },
                    colors: {
                        brand: { 50:'#eef2ff',100:'#e0e7ff',200:'#c7d2fe',300:'#a5b4fc',400:'#818cf8',500:'#6366f1',600:'#4f46e5',700:'#4338ca',800:'#3730a3',900:'#312e81' },
                    }
                }
            }
        }
    </script>
    <style>
        * { scrollbar-width: thin; scrollbar-color: #4f46e5 #1e1b4b; }
        body { background: #0c0a1a; }
        .glass { background: rgba(255,255,255,0.03); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.06); }
        .glass-strong { background: rgba(255,255,255,0.06); backdrop-filter: blur(30px); border: 1px solid rgba(255,255,255,0.1); }
        .glow { box-shadow: 0 0 30px rgba(99,102,241,0.15); }
        .glow-text { text-shadow: 0 0 20px rgba(99,102,241,0.5); }
        .gradient-text { background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .stat-card { transition: all 0.3s ease; }
        .stat-card:hover { transform: translateY(-4px); box-shadow: 0 8px 40px rgba(99,102,241,0.2); }
        .table-row { transition: background 0.15s; }
        .table-row:hover { background: rgba(99,102,241,0.08) !important; }
        .badge { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
        .badge-high { background: rgba(34,197,94,0.15); color: #4ade80; }
        .badge-medium { background: rgba(234,179,8,0.15); color: #facc15; }
        .badge-low { background: rgba(239,68,68,0.15); color: #f87171; }
        .badge-easy { background: rgba(34,197,94,0.15); color: #4ade80; }
        .badge-moderate { background: rgba(234,179,8,0.15); color: #facc15; }
        .badge-hard { background: rgba(249,115,22,0.15); color: #fb923c; }
        .badge-not-feasible { background: rgba(239,68,68,0.15); color: #f87171; }
        .badge-unknown { background: rgba(148,163,184,0.15); color: #94a3b8; }
        .nav-link { transition: all 0.2s; }
        .nav-link:hover { color: #818cf8; }
        .nav-link.active { color: #818cf8; border-bottom: 2px solid #818cf8; }
        @keyframes fadeIn { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.6s ease-out forwards; }
        .chart-container { position: relative; max-height: 300px; }
        #search-input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
        .pipeline-step { position: relative; padding-left: 2rem; }
        .pipeline-step::before { content: ''; position: absolute; left: 0.5rem; top: 0; bottom: 0; width: 2px; background: linear-gradient(to bottom, #6366f1, #c084fc); }
        .pipeline-step::after { content: ''; position: absolute; left: 0.25rem; top: 0.5rem; width: 0.75rem; height: 0.75rem; border-radius: 50%; background: #6366f1; border: 2px solid #0c0a1a; }
    </style>
</head>
<body class="font-sans text-gray-200 min-h-screen">

    <!-- Background effects -->
    <div class="fixed inset-0 z-0">
        <div class="absolute top-0 left-1/4 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl"></div>
        <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl"></div>
        <div class="absolute top-1/2 left-1/2 w-64 h-64 bg-pink-600/5 rounded-full blur-3xl"></div>
    </div>

    <!-- Navigation -->
    <nav class="fixed top-0 left-0 right-0 z-50 glass-strong">
        <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-gradient-to-br from-brand-500 to-purple-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">C</div>
                <span class="font-bold text-white">Composio Research</span>
            </div>
            <div class="hidden md:flex items-center gap-6 text-sm text-gray-400">
                <a href="#executive" class="nav-link">Executive</a>
                <a href="#architecture" class="nav-link">Architecture</a>
                <a href="#verification" class="nav-link">Verification</a>
                <a href="#analysis" class="nav-link">Analysis</a>
                <a href="#opportunities" class="nav-link">Opportunities</a>
                <a href="#dataset" class="nav-link">Dataset</a>
            </div>
        </div>
    </nav>

    <main class="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-20">

        <!-- Section 1: Executive Summary -->
        <section id="executive" class="mb-20 fade-in">
            <div class="text-center mb-12">
                <p class="text-brand-400 font-semibold text-sm uppercase tracking-wider mb-3">AI Product Ops Research</p>
                <h1 class="text-5xl md:text-6xl font-black text-white mb-4 glow-text">
                    <span class="gradient-text">100 Apps Researched</span>
                </h1>
                <p class="text-gray-400 text-lg max-w-2xl mx-auto">
                    Automated research pipeline with dual-model verification analyzing
                    {{ total_apps }} applications for Composio toolkit opportunities.
                </p>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                <div class="stat-card glass rounded-2xl p-6 text-center glow">
                    <div class="text-3xl font-black text-white mb-1">{{ insights.pct_self_serve }}%</div>
                    <div class="text-sm text-gray-400">Self-Serve</div>
                </div>
                <div class="stat-card glass rounded-2xl p-6 text-center glow">
                    <div class="text-3xl font-black text-white mb-1">{{ insights.dominant_auth }}</div>
                    <div class="text-sm text-gray-400">Top Auth Method</div>
                </div>
                <div class="stat-card glass rounded-2xl p-6 text-center glow">
                    <div class="text-3xl font-black text-white mb-1">{{ insights.pct_mcp_available }}%</div>
                    <div class="text-sm text-gray-400">MCP Available</div>
                </div>
                <div class="stat-card glass rounded-2xl p-6 text-center glow">
                    <div class="text-3xl font-black text-white mb-1">{{ "%.0f"|format(insights.avg_confidence * 100) }}%</div>
                    <div class="text-sm text-gray-400">Avg Confidence</div>
                </div>
            </div>

            <!-- Headline findings -->
            <div class="glass rounded-2xl p-8 glow">
                <h3 class="text-lg font-bold text-white mb-4">📊 Headline Findings</h3>
                <div class="grid md:grid-cols-2 gap-4 text-sm">
                    <div class="flex items-start gap-3">
                        <span class="text-green-400 mt-0.5">●</span>
                        <span><strong>{{ insights.pct_self_serve }}%</strong> of apps offer self-serve API access — high automation potential</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="text-blue-400 mt-0.5">●</span>
                        <span><strong>{{ insights.dominant_auth }}</strong> is the dominant authentication pattern</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="text-purple-400 mt-0.5">●</span>
                        <span><strong>{{ insights.pct_mcp_available }}%</strong> already support Model Context Protocol</span>
                    </div>
                    <div class="flex items-start gap-3">
                        <span class="text-yellow-400 mt-0.5">●</span>
                        <span>Most promising category: <strong>{{ insights.most_promising_category }}</strong></span>
                    </div>
                    {% if insights.top_blockers %}
                    <div class="flex items-start gap-3">
                        <span class="text-red-400 mt-0.5">●</span>
                        <span>Top blocker: <strong>{{ insights.top_blockers[0].blocker }}</strong> ({{ insights.top_blockers[0].count }} apps)</span>
                    </div>
                    {% endif %}
                    <div class="flex items-start gap-3">
                        <span class="text-cyan-400 mt-0.5">●</span>
                        <span><strong>{{ opp_high|length }}</strong> high-opportunity apps identified for Composio</span>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 2: Architecture -->
        <section id="architecture" class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-8">🏗️ Research Agent Architecture</h2>
            <div class="glass rounded-2xl p-8">
                <div class="grid md:grid-cols-2 gap-8">
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4">Pipeline Flow</h3>
                        <div class="space-y-4">
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">App Seeds (100 apps)</div>
                                <div class="text-xs text-gray-500">Input: name + hint URL</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">Documentation Discovery</div>
                                <div class="text-xs text-gray-500">Async crawling with trafilatura</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">Evidence Extraction</div>
                                <div class="text-xs text-gray-500">Deterministic keyword patterns</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">LLM Classification</div>
                                <div class="text-xs text-gray-500">GPT-OSS-120B via Groq</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">Verification Agent</div>
                                <div class="text-xs text-gray-500">Qwen3-32B (independent model)</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">Confidence Scoring</div>
                                <div class="text-xs text-gray-500">Composite 4-factor score</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">Human Audit (30 apps)</div>
                                <div class="text-xs text-gray-500">3 random per category</div>
                            </div>
                            <div class="pipeline-step py-2">
                                <div class="font-semibold text-brand-300">HTML Report</div>
                                <div class="text-xs text-gray-500">This page!</div>
                            </div>
                        </div>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4">Key Design Decisions</h3>
                        <div class="space-y-3 text-sm text-gray-300">
                            <div class="glass rounded-xl p-4">
                                <div class="font-semibold text-brand-300 mb-1">Hybrid Extraction</div>
                                <p class="text-gray-400">Deterministic regex extraction runs BEFORE any LLM call, reducing token usage by ~90%.</p>
                            </div>
                            <div class="glass rounded-xl p-4">
                                <div class="font-semibold text-brand-300 mb-1">Dual-Model Verification</div>
                                <p class="text-gray-400">Primary (GPT-OSS-120B) classifies; secondary (Qwen3-32B) independently verifies. A model never validates its own output.</p>
                            </div>
                            <div class="glass rounded-xl p-4">
                                <div class="font-semibold text-brand-300 mb-1">Evidence Bundles</div>
                                <p class="text-gray-400">Compact ~500-token bundles with keyword matches + relevant snippets. Full doc pages are never sent to LLMs.</p>
                            </div>
                            <div class="glass rounded-xl p-4">
                                <div class="font-semibold text-brand-300 mb-1">Checkpoint/Resume</div>
                                <p class="text-gray-400">Each stage saves JSON checkpoints. Pipeline can resume after interruption without re-processing completed stages.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Section 3: Verification Framework -->
        <section id="verification" class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-8">🔍 Verification Framework</h2>
            <div class="grid md:grid-cols-3 gap-6">
                <div class="glass rounded-2xl p-6">
                    <div class="text-2xl mb-3">🤖</div>
                    <h3 class="font-bold text-white mb-2">Research Agent</h3>
                    <p class="text-sm text-gray-400">GPT-OSS-120B classifies each app based on compact evidence bundles extracted from documentation.</p>
                </div>
                <div class="glass rounded-2xl p-6">
                    <div class="text-2xl mb-3">✅</div>
                    <h3 class="font-bold text-white mb-2">Verification Agent</h3>
                    <p class="text-sm text-gray-400">Qwen3-32B independently reviews each classification. Disagreements trigger confidence penalties and human review flags.</p>
                </div>
                <div class="glass rounded-2xl p-6">
                    <div class="text-2xl mb-3">👤</div>
                    <h3 class="font-bold text-white mb-2">Human Audit</h3>
                    <p class="text-sm text-gray-400">30 apps (3 per category) manually verified. Corrections applied back to the dataset with honest accuracy reporting.</p>
                </div>
            </div>
            <div class="mt-6 glass rounded-2xl p-6">
                <h3 class="font-bold text-white mb-4">Accuracy Metrics</h3>
                <div class="grid md:grid-cols-2 gap-6">
                    <div>
                        <div class="text-sm text-gray-400 mb-2">Average Confidence Score</div>
                        <div class="w-full bg-gray-800 rounded-full h-4">
                            <div class="bg-gradient-to-r from-brand-500 to-purple-500 h-4 rounded-full" style="width: {{ (insights.avg_confidence * 100)|int }}%"></div>
                        </div>
                        <div class="text-right text-xs text-gray-500 mt-1">{{ "%.1f"|format(insights.avg_confidence * 100) }}%</div>
                    </div>
                    <div>
                        <div class="text-sm text-gray-400 mb-2">Post-Audit Accuracy</div>
                        <div class="w-full bg-gray-800 rounded-full h-4">
                            <div class="bg-gradient-to-r from-green-500 to-emerald-500 h-4 rounded-full" style="width: {{ (insights.accuracy_after_verification * 100)|int }}%"></div>
                        </div>
                        <div class="text-right text-xs text-gray-500 mt-1">{{ "%.1f"|format(insights.accuracy_after_verification * 100) }}% ({{ insights.total_corrections }} corrections)</div>
                    </div>
                </div>
                {% if insights.lessons_learned %}
                <div class="mt-4">
                    <div class="text-sm text-gray-400 mb-2">Lessons Learned</div>
                    <ul class="text-sm text-gray-300 space-y-1">
                        {% for lesson in insights.lessons_learned %}
                        <li class="flex items-start gap-2"><span class="text-yellow-400">→</span> {{ lesson }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
        </section>

        <!-- Section 4-7: Analysis Charts -->
        <section id="analysis" class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-8">📈 Analysis</h2>
            <div class="grid md:grid-cols-2 gap-6">
                <!-- Auth Distribution -->
                <div class="glass rounded-2xl p-6">
                    <h3 class="font-bold text-white mb-4">Authentication Methods</h3>
                    <div class="chart-container"><canvas id="authChart"></canvas></div>
                </div>
                <!-- Access Distribution -->
                <div class="glass rounded-2xl p-6">
                    <h3 class="font-bold text-white mb-4">Self-Serve vs Gated</h3>
                    <div class="chart-container"><canvas id="accessChart"></canvas></div>
                </div>
                <!-- API Surface -->
                <div class="glass rounded-2xl p-6">
                    <h3 class="font-bold text-white mb-4">API Surface</h3>
                    <div class="chart-container"><canvas id="apiChart"></canvas></div>
                </div>
                <!-- MCP -->
                <div class="glass rounded-2xl p-6">
                    <h3 class="font-bold text-white mb-4">MCP Availability</h3>
                    <div class="chart-container"><canvas id="mcpChart"></canvas></div>
                </div>
            </div>

            <!-- Category Breakdown -->
            <div class="mt-6 glass rounded-2xl p-6">
                <h3 class="font-bold text-white mb-4">Apps by Category</h3>
                <div style="max-height: 350px;"><canvas id="categoryChart"></canvas></div>
            </div>

            <!-- Build Verdict -->
            <div class="mt-6 glass rounded-2xl p-6">
                <h3 class="font-bold text-white mb-4">Buildability Verdict</h3>
                <div class="chart-container"><canvas id="verdictChart"></canvas></div>
            </div>
        </section>

        <!-- Section 9: Common Blockers -->
        <section class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-8">🚧 Common Blockers</h2>
            <div class="glass rounded-2xl p-6">
                <div class="space-y-3">
                    {% for blocker in insights.top_blockers[:10] %}
                    <div class="flex items-center gap-4">
                        <div class="w-8 text-right text-sm font-mono text-gray-500">{{ loop.index }}</div>
                        <div class="flex-1">
                            <div class="flex items-center gap-3">
                                <span class="text-sm font-medium text-gray-200">{{ blocker.blocker }}</span>
                                <span class="badge badge-low">{{ blocker.count }} apps</span>
                            </div>
                            <div class="mt-1 w-full bg-gray-800 rounded-full h-2">
                                <div class="bg-gradient-to-r from-red-500 to-orange-500 h-2 rounded-full" style="width: {{ (blocker.count / total_apps * 100)|int }}%"></div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>

        <!-- Section 10: Composio Opportunity Matrix -->
        <section id="opportunities" class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-8">🎯 Composio Opportunity Matrix</h2>

            {% if opp_high %}
            <div class="mb-6">
                <h3 class="text-lg font-semibold text-green-400 mb-4">🟢 High Opportunity (Score ≥ 7)</h3>
                <div class="grid md:grid-cols-2 gap-3">
                    {% for app in opp_high[:12] %}
                    <div class="glass rounded-xl p-4 stat-card">
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-semibold text-white">{{ app.name }}</span>
                            <span class="badge badge-high">+{{ app.score }}</span>
                        </div>
                        <div class="text-xs text-gray-500 mb-1">{{ app.category }}</div>
                        <div class="text-xs text-gray-400">{{ app.rationale }}</div>
                        {% if app.has_toolkit %}<div class="text-xs text-brand-400 mt-1">⚡ Existing toolkit</div>{% endif %}
                        {% if app.is_new %}<div class="text-xs text-green-400 mt-1">🆕 New opportunity</div>{% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if opp_medium %}
            <div class="mb-6">
                <h3 class="text-lg font-semibold text-yellow-400 mb-4">🟡 Medium Opportunity (Score 3-6)</h3>
                <div class="grid md:grid-cols-3 gap-3">
                    {% for app in opp_medium[:15] %}
                    <div class="glass rounded-xl p-3">
                        <div class="flex items-center justify-between">
                            <span class="text-sm font-medium text-white">{{ app.name }}</span>
                            <span class="badge badge-medium">+{{ app.score }}</span>
                        </div>
                        <div class="text-xs text-gray-500">{{ app.category }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if opp_low %}
            <div>
                <h3 class="text-lg font-semibold text-red-400 mb-4">🔴 Low Opportunity (Score < 3)</h3>
                <div class="flex flex-wrap gap-2">
                    {% for app in opp_low %}
                    <span class="badge badge-low text-xs">{{ app.name }} ({{ app.score }})</span>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        </section>

        <!-- Section 12: Complete Dataset -->
        <section id="dataset" class="mb-20 fade-in">
            <h2 class="text-3xl font-bold text-white mb-4">📋 Complete Dataset</h2>
            <div class="mb-4">
                <input type="text" id="search-input" placeholder="Search apps, categories, auth methods..."
                    class="w-full md:w-96 bg-gray-900/50 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500">
            </div>
            <div class="glass rounded-2xl overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm" id="data-table">
                        <thead>
                            <tr class="border-b border-gray-800 text-left">
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(0)">#</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(1)">App</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(2)">Category</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(3)">Auth</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(4)">Access</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(5)">API</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">MCP</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(7)">Verdict</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Blocker</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(9)">Confidence</th>
                                <th class="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer" onclick="sortTable(10)">Opp.</th>
                            </tr>
                        </thead>
                        <tbody id="table-body">
                            {% for r in records %}
                            <tr class="table-row border-b border-gray-800/50 {% if loop.index is odd %}bg-gray-900/20{% endif %}">
                                <td class="px-4 py-3 text-gray-500 font-mono text-xs">{{ r.app_id }}</td>
                                <td class="px-4 py-3 font-medium text-white">
                                    {{ r.app_name }}
                                    {% if r.was_audited %}<span class="text-xs text-brand-400" title="Human audited">✓</span>{% endif %}
                                </td>
                                <td class="px-4 py-3 text-gray-400">{{ r.category }}</td>
                                <td class="px-4 py-3"><span class="badge {% if r.auth_method == 'OAuth2' %}badge-easy{% elif r.auth_method == 'API Key' %}badge-moderate{% else %}badge-unknown{% endif %}">{{ r.auth_method }}</span></td>
                                <td class="px-4 py-3"><span class="badge {% if r.access_model in ['Self-Serve', 'Freemium', 'Open Source'] %}badge-easy{% elif r.access_model == 'Gated' %}badge-hard{% else %}badge-unknown{% endif %}">{{ r.access_model }}</span></td>
                                <td class="px-4 py-3 text-gray-300">{{ r.api_type }}</td>
                                <td class="px-4 py-3">{% if r.has_mcp %}<span class="text-green-400">✓</span>{% else %}<span class="text-gray-600">—</span>{% endif %}</td>
                                <td class="px-4 py-3"><span class="badge badge-{{ r.build_verdict|lower|replace(' ', '-') }}">{{ r.build_verdict }}</span></td>
                                <td class="px-4 py-3 text-gray-400 text-xs max-w-32 truncate" title="{{ r.main_blocker }}">{{ r.main_blocker }}</td>
                                <td class="px-4 py-3">
                                    <span class="badge badge-{{ r.confidence_level|lower|replace(' ', '-') }}">{{ "%.0f"|format(r.confidence_score * 100) }}%</span>
                                </td>
                                <td class="px-4 py-3">
                                    <span class="badge badge-{{ r.opportunity_level|lower }}">{{ r.opportunity_score }}</span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer class="relative z-10 border-t border-gray-800 py-8">
        <div class="max-w-7xl mx-auto px-6 text-center text-sm text-gray-500">
            <p>Composio AI Product Ops Research System — Built with GPT-OSS-120B + Qwen3-32B via Groq</p>
            <p class="mt-1">Dual-model verification · {{ total_apps }} apps · Human-audited</p>
        </div>
    </footer>

    <script>
        // ─── Chart.js Configuration ──────────────────────────────────
        const chartColors = ['#818cf8','#c084fc','#f472b6','#34d399','#fbbf24','#fb923c','#f87171','#38bdf8','#a78bfa','#4ade80'];
        const chartDefaults = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', font: { size: 11 }, padding: 12 } }
            }
        };

        // Auth Chart
        new Chart(document.getElementById('authChart'), {
            type: 'doughnut',
            data: { labels: {{ auth_labels }}, datasets: [{ data: {{ auth_values }}, backgroundColor: chartColors, borderWidth: 0 }] },
            options: { ...chartDefaults, cutout: '55%' }
        });

        // Access Chart
        new Chart(document.getElementById('accessChart'), {
            type: 'doughnut',
            data: { labels: {{ access_labels }}, datasets: [{ data: {{ access_values }}, backgroundColor: chartColors, borderWidth: 0 }] },
            options: { ...chartDefaults, cutout: '55%' }
        });

        // API Chart
        new Chart(document.getElementById('apiChart'), {
            type: 'doughnut',
            data: { labels: {{ api_labels }}, datasets: [{ data: {{ api_values }}, backgroundColor: chartColors, borderWidth: 0 }] },
            options: { ...chartDefaults, cutout: '55%' }
        });

        // MCP Chart
        new Chart(document.getElementById('mcpChart'), {
            type: 'doughnut',
            data: { labels: {{ mcp_labels }}, datasets: [{ data: {{ mcp_values }}, backgroundColor: ['#4ade80','#374151'], borderWidth: 0 }] },
            options: { ...chartDefaults, cutout: '55%' }
        });

        // Category Chart
        new Chart(document.getElementById('categoryChart'), {
            type: 'bar',
            data: {
                labels: {{ cat_labels }},
                datasets: [{
                    label: 'Apps',
                    data: {{ cat_values }},
                    backgroundColor: 'rgba(99,102,241,0.6)',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 45 }, grid: { display: false } }
                }
            }
        });

        // Verdict Chart
        new Chart(document.getElementById('verdictChart'), {
            type: 'doughnut',
            data: { labels: {{ verdict_labels }}, datasets: [{ data: {{ verdict_values }}, backgroundColor: ['#4ade80','#fbbf24','#fb923c','#f87171','#64748b'], borderWidth: 0 }] },
            options: { ...chartDefaults, cutout: '55%' }
        });

        // ─── Search ──────────────────────────────────────────────────
        document.getElementById('search-input').addEventListener('input', function(e) {
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#table-body tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });

        // ─── Sort ────────────────────────────────────────────────────
        let sortDir = {};
        function sortTable(colIndex) {
            const table = document.getElementById('data-table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const dir = sortDir[colIndex] = !sortDir[colIndex];

            rows.sort((a, b) => {
                let aVal = a.cells[colIndex].textContent.trim();
                let bVal = b.cells[colIndex].textContent.trim();
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return dir ? aNum - bNum : bNum - aNum;
                }
                return dir ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            });

            rows.forEach(row => tbody.appendChild(row));
        }
    </script>
</body>
</html>"""
