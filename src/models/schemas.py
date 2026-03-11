"""Pydantic models for the process analysis data structures."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class Step(BaseModel):
    number: int
    name: str
    description: str
    actor: str


class AsIs(BaseModel):
    goal: str
    summary: str
    roles: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    mermaid_source: str = ""
    image_path: Optional[str] = None


class AutomationItem(BaseModel):
    function_name: str
    description: str
    rationale: str


class Automation(BaseModel):
    items: list[AutomationItem] = Field(default_factory=list)


class ToBe(BaseModel):
    goal: str
    summary: str
    roles: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    agent_responsibilities: list[str] = Field(default_factory=list)
    human_responsibilities: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    mermaid_source: str = ""
    image_path: Optional[str] = None


class HumanRole(BaseModel):
    role_name: str
    responsibilities: list[str] = Field(default_factory=list)
    mermaid_source: str = ""
    image_path: Optional[str] = None


class AgentSkill(BaseModel):
    name: str
    description: str


class Agent(BaseModel):
    agent_name: str
    user: str
    problem: str
    solution: str
    skills: list[AgentSkill] = Field(default_factory=list)
    skill_graph_mermaid_source: str = ""
    image_path: Optional[str] = None


class FunctionalRequirement(BaseModel):
    id: str
    description: str


class NonFunctionalRequirement(BaseModel):
    id: str
    description: str


class UseCase(BaseModel):
    given: str
    when: str
    then: str


class FeatureUserFlow(BaseModel):
    description: str
    mermaid_source: str = ""
    image_path: Optional[str] = None


class Feature(BaseModel):
    feature_name: str
    skill_mapping: str
    description: str
    user_story: str
    user_flow: FeatureUserFlow
    use_cases: list[UseCase] = Field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)


class PRD(BaseModel):
    summary: str
    success_metrics: list[str] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)


class AIService(BaseModel):
    name: str
    description: str


class Service(BaseModel):
    name: str
    description: str


class DataItem(BaseModel):
    name: str
    description: str


class InfrastructureItem(BaseModel):
    name: str
    description: str


class Architecture(BaseModel):
    ai_services: list[AIService] = Field(default_factory=list)
    services: list[Service] = Field(default_factory=list)
    data: list[DataItem] = Field(default_factory=list)
    infrastructure: list[InfrastructureItem] = Field(default_factory=list)


class TelegramSummary(BaseModel):
    process_title: str
    description: str
    automated_by_agent: str
    human_responsibilities: str


class ProcessAnalysis(BaseModel):
    process_title: str
    input_text: str
    input_type: str = "text"
    asis: AsIs
    automation: Automation
    tobe: ToBe
    human_role: HumanRole
    agent: Agent
    prd: PRD
    architecture: Architecture
    telegram_summary: TelegramSummary
    html_url: Optional[str] = None
