"""Pages GitHub entièrement fictives pour les tests de liaison d’un commit."""

import json

from tests.support.research import FakeFetcher

REPOSITORY = "orga-fictive/bibliotheque"
REPO_URL = f"https://github.com/{REPOSITORY}"
REPO_API = f"https://api.github.com/repos/{REPOSITORY}"
SHA = "128d4898ea3ef79a06720eabe0b041b1a9c2553d"
AUTHOR = "camille-fictive"
AUTHOR_ID = 312456
PROFILE_API = f"https://api.github.com/user/{AUTHOR_ID}"


def serve(fetcher: FakeFetcher, url: str, payload: object) -> None:
    fetcher.files[url] = ("application/json", json.dumps(payload).encode())


def github_commit(
    fetcher: FakeFetcher, *, verified: bool = True, public: bool = True, reachable: bool = True
) -> None:
    serve(
        fetcher,
        REPO_API,
        {"id": 836251, "full_name": REPOSITORY, "private": not public, "default_branch": "main"},
    )
    identity = {"id": AUTHOR_ID, "login": AUTHOR, "type": "User"}
    serve(
        fetcher,
        f"{REPO_API}/commits/{SHA}",
        {
            "sha": SHA,
            "author": identity,
            "committer": identity,
            "commit": {"verification": {"verified": verified, "reason": "valid"}},
        },
    )
    serve(
        fetcher,
        f"{REPO_API}/compare/{SHA}...main?per_page=1",
        {
            "status": "ahead" if reachable else "diverged",
            "merge_base_commit": {"sha": SHA if reachable else "f" * 40},
        },
    )
    github_profile(fetcher, "")


def github_profile(fetcher: FakeFetcher, bio: str, *, identity: int = AUTHOR_ID) -> None:
    serve(fetcher, PROFILE_API, {"id": identity, "type": "User", "bio": bio})
