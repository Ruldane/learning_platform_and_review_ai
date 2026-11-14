"""Ids des faits d'une nouvelle version du profil (D124) : un fait inchangé garde son id, un
fait neuf reçoit un numéro jamais pris, la version de January garde ses ids connus."""

from app.agents.tools.cv_schema import Line, MasterProfileData, SkillFact, assign_fact_ids
from app.agents.tools.profile_check import blank_facts
from app.features.cv.service.profile_merge import all_ids, keep_known, merge_draft
from tests.support.profile import profile


def first() -> MasterProfileData:
    return assign_fact_ids(blank_facts(profile()))


def test_merge_keeps_ids_of_unchanged_facts() -> None:
    previous = first()
    draft = blank_facts(profile())
    draft.experiences.reverse()  # ordre changé : les ids suivent les faits
    draft.experiences[1].achievements.insert(0, Line(text="Mis en place la revue de code"))
    draft.skills.append(SkillFact(name="Qdrant"))
    draft.skills[0].name = "python"  # même texte normalisé
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert [x.id for x in merged.experiences] == ["x2", "x1"]
    assert [a.id for a in merged.experiences[1].achievements] == ["x1a3", "x1a1", "x1a2"]
    assert merged.skills[0].id == "c1" and merged.skills[-1].id == "c6"
    assert merged.title is not None and merged.title.id == "t1"


def test_freed_numbers_are_never_reused() -> None:
    previous = first()
    older = first()
    older.skills.append(SkillFact(id="c9", name="Ancienne"))
    draft = blank_facts(profile())
    draft.experiences = draft.experiences[1:]  # x1 a disparu
    neuve = draft.experiences[0].model_copy(update={"company": "Neuve"}, deep=True)
    draft.experiences.append(neuve)
    merged = merge_draft(draft, previous, all_ids([previous, older]))
    assert [x.id for x in merged.experiences] == ["x2", "x3"]
    assert [a.id for x in merged.experiences for a in x.achievements] == ["x2a1", "x3a1"]
    draft.skills.append(SkillFact(name="Qdrant"))
    assert merge_draft(draft, previous, all_ids([previous, older])).skills[-1].id == "c10"


def test_merge_without_previous_numbers_from_one() -> None:
    merged = merge_draft(blank_facts(profile()), None, set())
    assert [x.id for x in merged.experiences] == ["x1", "x2"]
    assert merged.experiences[0].achievements[1].id == "x1a2"


def test_keep_known_keeps_assigned_ids_and_marks_january() -> None:
    previous = first()
    edited = previous.model_copy(deep=True)
    edited.experiences[0].role = "Ingénieure IA"  # fait modifié : même id
    edited.skills.append(SkillFact(id="c42", name="Qdrant"))  # id jamais attribué
    edited.skills.append(SkillFact(id="c2", name="Doublon"))  # id déjà porté
    edited.experiences[1].achievements.append(Line(id="x1a1", text="Déplacée"))  # mauvais parent
    kept = keep_known(edited, all_ids([previous]))
    assert kept.experiences[0].id == "x1" and kept.experiences[0].role == "Ingénieure IA"
    assert [s.id for s in kept.skills][-2:] == ["c6", "c7"]
    assert kept.experiences[1].achievements[-1].id == "x2a2"
    assert kept.skills[-2].sources == ["january"]
