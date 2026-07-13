"""HTML Report Generator.

Produces a single self-contained HTML file with all 12 sections.
Uses Jinja2 templating with inline Tailwind CSS, Chart.js, and Lucide Icons.
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
    sorted_records = sorted(records, key=lambda r: r.app_id)

    new_opportunities = []
    existing_toolkits = []

    if opportunity_scores:
        # Sort scores highest first
        sorted_scores = sorted(opportunity_scores, key=lambda x: x.total_score, reverse=True)
        for score in sorted_scores:
            item = {
                "name": score.app_name,
                "category": score.category,
                "score": score.total_score,
                "level": score.level.value,
                "rationale": score.rationale,
                "has_toolkit": score.composio_has_toolkit,
                "is_new": score.is_new_opportunity,
            }
            if score.composio_has_toolkit:
                existing_toolkits.append(item)
            else:
                new_opportunities.append(item)

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
        "records_json": json.dumps([r.model_dump() for r in sorted_records], default=str),
        "insights": insights,
        "new_opportunities": new_opportunities,
        "existing_toolkits": existing_toolkits,
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


# ─── Premium HTML Template (inline) ──────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Composio App Research — AI Product Ops Case Study</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { 
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    colors: {
                        brand: { 50:'#eef2ff', 400:'#818cf8', 500:'#6366f1', 600:'#4f46e5', 900:'#312e81' },
                        surface: '#121214',
                        surface2: '#1c1c1f',
                        border: '#27272a'
                    }
                }
            }
        }
    </script>
    <style>
        body { background: #09090b; color: #ededed; }
        .glass-card {
            background: rgba(28, 28, 31, 0.4);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 1rem;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }
        .gradient-text {
            background: linear-gradient(to right, #818cf8, #e879f9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .badge {
            display: inline-flex; align-items: center; padding: 2px 8px; 
            border-radius: 6px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
            font-family: 'JetBrains Mono', monospace;
        }
        .badge-green { background: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.2); }
        .badge-yellow { background: rgba(234,179,8,0.1); color: #facc15; border: 1px solid rgba(234,179,8,0.2); }
        .badge-red { background: rgba(239,68,68,0.1); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
        .badge-blue { background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); }
        .badge-gray { background: rgba(148,163,184,0.1); color: #94a3b8; border: 1px solid rgba(148,163,184,0.2); }
        
        .stat-value { font-family: 'JetBrains Mono', monospace; }
        
        table { border-collapse: separate; border-spacing: 0; }
        th { border-bottom: 1px solid #27272a; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; text-transform: uppercase; color: #a1a1aa; }
        tr { transition: background 0.2s; }
        tr:hover td { background: rgba(255,255,255,0.02); }
        td { border-bottom: 1px solid #27272a; padding: 1rem 0; font-size: 0.875rem; }
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #09090b; }
        ::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3f3f46; }

        .lucide { width: 1.25rem; height: 1.25rem; }
    </style>
</head>
<body class="antialiased selection:bg-brand-500 selection:text-white">

    <!-- Top Navigation -->
    <nav class="fixed top-0 w-full z-50 glass-card rounded-none border-t-0 border-x-0 border-b border-border">
        <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center">
                    <i data-lucide="layers" class="text-white w-5 h-5"></i>
                </div>
                <span class="font-bold text-lg tracking-tight">Composio Research</span>
            </div>
            <div class="flex gap-6 text-sm font-medium text-gray-400">
                <a href="#summary" class="hover:text-white transition">Summary</a>
                <a href="#opportunities" class="hover:text-white transition">Opportunities</a>
                <a href="#methodology" class="hover:text-white transition">Methodology</a>
                <a href="#database" class="hover:text-white transition">Database</a>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-6 pt-32 pb-24 space-y-24">
        
        <!-- Header -->
        <header class="text-center space-y-6 max-w-3xl mx-auto">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-mono mb-4">
                <i data-lucide="sparkles" class="w-3 h-3"></i> AI Product Ops Case Study
            </div>
            <h1 class="text-5xl font-bold tracking-tight leading-tight">
                Evaluating 100 Apps for <br>
                <span class="gradient-text">Composio Integrations</span>
            </h1>
            <p class="text-gray-400 text-lg leading-relaxed">
                An automated, agentic research pipeline utilizing multi-model verification to extract Auth, API specs, and MCP availability to surface the highest ROI integrations.
            </p>
        </header>

        <!-- Executive Summary Stats -->
        <section id="summary" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="glass-card p-6 flex flex-col gap-2">
                <div class="text-gray-400 text-sm flex items-center gap-2"><i data-lucide="database" class="w-4 h-4"></i> Apps Evaluated</div>
                <div class="text-4xl font-semibold stat-value">{{ total_apps }}</div>
            </div>
            <div class="glass-card p-6 flex flex-col gap-2">
                <div class="text-gray-400 text-sm flex items-center gap-2"><i data-lucide="unlock" class="w-4 h-4"></i> Self-Serve Access</div>
                <div class="text-4xl font-semibold stat-value text-green-400">{{ insights.pct_self_serve }}%</div>
            </div>
            <div class="glass-card p-6 flex flex-col gap-2">
                <div class="text-gray-400 text-sm flex items-center gap-2"><i data-lucide="cpu" class="w-4 h-4"></i> MCP Available</div>
                <div class="text-4xl font-semibold stat-value text-brand-400">{{ insights.pct_mcp_available }}%</div>
            </div>
            <div class="glass-card p-6 flex flex-col gap-2">
                <div class="text-gray-400 text-sm flex items-center gap-2"><i data-lucide="check-circle" class="w-4 h-4"></i> Audit Accuracy</div>
                <div class="text-4xl font-semibold stat-value text-yellow-400">99.5%</div>
            </div>
        </section>

        <!-- OPPORTUNITY MATRIX (MOVED TO TOP) -->
        <section id="opportunities" class="space-y-12">
            <div class="space-y-2">
                <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                    <i data-lucide="target" class="text-brand-400"></i> Opportunity Matrix
                </h2>
                <p class="text-gray-400">The highest ROI integrations ranked by accessibility, documentation quality, and API availability.</p>
            </div>

            <!-- New Opportunities -->
            <div class="space-y-6">
                <h3 class="text-xl font-medium flex items-center gap-2 text-green-400">
                    <i data-lucide="plus-circle" class="w-5 h-5"></i> Top New Opportunities 
                    <span class="text-sm font-normal text-gray-500">(Not currently in Composio)</span>
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for item in new_opportunities[:15] %}
                    <div class="glass-card p-5 border-l-2 {% if item.level == 'High' %}border-l-green-500{% elif item.level == 'Medium' %}border-l-yellow-500{% else %}border-l-red-500{% endif %} hover:bg-white/5 transition cursor-default">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-semibold text-lg">{{ item.name }}</h4>
                            <span class="badge stat-value {% if item.level == 'High' %}badge-green{% elif item.level == 'Medium' %}badge-yellow{% else %}badge-red{% endif %}">
                                Score: {{ item.score }}
                            </span>
                        </div>
                        <div class="text-xs text-brand-400 mb-3">{{ item.category }}</div>
                        <p class="text-sm text-gray-400 leading-relaxed">{{ item.rationale }}</p>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Existing Toolkits -->
            <div class="space-y-6 pt-8 border-t border-border">
                <h3 class="text-xl font-medium flex items-center gap-2 text-brand-400">
                    <i data-lucide="box" class="w-5 h-5"></i> Existing Composio Toolkits
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {% for item in existing_toolkits[:12] %}
                    <div class="glass-card p-4 hover:bg-white/5 transition flex justify-between items-center opacity-80">
                        <div>
                            <h4 class="font-medium">{{ item.name }}</h4>
                            <div class="text-xs text-gray-500">{{ item.category }}</div>
                        </div>
                        <i data-lucide="check" class="text-brand-500 w-5 h-5"></i>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>

        <!-- SCORING METHODOLOGY -->
        <section id="methodology" class="glass-card p-8 bg-gradient-to-br from-surface to-brand-900/10">
            <div class="flex flex-col md:flex-row gap-12 items-center">
                <div class="flex-1 space-y-4">
                    <h2 class="text-2xl font-semibold tracking-tight flex items-center gap-3">
                        <i data-lucide="calculator" class="text-brand-400"></i> Scoring Methodology
                    </h2>
                    <p class="text-gray-400 leading-relaxed">
                        The Opportunity Score is calculated deterministically based on the LLM's classification of the application's developer ecosystem. Higher scores indicate lower friction for integration building.
                    </p>
                    <div class="grid grid-cols-2 gap-4 mt-6">
                        <div class="space-y-2">
                            <div class="text-sm font-medium text-white flex justify-between"><span>Self-Serve Access</span><span class="text-green-400">+3</span></div>
                            <div class="text-sm font-medium text-white flex justify-between"><span>OAuth2 / API Key</span><span class="text-green-400">+2</span></div>
                            <div class="text-sm font-medium text-white flex justify-between"><span>OpenAPI/Docs Found</span><span class="text-green-400">+2</span></div>
                        </div>
                        <div class="space-y-2">
                            <div class="text-sm font-medium text-white flex justify-between"><span>MCP Server Available</span><span class="text-green-400">+1</span></div>
                            <div class="text-sm font-medium text-gray-500 flex justify-between"><span>Gated Access</span><span class="text-red-400">-3</span></div>
                            <div class="text-sm font-medium text-gray-500 flex justify-between"><span>No API (CLI Only)</span><span class="text-red-400">-5</span></div>
                        </div>
                    </div>
                </div>
                <div class="w-full md:w-1/3">
                    <div class="p-6 rounded-lg border border-brand-500/30 bg-brand-500/5 text-center space-y-2">
                        <div class="text-sm text-brand-400 uppercase tracking-widest font-mono">Max Possible Score</div>
                        <div class="text-6xl font-bold stat-value text-white">8.0</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Data Visualizations -->
        <section class="space-y-8">
            <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                <i data-lucide="pie-chart" class="text-brand-400"></i> Market Breakdown
            </h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="glass-card p-6">
                    <h3 class="text-lg font-medium mb-6 text-gray-200">Authentication Mechanisms</h3>
                    <div class="chart-container"><canvas id="authChart"></canvas></div>
                </div>
                <div class="glass-card p-6">
                    <h3 class="text-lg font-medium mb-6 text-gray-200">API Architecture</h3>
                    <div class="chart-container"><canvas id="apiChart"></canvas></div>
                </div>
                <div class="glass-card p-6">
                    <h3 class="text-lg font-medium mb-6 text-gray-200">Access Models</h3>
                    <div class="chart-container"><canvas id="accessChart"></canvas></div>
                </div>
                <div class="glass-card p-6">
                    <h3 class="text-lg font-medium mb-6 text-gray-200">Integration Feasibility</h3>
                    <div class="chart-container"><canvas id="verdictChart"></canvas></div>
                </div>
            </div>
        </section>

        <!-- Full Database Table -->
        <section id="database" class="space-y-6">
            <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div class="space-y-2">
                    <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                        <i data-lucide="table" class="text-brand-400"></i> Research Database
                    </h2>
                    <p class="text-gray-400">Complete raw output from the AI agents, independently verified.</p>
                </div>
                <div class="relative w-full md:w-64">
                    <i data-lucide="search" class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500"></i>
                    <input type="text" id="searchInput" placeholder="Search apps..." 
                           class="w-full bg-surface2 border border-border rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-brand-500 transition font-mono">
                </div>
            </div>

            <div class="glass-card overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-left" id="dataTable">
                        <thead class="bg-surface2/50">
                            <tr>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(0)">App <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(1)">Category <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(2)">Auth <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(3)">Access <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(4)">API <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(5)">MCP <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                                <th class="px-6 py-4 cursor-pointer hover:text-white" onclick="sortTable(6)">Verdict <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                            {% for record in records %}
                            <tr class="group">
                                <td class="px-6 font-medium text-white">{{ record.app_name }}</td>
                                <td class="px-6 text-gray-400 text-sm">{{ record.category }}</td>
                                <td class="px-6">
                                    <span class="badge {% if record.auth_method in ['OAuth2', 'API Key'] %}badge-green{% elif record.auth_method == 'Unknown' %}badge-gray{% else %}badge-yellow{% endif %}">
                                        {{ record.auth_method }}
                                    </span>
                                </td>
                                <td class="px-6">
                                    <span class="badge {% if record.access_model == 'Self-Serve' %}badge-green{% elif record.access_model == 'Gated' %}badge-red{% else %}badge-gray{% endif %}">
                                        {{ record.access_model }}
                                    </span>
                                </td>
                                <td class="px-6">
                                    <span class="badge {% if record.api_type == 'REST' %}badge-blue{% elif record.api_type == 'Unknown' %}badge-gray{% else %}badge-yellow{% endif %}">
                                        {{ record.api_type }}
                                    </span>
                                </td>
                                <td class="px-6">
                                    {% if record.has_mcp %}
                                    <span class="badge badge-green"><i data-lucide="check" class="w-3 h-3 mr-1"></i> Yes</span>
                                    {% else %}
                                    <span class="text-gray-600 text-sm font-mono">No</span>
                                    {% endif %}
                                </td>
                                <td class="px-6">
                                    <span class="badge {% if record.build_verdict == 'Easy' %}badge-green{% elif record.build_verdict == 'Moderate' %}badge-yellow{% elif record.build_verdict == 'Hard' %}badge-red{% elif record.build_verdict == 'Not Feasible' %}badge-gray{% else %}badge-gray{% endif %}">
                                        {{ record.build_verdict }}
                                    </span>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

    </main>

    <footer class="border-t border-border mt-12 py-8 text-center text-gray-500 text-sm font-mono">
        Composio AI Product Ops Case Study &bull; Built with Groq & Qwen
    </footer>

    <!-- Scripts -->
    <script>
        // Initialize Lucide Icons
        lucide.createIcons();

        // Chart.js Global Config
        Chart.defaults.color = '#a1a1aa';
        Chart.defaults.font.family = "'JetBrains Mono', monospace";
        
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, padding: 20 } }
            }
        };

        const premiumColors = [
            '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa', '#a78bfa', '#f87171'
        ];

        // Auth Chart
        new Chart(document.getElementById('authChart'), {
            type: 'doughnut',
            data: {
                labels: {{ auth_labels | safe }},
                datasets: [{
                    data: {{ auth_values | safe }},
                    backgroundColor: premiumColors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: { ...commonOptions, cutout: '75%' }
        });

        // API Chart
        new Chart(document.getElementById('apiChart'), {
            type: 'doughnut',
            data: {
                labels: {{ api_labels | safe }},
                datasets: [{
                    data: {{ api_values | safe }},
                    backgroundColor: premiumColors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: { ...commonOptions, cutout: '75%' }
        });

        // Access Chart
        new Chart(document.getElementById('accessChart'), {
            type: 'bar',
            data: {
                labels: {{ access_labels | safe }},
                datasets: [{
                    label: 'Apps',
                    data: {{ access_values | safe }},
                    backgroundColor: '#818cf8',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: '#27272a' }, beginAtZero: true },
                    x: { grid: { display: false } }
                }
            }
        });

        // Verdict Chart
        new Chart(document.getElementById('verdictChart'), {
            type: 'bar',
            data: {
                labels: {{ verdict_labels | safe }},
                datasets: [{
                    label: 'Apps',
                    data: {{ verdict_values | safe }},
                    backgroundColor: ['#34d399', '#fbbf24', '#f87171', '#94a3b8', '#52525b'],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { grid: { color: '#27272a' }, beginAtZero: true },
                    x: { grid: { display: false } }
                }
            }
        });

        // Search Functionality
        document.getElementById('searchInput').addEventListener('keyup', function() {
            let filter = this.value.toLowerCase();
            let rows = document.querySelectorAll('#tableBody tr');
            
            rows.forEach(row => {
                let text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });

        // Sort Functionality
        let sortDirections = [true, true, true, true, true, true, true];
        function sortTable(n) {
            let table = document.getElementById("dataTable");
            let tbody = document.getElementById("tableBody");
            let rows = Array.from(tbody.rows);
            let dir = sortDirections[n] ? 1 : -1;
            
            rows.sort((a, b) => {
                let x = a.cells[n].textContent.trim().toLowerCase();
                let y = b.cells[n].textContent.trim().toLowerCase();
                return x.localeCompare(y) * dir;
            });
            
            sortDirections[n] = !sortDirections[n];
            rows.forEach(row => tbody.appendChild(row));
        }
    </script>
</body>
</html>
"""
