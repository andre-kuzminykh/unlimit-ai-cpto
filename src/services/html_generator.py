"""HTML report generator using Jinja2 with Glassmorphism + Aurora UI."""

from __future__ import annotations

import logging
import uuid

from jinja2 import Template

from src.config import REPORTS_DIR, REPORT_BASE_URL
from src.models.schemas import ProcessAnalysis

logger = logging.getLogger(__name__)


def _prepare_context(analysis: ProcessAnalysis) -> dict:
    """Build Jinja2 template context from the analysis with mermaid sources."""
    ctx = analysis.model_dump()
    return ctx


REPORT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ process_title }} — Process Analysis Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --lime: #bef264;
    --teal: #2dd4bf;
    --cyan: #67e8f9;
    --purple: #7c3aed;
    --text: #0f172a;
    --text-light: #475569;
    --card-bg: rgba(255,255,255,0.55);
    --card-border: rgba(255,255,255,0.8);
    --card-shadow: 0 8px 32px rgba(124,58,237,0.12), 0 2px 8px rgba(0,0,0,0.04);
    --radius: 1.5rem;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #f8f9fc;
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Aurora background — white base with soft floating blobs */
  .aurora-bg {
    position: fixed; inset: 0; z-index: 0; overflow: hidden;
    background: #ffffff;
  }
  .aurora-bg .blob {
    position: absolute; border-radius: 50%; opacity: 0.18;
  }
  .aurora-bg .blob:nth-child(1) {
    width: 700px; height: 700px; background: var(--purple);
    filter: blur(100px);
    top: -12%; left: -8%;
    animation: float1 14s ease-in-out infinite alternate;
  }
  .aurora-bg .blob:nth-child(2) {
    width: 550px; height: 550px; background: var(--teal);
    filter: blur(110px);
    top: 25%; right: -12%; opacity: 0.15;
    animation: float2 16s ease-in-out infinite alternate;
  }
  .aurora-bg .blob:nth-child(3) {
    width: 500px; height: 500px; background: var(--cyan);
    filter: blur(120px);
    bottom: -8%; left: 25%; opacity: 0.14;
    animation: float3 18s ease-in-out infinite alternate;
  }
  .aurora-bg .blob:nth-child(4) {
    width: 400px; height: 400px; background: var(--lime);
    filter: blur(90px);
    top: 55%; left: 8%; opacity: 0.12;
    animation: float4 13s ease-in-out infinite alternate;
  }
  .aurora-bg .blob:nth-child(5) {
    width: 450px; height: 450px; background: var(--purple);
    filter: blur(100px);
    bottom: 10%; right: 5%; opacity: 0.10;
    animation: float5 15s ease-in-out infinite alternate;
  }

  @keyframes float1 {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(50px, 40px) scale(1.15); }
  }
  @keyframes float2 {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(-40px, 50px) scale(1.1); }
  }
  @keyframes float3 {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(30px, -40px) scale(1.12); }
  }
  @keyframes float4 {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(-30px, -30px) scale(1.18); }
  }
  @keyframes float5 {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(40px, 20px) scale(1.08); }
  }

  .container {
    position: relative; z-index: 10;
    max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem 4rem;
  }

  /* Hero Header */
  .hero {
    text-align: center; padding: 3rem 0 2rem;
  }
  .hero h1 {
    font-size: 2.6rem; font-weight: 700; line-height: 1.2;
    background: linear-gradient(135deg, var(--purple), var(--teal), var(--cyan));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.75rem;
  }
  .hero .subtitle {
    font-family: 'Space Mono', monospace; font-size: 0.85rem;
    color: var(--purple); letter-spacing: 0.05em; text-transform: uppercase;
    opacity: 0.7;
  }

  /* Tab navigation */
  .tabs {
    display: flex; gap: 0.5rem; justify-content: center;
    margin-bottom: 2rem; flex-wrap: wrap;
  }
  .tab-btn {
    font-family: 'Space Mono', monospace; font-size: 0.8rem;
    padding: 0.65rem 1.5rem; border-radius: 999px;
    border: 1px solid rgba(124,58,237,0.15);
    background: rgba(255,255,255,0.5); color: var(--text-light);
    cursor: pointer; transition: all 0.3s; backdrop-filter: blur(12px);
    letter-spacing: 0.04em; text-transform: uppercase;
  }
  .tab-btn:hover { background: rgba(255,255,255,0.8); color: var(--text); }
  .tab-btn.active {
    background: linear-gradient(135deg, var(--purple), var(--teal));
    color: #fff; border-color: transparent; font-weight: 700;
  }

  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Glassmorphism card */
  .glass-card {
    background: var(--card-bg); backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--card-border); border-radius: var(--radius);
    box-shadow: var(--card-shadow); padding: 2rem; margin-bottom: 1.5rem;
  }

  .glass-card h2 {
    font-size: 1.4rem; font-weight: 700; margin-bottom: 1rem;
    background: linear-gradient(135deg, var(--purple), var(--teal));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .glass-card h3 {
    font-size: 1.1rem; font-weight: 600; color: var(--text);
    margin: 1.25rem 0 0.5rem; display: flex; align-items: center; gap: 0.5rem;
  }
  .glass-card h3 .badge {
    font-family: 'Space Mono', monospace; font-size: 0.65rem;
    background: linear-gradient(135deg, var(--purple), var(--teal));
    color: #fff; padding: 0.15rem 0.6rem; border-radius: 999px;
    text-transform: uppercase; letter-spacing: 0.05em;
  }

  .glass-card p, .glass-card li {
    font-size: 0.92rem; line-height: 1.65; color: var(--text-light);
  }
  .glass-card ul, .glass-card ol {
    padding-left: 1.25rem; margin: 0.5rem 0;
  }
  .glass-card li { margin-bottom: 0.35rem; }

  /* Diagram container for Mermaid */
  .diagram-container {
    margin: 1.5rem 0; text-align: center;
    overflow-x: auto; -webkit-overflow-scrolling: touch;
  }
  .diagram-container .mermaid {
    display: inline-block; text-align: center;
  }
  .diagram-container .mermaid svg {
    height: auto;
  }
  /* AS-IS and TO-BE sequence diagrams — render large */
  .diagram-large .mermaid svg {
    min-width: 900px;
  }

  /* Tags */
  .tag-list { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
  .tag {
    font-family: 'Space Mono', monospace; font-size: 0.72rem;
    padding: 0.25rem 0.75rem; border-radius: 999px;
    border: 1px solid rgba(124,58,237,0.25);
    background: rgba(124,58,237,0.06); color: var(--purple);
    letter-spacing: 0.03em;
  }
  .tag.teal { border-color: rgba(45,212,191,0.3); background: rgba(45,212,191,0.08); color: #0d9488; }
  .tag.cyan { border-color: rgba(103,232,249,0.3); background: rgba(103,232,249,0.08); color: #0891b2; }
  .tag.lime { border-color: rgba(190,242,100,0.3); background: rgba(190,242,100,0.1); color: #4d7c0f; }

  /* Steps table */
  .steps-table { width: 100%; border-collapse: separate; border-spacing: 0; margin: 1rem 0; }
  .steps-table th {
    font-family: 'Space Mono', monospace; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.06em;
    background: rgba(124,58,237,0.06); color: var(--purple);
    padding: 0.6rem 1rem; text-align: left;
  }
  .steps-table th:first-child { border-radius: 0.75rem 0 0 0; }
  .steps-table th:last-child { border-radius: 0 0.75rem 0 0; }
  .steps-table td {
    padding: 0.6rem 1rem; font-size: 0.88rem; color: var(--text-light);
    border-bottom: 1px solid rgba(124,58,237,0.06);
  }

  /* Gherkin */
  .gherkin {
    background: rgba(124,58,237,0.03); border-radius: 0.75rem;
    padding: 1rem 1.25rem; margin: 0.5rem 0;
    font-family: 'Space Mono', monospace; font-size: 0.8rem;
    line-height: 1.7; color: var(--text);
  }
  .gherkin .keyword { color: var(--purple); font-weight: 700; }

  /* Architecture grid */
  .arch-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1rem;
  }
  @media (max-width: 768px) { .arch-grid { grid-template-columns: 1fr; } }

  .arch-section-title {
    font-family: 'Space Mono', monospace; font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.75rem; padding-bottom: 0.4rem;
    border-bottom: 2px solid;
  }
  .arch-section-title.ai { color: var(--purple); border-color: var(--purple); }
  .arch-section-title.svc { color: #0d9488; border-color: var(--teal); }
  .arch-section-title.data { color: #0891b2; border-color: var(--cyan); }
  .arch-section-title.infra { color: #4d7c0f; border-color: var(--lime); }

  .arch-item { margin-bottom: 0.75rem; }
  .arch-item-name {
    font-weight: 600; font-size: 0.9rem; color: var(--text);
  }
  .arch-item-desc {
    font-size: 0.82rem; color: var(--text-light); margin-top: 0.15rem;
  }

  /* Feature cards */
  .feature-card {
    background: rgba(255,255,255,0.45); backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--card-border); border-radius: var(--radius);
    box-shadow: var(--card-shadow);
    padding: 1.75rem; margin-bottom: 1.5rem;
  }
  .feature-card h3 {
    font-size: 1.15rem; color: var(--text); margin: 0 0 0.5rem;
  }

  /* User story box */
  .user-story {
    background: linear-gradient(135deg, rgba(124,58,237,0.06), rgba(45,212,191,0.06));
    border-left: 3px solid var(--purple);
    border-radius: 0 0.75rem 0.75rem 0;
    padding: 1rem 1.25rem; margin: 0.75rem 0;
    font-style: italic; font-size: 0.9rem; color: var(--text);
    line-height: 1.6;
  }

  /* Requirements */
  .req-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 0.75rem; }
  @media (max-width: 768px) { .req-grid { grid-template-columns: 1fr; } }
  .req-item {
    display: flex; gap: 0.5rem; font-size: 0.85rem; color: var(--text-light);
    margin-bottom: 0.4rem;
  }
  .req-item .req-id {
    font-family: 'Space Mono', monospace; font-size: 0.72rem;
    color: var(--purple); font-weight: 700; min-width: 50px;
  }

  /* Metrics highlight */
  .metrics-grid { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.75rem 0; }
  .metric-badge {
    background: linear-gradient(135deg, rgba(190,242,100,0.15), rgba(45,212,191,0.1));
    border: 1px solid rgba(190,242,100,0.3); border-radius: 0.75rem;
    padding: 0.5rem 1rem; font-size: 0.82rem; color: var(--text);
  }

  /* Workplan — expandable tasks */
  .wp-task {
    background: var(--card-bg); backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--card-border); border-radius: var(--radius);
    box-shadow: var(--card-shadow); margin-bottom: 1rem;
    overflow: hidden;
  }
  .wp-task-header {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 1.25rem 1.5rem; cursor: pointer;
    transition: background 0.2s;
  }
  .wp-task-header:hover { background: rgba(124,58,237,0.03); }
  .wp-task-toggle {
    width: 24px; height: 24px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    border-radius: 6px; background: rgba(124,58,237,0.08);
    color: var(--purple); font-size: 0.85rem; font-weight: 700;
    transition: transform 0.25s;
  }
  .wp-task.open .wp-task-toggle { transform: rotate(90deg); }
  .wp-task-info { flex: 1; min-width: 0; }
  .wp-task-name {
    font-weight: 600; font-size: 1rem; color: var(--text);
    margin-bottom: 0.2rem;
  }
  .wp-task-desc {
    font-size: 0.85rem; color: var(--text-light); line-height: 1.5;
    font-style: italic;
  }
  .wp-id {
    font-family: 'Space Mono', monospace; font-size: 0.75rem;
    color: var(--purple); font-weight: 700; margin-right: 0.3rem;
  }
  .wp-task-badge {
    font-family: 'Space Mono', monospace; font-size: 0.68rem;
    background: rgba(124,58,237,0.08); color: var(--purple);
    padding: 0.2rem 0.6rem; border-radius: 999px; flex-shrink: 0;
    letter-spacing: 0.03em;
  }
  .wp-task-body {
    max-height: 0; overflow: hidden;
    transition: max-height 0.35s ease;
  }
  .wp-task.open .wp-task-body { max-height: 2000px; }
  .wp-subtasks {
    padding: 0 1.5rem 1.25rem; border-top: 1px solid rgba(124,58,237,0.06);
  }
  .wp-subtask {
    padding: 1rem 0;
    border-bottom: 1px solid rgba(124,58,237,0.05);
  }
  .wp-subtask:last-child { border-bottom: none; }
  .wp-subtask-name {
    font-weight: 500; font-size: 0.92rem; color: var(--text);
    margin-bottom: 0.3rem;
  }
  .wp-subtask-desc {
    font-size: 0.85rem; color: var(--text-light); line-height: 1.5;
    margin-bottom: 0.5rem;
  }
  .wp-ac-label {
    font-family: 'Space Mono', monospace; font-size: 0.68rem;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #0d9488; margin-bottom: 0.3rem;
  }
  .wp-ac-list {
    list-style: none; padding: 0; margin: 0;
  }
  .wp-ac-list li {
    font-size: 0.82rem; color: var(--text-light); line-height: 1.6;
    padding-left: 1.2rem; position: relative;
  }
  .wp-ac-list li::before {
    content: "\2713"; position: absolute; left: 0;
    color: var(--teal); font-weight: 700;
  }

  .footer {
    text-align: center; padding: 3rem 0 1rem;
    font-family: 'Space Mono', monospace; font-size: 0.72rem;
    color: var(--text-light); letter-spacing: 0.06em; opacity: 0.4;
  }
</style>
</head>
<body>

<div class="aurora-bg">
  <div class="blob"></div><div class="blob"></div><div class="blob"></div><div class="blob"></div><div class="blob"></div>
</div>

<div class="container">

<div class="hero">
  <h1>{{ process_title }}</h1>
  <div class="subtitle">Process-to-Agent Transformation Report</div>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('asis')">AS-IS</button>
  <button class="tab-btn" onclick="switchTab('tobe')">TO-BE</button>
  <button class="tab-btn" onclick="switchTab('prd')">PRD</button>
  <button class="tab-btn" onclick="switchTab('arch')">Architecture</button>
  <button class="tab-btn" onclick="switchTab('workplan')">Workplan</button>
</div>

<!-- ==================== AS-IS TAB ==================== -->
<div id="tab-asis" class="tab-content active">

  <div class="glass-card">
    <h2>AS-IS Process Analysis</h2>

    {% if asis.mermaid_source %}
    <div class="diagram-container diagram-large">
      <pre class="mermaid">{{ asis.mermaid_source }}</pre>
    </div>
    {% endif %}

    <h3>Goal</h3>
    <p>{{ asis.goal }}</p>

    <h3>Summary</h3>
    <p>{{ asis.summary }}</p>
  </div>

  <div class="glass-card">
    <h3>Process Steps</h3>
    <table class="steps-table">
      <thead>
        <tr><th>#</th><th>Step</th><th>Description</th><th>Artifact</th><th>Actor</th></tr>
      </thead>
      <tbody>
        {% for step in asis.steps %}
        <tr>
          <td>{{ step.number }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.name }}</td>
          <td>{{ step.description }}</td>
          <td>{{ step.artifact }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.actor }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  {% if asis.automation_opportunities %}
  <div class="glass-card">
    <h3>Potential Automation Points</h3>
    <ul>
      {% for opp in asis.automation_opportunities %}<li>{{ opp }}</li>{% endfor %}
    </ul>
  </div>
  {% endif %}

  <div class="glass-card">
    <h3>Roles</h3>
    <div class="tag-list">
      {% for role in asis.roles %}<span class="tag">{{ role }}</span>{% endfor %}
    </div>

    <h3>Systems</h3>
    <div class="tag-list">
      {% for sys in asis.systems %}<span class="tag teal">{{ sys }}</span>{% endfor %}
    </div>

    <h3>Current Metrics</h3>
    <div class="metrics-grid">
      {% for m in asis.metrics %}<div class="metric-badge">{{ m }}</div>{% endfor %}
    </div>
  </div>

</div>

<!-- ==================== TO-BE TAB ==================== -->
<div id="tab-tobe" class="tab-content">

  <div class="glass-card">
    <h2>TO-BE Process with AI Agent</h2>

    {% if tobe.mermaid_source %}
    <div class="diagram-container diagram-large">
      <pre class="mermaid">{{ tobe.mermaid_source }}</pre>
    </div>
    {% endif %}

    <h3>Goal</h3>
    <p>{{ tobe.goal }}</p>

    <h3>Summary</h3>
    <p>{{ tobe.summary }}</p>
  </div>

  <div class="glass-card">
    <h3>Updated Process Steps</h3>
    <table class="steps-table">
      <thead>
        <tr><th>#</th><th>Step</th><th>Description</th><th>Artifact</th><th>Actor</th></tr>
      </thead>
      <tbody>
        {% for step in tobe.steps %}
        <tr>
          <td>{{ step.number }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.name }}</td>
          <td>{{ step.description }}</td>
          <td>{{ step.artifact }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.actor }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="glass-card">
    <h3>Roles</h3>
    <div class="tag-list">
      {% for role in tobe.roles %}<span class="tag">{{ role }}</span>{% endfor %}
    </div>

    <h3><span class="badge">AI Agent</span> Agent Responsibilities</h3>
    <ul>
      {% for r in tobe.agent_responsibilities %}<li>{{ r }}</li>{% endfor %}
    </ul>

    <h3>Human Responsibilities</h3>
    <ul>
      {% for r in tobe.human_responsibilities %}<li>{{ r }}</li>{% endfor %}
    </ul>

    <h3>Expected Improvements</h3>
    <div class="metrics-grid">
      {% for m in tobe.metrics %}<div class="metric-badge">{{ m }}</div>{% endfor %}
    </div>
  </div>

  {% if human_role %}
  <div class="glass-card">
    <h3>Future Human Role: {{ human_role.role_name }}</h3>
    {% if human_role.mermaid_source %}
    <div class="diagram-container">
      <pre class="mermaid">{{ human_role.mermaid_source }}</pre>
    </div>
    {% endif %}
    <ul>
      {% for r in human_role.responsibilities %}<li>{{ r }}</li>{% endfor %}
    </ul>
  </div>
  {% endif %}

</div>

<!-- ==================== PRD TAB ==================== -->
<div id="tab-prd" class="tab-content">

  <!-- Agent Graph -->
  <div class="glass-card">
    <h2>AI Agent Definition</h2>

    {% if agent.skill_graph_mermaid_source %}
    <div class="diagram-container diagram-large">
      <pre class="mermaid">{{ agent.skill_graph_mermaid_source }}</pre>
    </div>
    {% endif %}

    <h3>Agent Name</h3>
    <p style="font-weight:600;color:var(--purple);font-size:1.1rem">{{ agent.agent_name }}</p>

    <h3>Primary User</h3>
    <p>{{ agent.user }}</p>

    <h3>Problem</h3>
    <p>{{ agent.problem }}</p>

    <h3>Solution</h3>
    <p>{{ agent.solution }}</p>

    <h3>Agent Skills</h3>
    <div class="tag-list">
      {% for skill in agent.skills %}
      <span class="tag teal">{{ skill.name }}</span>
      {% endfor %}
    </div>
  </div>

  <!-- PRD Summary -->
  <div class="glass-card">
    <h2>Product Requirements</h2>
    <p>{{ prd.summary }}</p>

    <h3>Success Metrics</h3>
    <div class="metrics-grid">
      {% for m in prd.success_metrics %}<div class="metric-badge">{{ m }}</div>{% endfor %}
    </div>
  </div>

  <!-- Features -->
  {% for feature in prd.features %}
  <div class="feature-card">
    <h3>
      <span class="badge">Feature {{ loop.index }}</span>
      {{ feature.feature_name }}
    </h3>
    <div class="tag-list" style="margin-bottom:0.75rem">
      <span class="tag teal">Skill: {{ feature.skill_mapping }}</span>
    </div>
    <p>{{ feature.description }}</p>

    <h3>User Story</h3>
    <div class="user-story">{{ feature.user_story }}</div>

    {% if feature.user_flow and feature.user_flow.mermaid_source %}
    <h3>User Flow</h3>
    <div class="diagram-container">
      <pre class="mermaid">{{ feature.user_flow.mermaid_source }}</pre>
    </div>
    {% endif %}

    {% if feature.use_cases %}
    <h3>Use Cases</h3>
    {% for uc in feature.use_cases %}
    <div class="gherkin">
      <span class="keyword">Given</span> {{ uc.given }}<br>
      <span class="keyword">When</span> {{ uc.when }}<br>
      <span class="keyword">Then</span> {{ uc.then }}
    </div>
    {% endfor %}
    {% endif %}

    {% if feature.functional_requirements or feature.non_functional_requirements %}
    <h3>Requirements</h3>
    <div class="req-grid">
      <div>
        <div style="font-family:'Space Mono',monospace;font-size:0.72rem;color:var(--purple);margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.06em">Functional</div>
        {% for fr in feature.functional_requirements %}
        <div class="req-item"><span class="req-id">{{ fr.id }}</span> {{ fr.description }}</div>
        {% endfor %}
      </div>
      <div>
        <div style="font-family:'Space Mono',monospace;font-size:0.72rem;color:#0891b2;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.06em">Non-Functional</div>
        {% for nfr in feature.non_functional_requirements %}
        <div class="req-item"><span class="req-id" style="color:#0891b2">{{ nfr.id }}</span> {{ nfr.description }}</div>
        {% endfor %}
      </div>
    </div>
    {% endif %}
  </div>
  {% endfor %}

</div>

<!-- ==================== ARCHITECTURE TAB ==================== -->
<div id="tab-arch" class="tab-content">

  <div class="glass-card">
    <h2>System Architecture</h2>

    {% if architecture.mermaid_source %}
    <div class="diagram-container diagram-large">
      <pre class="mermaid">{{ architecture.mermaid_source }}</pre>
    </div>
    {% endif %}

    {% if architecture.summary %}
    <h3>Overview</h3>
    <p>{{ architecture.summary }}</p>
    {% endif %}

    <div class="arch-grid">
      <!-- AI Services -->
      <div>
        <div class="arch-section-title ai">AI Services</div>
        {% for svc in architecture.ai_services %}
        <div class="arch-item">
          <div class="arch-item-name">{{ svc.name }}</div>
          <div class="arch-item-desc">{{ svc.description }}</div>
        </div>
        {% endfor %}
      </div>

      <!-- Services -->
      <div>
        <div class="arch-section-title svc">Services</div>
        {% for svc in architecture.services %}
        <div class="arch-item">
          <div class="arch-item-name">{{ svc.name }}</div>
          <div class="arch-item-desc">{{ svc.description }}</div>
        </div>
        {% endfor %}
      </div>

      <!-- Data -->
      <div>
        <div class="arch-section-title data">Data</div>
        {% for d in architecture.data %}
        <div class="arch-item">
          <div class="arch-item-name">{{ d.name }}</div>
          <div class="arch-item-desc">{{ d.description }}</div>
        </div>
        {% endfor %}
      </div>

      <!-- Infrastructure -->
      <div>
        <div class="arch-section-title infra">Infrastructure</div>
        {% for inf in architecture.infrastructure %}
        <div class="arch-item">
          <div class="arch-item-name">{{ inf.name }}</div>
          <div class="arch-item-desc">{{ inf.description }}</div>
        </div>
        {% endfor %}
      </div>
    </div>
  </div>

</div>

<!-- ==================== WORKPLAN TAB ==================== -->
<div id="tab-workplan" class="tab-content">

  <div class="glass-card">
    <h2>Implementation Workplan</h2>
    <p style="color:var(--text-light);font-size:0.9rem;margin-bottom:0.5rem">Click on a task to expand subtasks and acceptance criteria.</p>
  </div>

  {% for task in workplan.tasks %}
  <div class="wp-task" onclick="this.classList.toggle('open')">
    <div class="wp-task-header">
      <div class="wp-task-toggle">&#9654;</div>
      <div class="wp-task-info">
        <div class="wp-task-name">{% if task.id %}<span class="wp-id">{{ task.id }}</span> {% endif %}{{ task.task_name }}</div>
        <div class="wp-task-desc">{{ task.description }}</div>
      </div>
      <div class="wp-task-badge">{{ task.subtasks|length }} subtasks</div>
    </div>
    <div class="wp-task-body">
      <div class="wp-subtasks">
        {% for sub in task.subtasks %}
        <div class="wp-subtask">
          <div class="wp-subtask-name">{% if sub.id %}<span class="wp-id">{{ sub.id }}</span> {% endif %}{{ sub.name }}</div>
          <div class="wp-subtask-desc">{{ sub.description }}</div>
          {% if sub.acceptance_criteria %}
          <div class="wp-ac-label">Acceptance Criteria</div>
          <ul class="wp-ac-list">
            {% for ac in sub.acceptance_criteria %}<li>{{ ac }}</li>{% endfor %}
          </ul>
          {% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
  </div>
  {% endfor %}

</div>

<div class="footer">Process-to-Agent Analysis Report &bull; Generated by AI</div>

</div><!-- /container -->

<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

// Render ALL mermaid diagrams on page load, including those in hidden tabs.
// Mermaid cannot measure elements inside display:none containers, so we
// briefly make every tab visible, run mermaid, then restore visibility.
document.addEventListener('DOMContentLoaded', async function() {
  var tabs = document.querySelectorAll('.tab-content');
  // Show all tabs
  tabs.forEach(function(t) { t.style.display = 'block'; });
  // Render all diagrams
  await mermaid.run({ querySelector: '.mermaid' });
  // Restore: hide all, then show only the active one
  tabs.forEach(function(t) { t.style.display = ''; });
});

function switchTab(id) {
  document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
  document.getElementById('tab-' + id).classList.add('active');
  event.target.classList.add('active');
}
</script>
</body>
</html>"""


def generate_html_report(analysis: ProcessAnalysis) -> tuple[str, str]:
    """Generate the HTML report file. Returns (file_path, public_url)."""
    report_id = uuid.uuid4().hex[:12]
    filename = f"report_{report_id}.html"
    filepath = REPORTS_DIR / filename

    context = _prepare_context(analysis)
    template = Template(REPORT_TEMPLATE)
    html = template.render(**context)

    filepath.write_text(html, encoding="utf-8")
    url = f"{REPORT_BASE_URL}/reports/{filename}"

    logger.info("Generated HTML report: %s", filepath)
    return str(filepath), url
