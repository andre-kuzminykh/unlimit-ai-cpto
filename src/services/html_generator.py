"""HTML report generator using Jinja2 with Glassmorphism + Aurora UI."""

from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path

from jinja2 import Template

from src.config import REPORTS_DIR, REPORT_BASE_URL
from src.models.schemas import ProcessAnalysis

logger = logging.getLogger(__name__)


def _image_to_data_uri(image_path: str | None) -> str | None:
    """Convert an image file to a base64 data URI for embedding in HTML."""
    if not image_path:
        return None
    p = Path(image_path)
    if not p.exists():
        return None
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _prepare_context(analysis: ProcessAnalysis) -> dict:
    """Build Jinja2 template context from the analysis, embedding images as data URIs."""
    ctx = analysis.model_dump()

    # Convert all image paths to data URIs
    for section in ["asis", "tobe", "human_role", "agent"]:
        img = ctx[section].get("image_path")
        ctx[section]["image_data_uri"] = _image_to_data_uri(img)

    for i, feature in enumerate(ctx["prd"]["features"]):
        uf = feature.get("user_flow", {})
        img = uf.get("image_path") if uf else None
        if uf:
            uf["image_data_uri"] = _image_to_data_uri(img)

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
    --card-border: rgba(255,255,255,0.6);
    --card-shadow: 0 8px 32px rgba(124,58,237,0.10);
    --radius: 1.5rem;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', system-ui, sans-serif;
    background: #0f0b1a;
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Aurora background */
  .aurora-bg {
    position: fixed; inset: 0; z-index: 0; overflow: hidden;
  }
  .aurora-bg .blob {
    position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.45;
    animation: aurora-drift 12s ease-in-out infinite alternate;
  }
  .aurora-bg .blob:nth-child(1) {
    width: 600px; height: 600px; background: var(--purple);
    top: -10%; left: -5%;
  }
  .aurora-bg .blob:nth-child(2) {
    width: 500px; height: 500px; background: var(--teal);
    top: 30%; right: -10%; animation-delay: -4s;
  }
  .aurora-bg .blob:nth-child(3) {
    width: 450px; height: 450px; background: var(--cyan);
    bottom: -5%; left: 30%; animation-delay: -8s;
  }
  .aurora-bg .blob:nth-child(4) {
    width: 350px; height: 350px; background: var(--lime);
    top: 50%; left: 10%; animation-delay: -6s; opacity: 0.25;
  }

  @keyframes aurora-drift {
    0% { transform: translate(0, 0) scale(1); }
    100% { transform: translate(40px, 30px) scale(1.12); }
  }

  .container {
    position: relative; z-index: 1;
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
    color: var(--teal); letter-spacing: 0.05em; text-transform: uppercase;
  }

  /* Tab navigation */
  .tabs {
    display: flex; gap: 0.5rem; justify-content: center;
    margin-bottom: 2rem; flex-wrap: wrap;
  }
  .tab-btn {
    font-family: 'Space Mono', monospace; font-size: 0.8rem;
    padding: 0.65rem 1.5rem; border-radius: 999px; border: 1px solid var(--card-border);
    background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.7);
    cursor: pointer; transition: all 0.3s; backdrop-filter: blur(12px);
    letter-spacing: 0.04em; text-transform: uppercase;
  }
  .tab-btn:hover { background: rgba(255,255,255,0.2); color: #fff; }
  .tab-btn.active {
    background: linear-gradient(135deg, var(--purple), var(--teal));
    color: #fff; border-color: transparent; font-weight: 700;
  }

  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Glassmorphism card */
  .glass-card {
    background: var(--card-bg); backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
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

  .diagram-container {
    margin: 1.5rem 0; text-align: center;
  }
  .diagram-container img {
    max-width: 100%; height: auto; border-radius: 1rem;
    border: 1px solid var(--card-border);
    box-shadow: 0 4px 24px rgba(124,58,237,0.08);
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
    background: rgba(15,23,42,0.04); border-radius: 0.75rem;
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
    background: rgba(255,255,255,0.35); backdrop-filter: blur(16px);
    border: 1px solid var(--card-border); border-radius: var(--radius);
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

  .footer {
    text-align: center; padding: 3rem 0 1rem;
    font-family: 'Space Mono', monospace; font-size: 0.72rem;
    color: rgba(255,255,255,0.3); letter-spacing: 0.06em;
  }
</style>
</head>
<body>

<div class="aurora-bg">
  <div class="blob"></div><div class="blob"></div><div class="blob"></div><div class="blob"></div>
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
</div>

<!-- ==================== AS-IS TAB ==================== -->
<div id="tab-asis" class="tab-content active">

  <div class="glass-card">
    <h2>AS-IS Process Analysis</h2>

    {% if asis.image_data_uri %}
    <div class="diagram-container">
      <img src="{{ asis.image_data_uri }}" alt="AS-IS Process Diagram">
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
        <tr><th>#</th><th>Step</th><th>Description</th><th>Actor</th></tr>
      </thead>
      <tbody>
        {% for step in asis.steps %}
        <tr>
          <td>{{ step.number }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.name }}</td>
          <td>{{ step.description }}</td>
          <td><span class="tag">{{ step.actor }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

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

    {% if tobe.image_data_uri %}
    <div class="diagram-container">
      <img src="{{ tobe.image_data_uri }}" alt="TO-BE Process Diagram">
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
        <tr><th>#</th><th>Step</th><th>Description</th><th>Actor</th></tr>
      </thead>
      <tbody>
        {% for step in tobe.steps %}
        <tr>
          <td>{{ step.number }}</td>
          <td style="font-weight:500;color:var(--text)">{{ step.name }}</td>
          <td>{{ step.description }}</td>
          <td><span class="tag {% if 'Agent' in step.actor or 'AI' in step.actor %}teal{% endif %}">{{ step.actor }}</span></td>
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
    {% if human_role.image_data_uri %}
    <div class="diagram-container">
      <img src="{{ human_role.image_data_uri }}" alt="Future Human Role Diagram">
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

    {% if agent.image_data_uri %}
    <div class="diagram-container">
      <img src="{{ agent.image_data_uri }}" alt="Agent Skill Graph">
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

    {% if feature.user_flow and feature.user_flow.image_data_uri %}
    <h3>User Flow</h3>
    <div class="diagram-container">
      <img src="{{ feature.user_flow.image_data_uri }}" alt="Feature {{ loop.index }} User Flow">
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

<div class="footer">Process-to-Agent Analysis Report &bull; Generated by AI</div>

</div><!-- /container -->

<script>
function switchTab(id) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
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
