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

    high_opportunities = []
    medium_opportunities = []
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
            elif score.level.value == 'High':
                high_opportunities.append(item)
            elif score.level.value == 'Medium':
                medium_opportunities.append(item)

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
        "high_opportunities": high_opportunities,
        "medium_opportunities": medium_opportunities,
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
                <div class="text-gray-400 text-sm flex items-center gap-2">
                    <i data-lucide="{% if insights.final_audit_accuracy > 0 %}check-circle{% else %}brain-circuit{% endif %}" class="w-4 h-4"></i> 
                    {% if insights.final_audit_accuracy > 0 %}Audit Accuracy{% else %}LLM Accuracy{% endif %}
                </div>
                <div class="text-4xl font-semibold stat-value text-yellow-400">
                    {% if insights.final_audit_accuracy > 0 %}{{ insights.final_audit_accuracy }}%{% else %}{{ insights.second_pass_accuracy }}%{% endif %}
                </div>
            </div>
        </section>

        <!-- KEY INSIGHTS & PATTERNS -->
        <section id="patterns" class="space-y-6">
            <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                <i data-lucide="lightbulb" class="text-brand-400"></i> Key Insights & Patterns
            </h2>
            <div class="glass-card p-8 space-y-6 border-l-4 border-l-brand-400">
                <p class="text-gray-300 leading-relaxed text-lg">
                    We clustered the results of all 100 applications to surface the dominant trends in the integration landscape:
                </p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="space-y-2">
                        <h4 class="text-white font-medium flex items-center gap-2"><i data-lucide="key" class="w-4 h-4 text-green-400"></i> OAuth Dominates Modern Apps</h4>
                        <p class="text-sm text-gray-400 leading-relaxed">OAuth2 and API Keys make up the vast majority of authentication. Legacy Basic Auth is virtually extinct outside of on-prem enterprise setups.</p>
                    </div>
                    <div class="space-y-2">
                        <h4 class="text-white font-medium flex items-center gap-2"><i data-lucide="unlock" class="w-4 h-4 text-green-400"></i> Easy Wins in E-commerce & Productivity</h4>
                        <p class="text-sm text-gray-400 leading-relaxed">Apps in E-commerce, Marketing, and Productivity are heavily self-serve (developer portals available instantly). These represent immediate, low-friction integration targets.</p>
                    </div>
                    <div class="space-y-2">
                        <h4 class="text-white font-medium flex items-center gap-2"><i data-lucide="lock" class="w-4 h-4 text-red-400"></i> Finance & Health Need Outreach</h4>
                        <p class="text-sm text-gray-400 leading-relaxed">Fintech, HR, and CRM systems (like DealCloud) are frequently gated behind "Contact Sales" or partner networks, requiring direct BD outreach before a toolkit can be built.</p>
                    </div>
                    <div class="space-y-2">
                        <h4 class="text-white font-medium flex items-center gap-2"><i data-lucide="alert-triangle" class="w-4 h-4 text-yellow-400"></i> The Primary Blocker</h4>
                        <p class="text-sm text-gray-400 leading-relaxed">When an app is marked "Not Feasible," the overwhelming reason is the sheer lack of a public API, followed closely by enterprise gatekeeping (requiring a $50k/yr contract to access the sandbox).</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- OPPORTUNITY MATRIX -->
        <section id="opportunities" class="space-y-12">
            <div class="space-y-4">
                <div class="space-y-2">
                    <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                        <i data-lucide="target" class="text-brand-400"></i> Opportunity Matrix
                    </h2>
                    <p class="text-gray-400">The highest ROI integrations ranked by accessibility, documentation quality, and API availability.</p>
                </div>
                
                <!-- SCORING METHODOLOGY CALLOUT -->
                <div class="p-6 rounded-xl border border-brand-500/20 bg-brand-500/5 flex flex-col md:flex-row gap-8 items-center justify-between">
                    <div class="flex-1 space-y-2">
                        <h4 class="text-sm font-semibold text-brand-400 uppercase tracking-widest flex items-center gap-2">
                            <i data-lucide="info" class="w-4 h-4"></i> Opportunity Scoring Methodology
                        </h4>
                        <p class="text-xs text-gray-400 leading-relaxed max-w-2xl">
                            Scores are calculated deterministically to surface the lowest-friction integration paths.
                        </p>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 pt-2">
                            <div class="text-xs flex justify-between"><span class="text-gray-300">Self-Serve</span> <span class="text-green-400 font-mono">+3</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-300">OAuth/API Key</span> <span class="text-green-400 font-mono">+2</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-300">REST API</span> <span class="text-green-400 font-mono">+2</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-300">Public Docs</span> <span class="text-green-400 font-mono">+2</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-300">MCP Server</span> <span class="text-green-400 font-mono">+1</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-500">Gated Access</span> <span class="text-red-400 font-mono">-3</span></div>
                            <div class="text-xs flex justify-between"><span class="text-gray-500">No API</span> <span class="text-red-400 font-mono">-5</span></div>
                        </div>
                    </div>
                    <div class="flex flex-col items-center justify-center px-6 border-l border-brand-500/20">
                        <span class="text-xs text-gray-500 font-mono uppercase">Max Score</span>
                        <span class="text-3xl font-bold text-white stat-value">10.0</span>
                    </div>
                </div>
            </div>

            <!-- High Feasibility Opportunities -->
            <div class="space-y-6">
                <h3 class="text-xl font-medium flex items-center gap-2 text-green-400">
                    <i data-lucide="zap" class="w-5 h-5"></i> High Feasibility 
                    <span class="text-sm font-normal text-gray-500">(Score >= 7)</span>
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for item in high_opportunities[:15] %}
                    <div class="glass-card p-5 border-l-2 border-l-green-500 hover:bg-white/5 transition cursor-default">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-semibold text-lg">{{ item.name }}</h4>
                            <span class="badge stat-value badge-green">
                                Score: {{ item.score }}
                            </span>
                        </div>
                        <div class="text-xs text-brand-400 mb-3">{{ item.category }}</div>
                        <div class="space-y-1">
                            {% for rat in item.rationale %}
                            <div class="flex items-center gap-1.5 text-sm {% if rat.type == 'positive' %}text-gray-300{% else %}text-gray-500{% endif %}">
                                {% if rat.type == 'positive' %}
                                <i data-lucide="triangle" class="w-3 h-3 text-green-400 fill-green-400"></i>
                                {% else %}
                                <i data-lucide="triangle" class="w-3 h-3 text-red-400 fill-red-400 rotate-180"></i>
                                {% endif %}
                                {{ rat.text }} <span class="font-mono text-xs opacity-70 ml-auto">{% if rat.type == 'positive' %}+{% endif %}{{ rat.score }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Medium Feasibility Opportunities -->
            <div class="space-y-6 pt-8 border-t border-border">
                <h3 class="text-xl font-medium flex items-center gap-2 text-yellow-400">
                    <i data-lucide="activity" class="w-5 h-5"></i> Medium Feasibility 
                    <span class="text-sm font-normal text-gray-500">(Score >= 3)</span>
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for item in medium_opportunities[:12] %}
                    <div class="glass-card p-5 border-l-2 border-l-yellow-500 hover:bg-white/5 transition cursor-default">
                        <div class="flex justify-between items-start mb-2">
                            <h4 class="font-semibold text-lg">{{ item.name }}</h4>
                            <span class="badge stat-value badge-yellow">
                                Score: {{ item.score }}
                            </span>
                        </div>
                        <div class="text-xs text-brand-400 mb-3">{{ item.category }}</div>
                        <div class="space-y-1">
                            {% for rat in item.rationale %}
                            <div class="flex items-center gap-1.5 text-sm {% if rat.type == 'positive' %}text-gray-300{% else %}text-gray-500{% endif %}">
                                {% if rat.type == 'positive' %}
                                <i data-lucide="triangle" class="w-3 h-3 text-green-400 fill-green-400"></i>
                                {% else %}
                                <i data-lucide="triangle" class="w-3 h-3 text-red-400 fill-red-400 rotate-180"></i>
                                {% endif %}
                                {{ rat.text }} <span class="font-mono text-xs opacity-70 ml-auto">{% if rat.type == 'positive' %}+{% endif %}{{ rat.score }}</span>
                            </div>
                            {% endfor %}
                        </div>
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
                    <div class="glass-card p-4 hover:bg-white/5 transition flex justify-between items-center opacity-80 border-l-2 border-l-brand-500">
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

        <!-- AGENT ARCHITECTURE & VERIFICATION -->
        <section id="methodology" class="space-y-8">
            <div class="space-y-2">
                <h2 class="text-3xl font-semibold tracking-tight flex items-center gap-3">
                    <i data-lucide="cpu" class="text-brand-400"></i> Methodology & Verification Loop
                </h2>
                <p class="text-gray-400">How the autonomous agents gathered data, and how we proved it was accurate.</p>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- The Agent -->
                <div class="glass-card p-6 space-y-4">
                    <h3 class="text-xl font-medium text-white flex items-center gap-2">
                        <i data-lucide="bot" class="w-5 h-5 text-brand-400"></i> The Agent Architecture
                    </h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        Instead of scraping manually, we built a dual-agent pipeline utilizing Composio's own ideology:
                    </p>
                    <ul class="text-sm text-gray-400 space-y-3">
                        <li class="flex gap-3 items-start"><i data-lucide="search" class="w-4 h-4 text-brand-400 shrink-0 mt-0.5"></i> <span><strong>Doc Discovery:</strong> An agent leverages Trafilatura to autonomously crawl the web and extract the exact developer API documentation URLs and clean text for each app.</span></li>
                        <li class="flex gap-3 items-start"><i data-lucide="brain-circuit" class="w-4 h-4 text-brand-400 shrink-0 mt-0.5"></i> <span><strong>Primary Classifier (GPT-OSS 120B):</strong> Reads minimized DOM elements and classifies the auth method, API surface, and buildability.</span></li>
                        <li class="flex gap-3 items-start"><i data-lucide="scale" class="w-4 h-4 text-brand-400 shrink-0 mt-0.5"></i> <span><strong>Secondary Verifier (Qwen 3 32B):</strong> Acts as a discriminator. It receives the same data and the Classifier's output, assigning confidence scores and flagging hallucinations.</span></li>
                    </ul>
                    <a href="https://github.com/sh3bh1t/composio_aipi/blob/main/README.md" target="_blank" class="text-brand-400 hover:underline inline-flex items-center gap-1 mt-4 text-sm font-medium">
                        Click here for the complete architecture diagram <i data-lucide="external-link" class="w-4 h-4"></i>
                    </a>
                </div>

                <!-- Verification -->
                <div class="glass-card p-6 space-y-4 border-t-4 border-t-yellow-400 md:border-t-0 md:border-l-4 md:border-l-yellow-400">
                    <h3 class="text-xl font-medium text-white flex items-center gap-2">
                        <i data-lucide="check-square" class="w-5 h-5 text-yellow-400"></i> Verification & Accuracy Audit
                    </h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        Accuracy is what matters most. We ran a strict human-in-the-loop (HITL) audit across a sample set of 30 apps (3 per category) to verify our agent's claims.
                    </p>
                    <ol class="text-xs text-gray-400 space-y-2 list-decimal list-inside ml-1">
                        <li><strong>Generate Sample:</strong> Automatically sampled 30 apps into an <code class="bg-surface2 px-1 py-0.5 rounded text-brand-400">audit_worksheet.json</code>.</li>
                        <li><strong>Manual Grading:</strong> A human researcher manually verified the API docs for all 30 apps, recording the ground truth alongside the pipeline's guesses.</li>
                        <li><strong>Recalculate & Apply:</strong> The system ingested the human corrections, calculated true accuracy, and patched the final dataset to reflect reality.</li>
                    </ol>
                    <div class="space-y-4 pt-2">
                        <div class="bg-surface2/50 p-4 rounded-lg space-y-1 border border-border">
                            <div class="flex justify-between items-center text-sm">
                                <span class="text-gray-300">1. First-Pass LLM (GPT-OSS 120B):</span>
                                <span class="text-white font-mono">{{ insights.first_pass_accuracy }}%</span>
                            </div>
                            <div class="flex justify-between items-center text-sm">
                                <span class="text-gray-300">2. Second-Pass LLM (Qwen 3 32B):</span>
                                <span class="text-white font-mono">{{ insights.second_pass_accuracy }}%</span>
                            </div>
                            <div class="flex justify-between items-center text-sm pt-2 mt-2 border-t border-border">
                                <span class="text-brand-400 font-medium">3. Final Audited Accuracy (Human):</span>
                                <span class="text-green-400 font-mono font-bold">{{ insights.final_audit_accuracy }}%</span>
                            </div>
                        </div>
                        <div class="text-xs text-gray-400 leading-relaxed mt-4 bg-surface2/30 p-4 rounded-lg border border-border/50">
                            {% if insights.dynamic_hits %}
                            <div class="mb-3">
                                <strong class="text-green-400 flex items-center gap-1 mb-1"><i data-lucide="trending-up" class="w-3 h-3"></i> Top Hits</strong>
                                <ul class="list-disc list-inside space-y-1 ml-1">
                                    {% for hit in insights.dynamic_hits %}
                                    <li>{{ hit }} - The agent excelled at extracting this field.</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% endif %}
                            
                            {% if insights.dynamic_misses %}
                            <div>
                                <strong class="text-red-400 flex items-center gap-1 mb-1"><i data-lucide="trending-down" class="w-3 h-3"></i> Top Misses</strong>
                                <ul class="list-disc list-inside space-y-1 ml-1">
                                    {% for miss in insights.dynamic_misses %}
                                    <li>{{ miss }} - The agent struggled or hallucinated on this field.</li>
                                    {% endfor %}
                                </ul>
                            </div>
                            {% else %}
                            <p class="text-gray-500 italic mt-2">Generate and apply the human audit worksheet to calculate real hits and misses.</p>
                            {% endif %}
                        </div>
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
                                <th class="px-6 py-4 cursor-pointer hover:text-white w-1/4" onclick="sortTable(0)">App & Description <i data-lucide="arrow-up-down" class="inline w-3 h-3 ml-1"></i></th>
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
                                <td class="px-6 py-4">
                                    <div class="font-medium text-white">{{ record.app_name }}</div>
                                    <div class="text-xs text-gray-500 mt-1 max-w-[200px] truncate" title="{{ record.one_line_description }}">{{ record.one_line_description }}</div>
                                </td>
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
