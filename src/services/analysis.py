"""Process analysis using OpenAI — generates the full structured analysis."""

import json
import logging
from openai import AsyncOpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.models.schemas import ProcessAnalysis

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert business process analyst and AI transformation architect.
You receive a description of a business process and produce a comprehensive structured analysis.

You MUST output valid JSON matching the exact schema below. Do not include any text outside the JSON.
All output must be in English regardless of input language.

Required JSON schema:
{
  "process_title": "string — concise process name",
  "asis": {
    "goal": "string",
    "summary": "string — 2-3 sentence summary",
    "roles": ["string"],
    "systems": ["string"],
    "steps": [{"number": 1, "name": "string", "description": "string", "actor": "string"}],
    "metrics": ["string"],
    "mermaid_source": "string — valid Mermaid sequenceDiagram code for the AS-IS process"
  },
  "automation": {
    "items": [{"function_name": "string", "description": "string", "rationale": "string"}]
  },
  "tobe": {
    "goal": "string",
    "summary": "string",
    "roles": ["string"],
    "steps": [{"number": 1, "name": "string", "description": "string", "actor": "string"}],
    "agent_responsibilities": ["string"],
    "human_responsibilities": ["string"],
    "metrics": ["string"],
    "mermaid_source": "string — valid Mermaid sequenceDiagram code for the TO-BE process showing AI Agent"
  },
  "human_role": {
    "role_name": "string",
    "responsibilities": ["string"],
    "mermaid_source": "string — valid Mermaid flowchart TD showing future human responsibilities"
  },
  "agent": {
    "agent_name": "string",
    "user": "string — primary user of the agent",
    "problem": "string",
    "solution": "string",
    "skills": [{"name": "string", "description": "string"}],
    "skill_graph_mermaid_source": "string — valid Mermaid graph TD showing agent skills"
  },
  "prd": {
    "summary": "string",
    "success_metrics": ["string"],
    "features": [
      {
        "feature_name": "string",
        "skill_mapping": "string — which agent skill this maps to",
        "description": "string",
        "user_story": "string — As a {user}, I want {action}, So that {value}",
        "user_flow": {
          "description": "string",
          "mermaid_source": "string — valid Mermaid flowchart for this feature's user flow"
        },
        "use_cases": [{"given": "string", "when": "string", "then": "string"}],
        "functional_requirements": [{"id": "FR-X", "description": "string"}],
        "non_functional_requirements": [{"id": "NFR-X", "description": "string"}]
      }
    ]
  },
  "architecture": {
    "summary": "string — 3-5 sentence detailed description of the overall system architecture, explaining how components interact",
    "mermaid_source": "string — valid Mermaid flowchart TD showing the high-level architecture with all layers and connections",
    "ai_services": [{"name": "string", "description": "string — detailed description of the AI service, its purpose, input/output, and integration points"}],
    "services": [{"name": "string", "description": "string — detailed description of the service, protocols, APIs exposed"}],
    "data": [{"name": "string", "description": "string — detailed description of the data store, schema highlights, access patterns"}],
    "infrastructure": [{"name": "string", "description": "string — detailed description of the infrastructure component, scaling strategy, deployment"}]
  },
  "telegram_summary": {
    "process_title": "string",
    "description": "string — short process summary",
    "automated_by_agent": "string — concise summary of what agent automates",
    "human_responsibilities": "string — concise summary of what human does"
  }
}

IMPORTANT Mermaid rules for AS-IS and TO-BE diagrams (sequenceDiagram):
- Use sequenceDiagram syntax with autonumber
- Group participants with box rgb(...) ... end
- Use rect rgb(...) ... end to group logical phases
- Use note right of PARTICIPANT: to add context annotations
- Each note should contain phase name and key pain points or risks separated by pipe |
- Number steps in notes: "1. Step name"
- Use participant aliases for readability: participant CO as Coordinator
- Use opt, alt/else, loop blocks for conditional flows
- Use ->> for synchronous calls, -->> for responses
- The TO-BE diagram MUST include an AI_AGENT participant and show which steps are automated

IMPORTANT Mermaid rules for other diagrams (flowchart/graph):
- Use flowchart TD (top-down) syntax
- Use simple node IDs like A, B, C or A1, A2 etc.
- Always quote node labels: A["Label text"]
- Do NOT use special characters like parentheses, colons, or quotes inside node labels
- Keep diagrams readable with 5-15 nodes max
- Use standard arrow syntax: A --> B or A -->|"label"| B
- Do NOT use subgraph unless necessary
- Ensure each mermaid_source field starts with "flowchart TD" or "graph TD"

IMPORTANT architecture diagram rules:
- The architecture mermaid_source must be a flowchart TD
- Use subgraph blocks to group layers: Client, API Gateway, Services, AI Services, Data, Infrastructure
- Show connections between components with labeled arrows
- Keep it comprehensive but readable

IMPORTANT telegram_summary rules:
- The combined text of process_title + description + automated_by_agent + human_responsibilities must be under 800 characters total
- Be concise and executive-friendly

Generate 1 skill per agent skill, and 1 feature per skill in the PRD.
Generate at least 3 skills and features.
Make the analysis thorough, realistic, and actionable."""

USER_PROMPT_TEMPLATE = """Analyze the following business process description and produce the full structured JSON analysis.

Process Description:
{input_text}"""


async def analyze_process(input_text: str, input_type: str = "text") -> ProcessAnalysis:
    """Run the full process analysis via OpenAI and return structured data."""
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    logger.info("Starting process analysis with model %s", OPENAI_MODEL)

    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(input_text=input_text)},
        ],
        temperature=0.4,
        max_completion_tokens=16000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    logger.info("Received analysis response: %d characters", len(raw))

    data = json.loads(raw)
    data["input_text"] = input_text
    data["input_type"] = input_type

    analysis = ProcessAnalysis(**data)
    logger.info("Process analysis parsed successfully: %s", analysis.process_title)
    return analysis
