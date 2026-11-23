"""Retire les leçons écrites par erreur pour des modules « Valider mes acquis » (D309).

Un module de validation (D220) ne porte qu'un quiz. Les leçons qu'il a reçues sont supprimées,
avec leurs ressources, chasses, propositions de mise à jour et variantes. Une leçon déjà
reprise par une séance d'étude ou un épisode de podcast est gardée : ces lignes la citent."""

from alembic import op

revision = "0076"
down_revision = "0075"

_TARGETS = """
    SELECT l.id FROM lessons AS l
    JOIN modules AS m ON m.id = l.module_id
    WHERE m.kind = 'validation'
      AND l.id NOT IN (SELECT lesson_id FROM study_sessions WHERE lesson_id IS NOT NULL)
      AND l.id NOT IN (SELECT lesson_id FROM podcast_episodes)
"""


def upgrade() -> None:
    for table in ("lesson_hunts", "lesson_updates", "lesson_variant_sets"):
        op.execute(f"DELETE FROM {table} WHERE lesson_id IN ({_TARGETS})")  # noqa: S608
    op.execute(
        "DELETE FROM resources WHERE module_id IN "
        "(SELECT id FROM modules WHERE kind = 'validation')"
    )
    op.execute(f"DELETE FROM lessons WHERE id IN ({_TARGETS})")  # noqa: S608


def downgrade() -> None:
    """Suppression de données : rien à rétablir."""
