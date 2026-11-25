"""Contract and generated cases of the request scheduling system."""

from datetime import timedelta

CHANGE_DELAY = timedelta(minutes=10)
DURATION = timedelta(minutes=30)
TITLE = "Request scheduler"
ENTRY = "service.py"
SKILL = "Python development"
LEGACY_SKILL = "Développement Python"  # the French name stored before the switch to English
BRIEF = (
    "Deliver a request scheduler. The function schedule(requests) returns "
    "the ids in order of arrival. Each request has a distinct id "
    "and an urgent flag (True or False). Keep the original list intact."
)
CHANGE = (
    "The client wants urgent requests handled first. "
    "Keep the order of arrival at equal priority and always return the ids."
)

STARTER = '''"""Scheduling of generated requests for the Boss."""


def schedule(requests):
    """Return the ids in processing order."""
    return [request["id"] for request in requests]


if __name__ == "__main__":
    print(schedule([{"id": "D-1", "urgent": False}, {"id": "D-2", "urgent": True}]))
'''


def starter_files() -> dict[str, str]:
    guide = (
        f"# {TITLE}\n\n{BRIEF}\n\n"
        "Open the Boss page to read the client's change and submit the files."
    )
    return {ENTRY: STARTER, "README.md": guide}
