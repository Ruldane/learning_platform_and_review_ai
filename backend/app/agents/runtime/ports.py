"""Ports des agents regroupés (D82) : tout ce que le moteur emprunte aux features passe par un
seul objet, composé par `app.bootstrap.agent_ports` (le moteur n'importe aucune feature,
contrat 6). Un port de plus = un champ ici, avec sa valeur « non branché », et une ligne dans
`bootstrap.agent_ports`."""

from dataclasses import dataclass

from app.agents.tools.council_port import NO_COUNCIL, CouncilStore
from app.agents.tools.lesson_port import NO_LESSONS, LessonStore
from app.agents.tools.memory_port import NO_MEMORY, MemoryGateway
from app.agents.tools.program_port import NO_PROGRAM, ProgramStore
from app.agents.tools.web_port import NO_WEB, WebGateway


@dataclass(frozen=True)
class AgentPorts:
    memory: MemoryGateway = NO_MEMORY  # mémoire (D68)
    web: WebGateway = NO_WEB  # recherche web (D77)
    council: CouncilStore = NO_COUNCIL  # Conseil d'apprentissage (D84)
    program: ProgramStore = NO_PROGRAM  # programme du Stratège (D86)
    lessons: LessonStore = NO_LESSONS  # leçons du Rédacteur (D90)


NO_PORTS = AgentPorts()
