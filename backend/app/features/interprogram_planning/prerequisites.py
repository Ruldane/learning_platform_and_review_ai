"""Comparaison sur les intitulés et compétences déclarés, sans inférer de nouveaux acquis."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from unicodedata import normalize

from app.db.models.program import Module, Task
from app.features.interprogram_planning.schemas import SharedModuleRef, SharedPrerequisite
from app.features.interprogram_planning.sources import WeekFacts
from app.features.program.service.programs import Loaded


def _key(text: str) -> str:
    return " ".join(normalize("NFKC", text).casefold().split())


@dataclass(frozen=True)
class ModuleWork:
    program: Loaded
    module: Module
    tasks: list[Task]

    def reference(self) -> SharedModuleRef:
        return SharedModuleRef(
            id=self.module.id, program_id=self.program.program.id, title=self.module.title
        )

    def completed(self) -> bool:
        return self.module.skipped or (
            bool(self.tasks) and all(task.status == "done" for task in self.tasks)
        )


def module_work(facts: WeekFacts) -> list[ModuleWork]:
    groups: list[ModuleWork] = []
    for program in facts.programs:
        tasks: dict[str, list[Task]] = defaultdict(list)
        for task in program.tasks:
            tasks[task.module_id].append(task)
        groups.extend(ModuleWork(program, module, tasks[module.id]) for module in program.modules)
    return groups


class Prerequisites:
    def __init__(self, groups: list[ModuleWork]) -> None:
        self._index: dict[str, list[ModuleWork]] = defaultdict(list)
        for group in groups:
            names = {_key(group.module.title)}
            names.update(_key(skill) for skill in group.module.skills if isinstance(skill, str))
            for name in names:
                self._index[name].append(group)

    def read(
        self, group: ModuleWork, scheduled: dict[str, date], week_start: date
    ) -> tuple[list[SharedPrerequisite], date | None]:
        requirements = []
        earliest = week_start
        unresolved = False
        labels = list(
            dict.fromkeys(
                item for item in group.module.prerequisites if isinstance(item, str) and _key(item)
            )
        )
        for label in labels:
            alternatives = [
                candidate
                for candidate in self._index[_key(label)]
                if candidate.module.id != group.module.id
            ]
            planned = [
                scheduled[item.module.id] for item in alternatives if item.module.id in scheduled
            ]
            relation = SharedPrerequisite(
                module=group.reference(),
                label=label,
                references=[item.reference() for item in alternatives],
                status="unmatched",
            )
            if any(item.completed() for item in alternatives):
                relation.status = "completed"
            elif planned:
                relation.status = "planned"
                earliest = max(earliest, min(planned) + timedelta(days=1))
            elif alternatives:
                relation.status = "pending"
                unresolved = True
            requirements.append(relation)
        return requirements, None if unresolved else earliest
