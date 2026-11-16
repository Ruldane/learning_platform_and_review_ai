"""Partie `planifie` du contrôle de la phase 8 : le brief du matin créé par la tâche planifiée, pas
par l'ouverture de l'accueil. À lancer AVANT toute ouverture de l'accueil du jour : `GET
/brief/today` crée le brief, `GET /activity` ne crée rien, c'est donc lui que le script relit.

Étape `préalable` : aucun brief du jour (sinon le script le dit et ne règle rien). Étape
`planification` : l'heure du brief est réglée trois minutes plus tard, le fil d'activité est relu
jusqu'à l'élément « Brief du jour prêt » (la tâche passe toutes les 10 minutes : 10 minutes au
plus après l'heure réglée) ; l'heure d'origine est remise, quoi qu'il arrive. Étape `origine` : le
brief du jour est d'origine `schedule`, c'est celui de l'élément du fil. Rien de ce qui est reçu
n'apparaît dans la sortie : seulement des étapes, des nombres, des codes et des identifiants."""

import time
from datetime import UTC, datetime
from typing import Any

from scripts.phase4_steps import CheckFailed, Run, expect_ok
from scripts.phase8_common import Track, local_now, put_settings, settings_kept, wait_for
from scripts.phase8_rules import check_same_day, target_moment

PLANNED_GRACE_S = 660.0  # la tâche passe toutes les 10 minutes : 10 minutes et une de marge
ACTIVITY_LIMIT = 50


async def _brief_items(run: Run, step: str, since: datetime) -> list[dict[str, Any]]:
    """Les éléments « Brief du jour prêt » du fil depuis `since` (le fil ne crée rien)."""
    params = {"after": since.astimezone(UTC).isoformat(), "limit": ACTIVITY_LIMIT}
    page = await expect_ok(run, step, "GET", "/activity", params=params)
    return [item for item in page["items"] if item["kind"] == "brief"]


def _midnight(zone: str) -> datetime:
    return local_now(zone).replace(hour=0, minute=0, second=0, microsecond=0)


async def check_prerequisite(run: Run, st: Track) -> None:
    step = "préalable"
    settings = await expect_ok(run, step, "GET", "/settings")
    found = await _brief_items(run, step, _midnight(str(settings["timezone"])))
    if found:
        raise CheckFailed(
            step,
            f"Le brief du jour existe déjà ({found[0]['id']}) : la partie « planifie » "
            "demande un jour sans brief. Relance-la demain, avant d'ouvrir l'accueil.",
        )


async def check_planned(run: Run, st: Track) -> None:
    step = "planification"
    async with settings_kept(run, step) as original:
        zone = str(original["timezone"])
        now = local_now(zone)
        target = target_moment(now)
        check_same_day(step, now, target)
        await put_settings(run, step, original | {"brief_time": target.strftime("%H:%M")})
        print("    heure du brief réglée à 3 minutes (remise ensuite)", flush=True)
        began = time.monotonic()
        midnight = _midnight(zone)
        wait_s = (target - now).total_seconds() + PLANNED_GRACE_S

        async def appeared() -> bool:
            found = await _brief_items(run, step, midnight)
            st.activity_id = str(found[0]["id"]) if found else ""
            return bool(found)

        await wait_for(run, step, appeared, "aucun « Brief du jour prêt » au fil", wait_s)
        waited = time.monotonic() - began
    print(f"    élément {st.activity_id} au fil, {waited:.0f} s après le réglage", flush=True)


async def check_origin(run: Run, st: Track) -> None:
    step = "origine"
    brief = await expect_ok(run, step, "GET", "/brief/today")
    if brief["origin"] != "schedule":
        raise CheckFailed(step, f"Origine du brief « {brief['origin']} » : « schedule » attendue.")
    if st.activity_id != f"brief:{brief['id']}:ready":
        raise CheckFailed(step, "Le brief du jour n'est pas celui de l'élément du fil.")
    st.brief = brief
    print(f"    brief {brief['id']} créé par la tâche planifiée", flush=True)
