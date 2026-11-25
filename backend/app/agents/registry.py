"""Agent registry: a name (slug, same as the front's `agentColors.ts`) and a model tier. Each
agent's prompt is the file `prompts/<name>.md`. Filled by the graphs."""

from dataclasses import dataclass

from app.agents.tools.boss_port import BOSS_AGENT
from app.agents.tools.code_trial_port import DEFENDER, PROSECUTOR
from app.agents.tools.conversation_port import BRAIN_LIBRARIAN, LESSON_PROFESSOR, TRAINING_TUTOR
from app.core.errors import AppError
from app.providers.llm.base import Tier


@dataclass(frozen=True)
class AgentSpec:
    name: str
    tier: Tier


AGENTS: dict[str, AgentSpec] = {
    spec.name: spec
    for spec in (
        AgentSpec(name="demo_proponent", tier="fast"),  # Proponent of the `demo_debate` graph
        AgentSpec(name="demo_critic", tier="fast"),  # Critic of the `demo_debate` graph
        AgentSpec(name="archivist", tier="fast"),  # Archivist of the `learned_document` graph
        AgentSpec(name="scout", tier="fast"),  # Scout (`web_research`, Council)
        AgentSpec(name="moderator", tier="fast"),  # Council moderator
        AgentSpec(name="strategist", tier="strong"),  # Strategist: debate, proposals, program
        AgentSpec(name="practitioner", tier="standard"),  # Practitioner: voice of the field
        AgentSpec(name="skeptic", tier="standard"),  # Skeptic: objections, feasibility
        AgentSpec(name="scribe", tier="fast"),  # Scribe: board and minutes
        AgentSpec(name="writer", tier="strong"),  # Writer: a module's lesson
        AgentSpec(name="verifier", tier="standard"),  # Verifier: structure, facts, links
        AgentSpec(name="examiner", tier="standard"),  # Examiner: a module's quiz, grades
        AgentSpec(name="tutor", tier="standard"),  # Tutor: guided study sessions
        AgentSpec(name="analyst", tier="fast"),  # Analyst: posting analysis, gap
        AgentSpec(name="designer", tier="vision"),  # Designer: CV design (images)
        AgentSpec(name="ats_reader", tier="standard"),  # ATS reader: CV review (keywords)
        AgentSpec(name="recruiter", tier="standard"),  # Recruiter: CV review (impact)
        AgentSpec(name="tracker", tier="fast"),  # Tracking assistant: one-sentence record
        AgentSpec(name="interviewer", tier="strong"),  # Interviewer: mock interview, debrief
        AgentSpec(name="manager", tier="standard"),  # Hiring manager: hiring committee
        AgentSpec(name="colleague", tier="standard"),  # Future colleague: hiring committee
        # The IDE professor uses fast for hints and annotations and strong for explanations.
        # and proposals; exercise writer: standard
        AgentSpec(name="professor", tier="fast"),
        AgentSpec(name=LESSON_PROFESSOR, tier="fast"),
        AgentSpec(name=TRAINING_TUTOR, tier="fast"),
        AgentSpec(name=BRAIN_LIBRARIAN, tier="fast"),
        AgentSpec(name="exercise_writer", tier="standard"),
        AgentSpec(name=PROSECUTOR, tier="standard"),
        AgentSpec(name=DEFENDER, tier="standard"),
        AgentSpec(name=BOSS_AGENT, tier="standard"),
        AgentSpec(name="oncall_reviewer", tier="standard"),
        AgentSpec(name="podcast_host", tier="standard"),
    )
}


def get_agent(name: str) -> AgentSpec:
    spec = AGENTS.get(name)
    if spec is None:
        raise AppError("unknown_agent", f"Unknown agent: {name}", 404, {"agent": name})
    return spec
