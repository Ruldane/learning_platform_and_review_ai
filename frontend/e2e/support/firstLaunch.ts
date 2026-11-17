import { expect, type APIRequestContext } from "@playwright/test";

/**
 * Amorçage du premier lancement (phase 9, P20) : sur une base neuve, le back fige `onboarding_done`
 * à faux au premier `GET /settings` (aucune clé ni objectif), et la porte de la coquille
 * (`OnboardingGate`) renvoie alors toute page vers `/bienvenue`. Les parcours n° 1 à n° 4 ne
 * visent pas l'accueil : ils le terminent par l'API avant leur premier `page.goto`, exactement
 * comme le fait « Terminer » (un `PUT /settings` complet, `onboarding_done: true`). Le code de
 * l'application n'est jamais contourné ; le premier lancement lui-même est joué par le parcours
 * n° 5 (`account.spec.ts`).
 */
export const API = `${process.env.E2E_API_URL ?? "http://localhost:8765"}/api/v1`;

/**
 * Marque le premier lancement comme fait. `PUT /settings` remplace tout l'objet : on relit donc
 * d'abord les réglages (le premier `GET` crée la ligne), puis on les renvoie avec
 * `onboarding_done: true` (les champs calculés, comme `vision_enabled`, sont ignorés par le back).
 * Sans effet si c'est déjà fait : `onboarding_done` est monotone.
 */
export async function finishFirstLaunch(request: APIRequestContext, api = API): Promise<void> {
  const current = await request.get(`${api}/settings`);
  expect(current.ok()).toBe(true);
  const settings = (await current.json()) as Record<string, unknown>;
  if (settings.onboarding_done === true) return;
  const saved = await request.put(`${api}/settings`, {
    data: { ...settings, onboarding_done: true },
  });
  expect(saved.ok()).toBe(true);
  expect(((await saved.json()) as Record<string, unknown>).onboarding_done).toBe(true);
}
