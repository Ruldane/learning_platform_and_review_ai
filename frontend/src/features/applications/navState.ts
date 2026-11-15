import type { AlertOut } from "./types";

/** Ce que la création d'une fiche transmet à la fiche ouverte (`navigate(..., { state })`). */
export interface OpenedState {
  info: AlertOut[];
}

const isAlert = (value: unknown): value is AlertOut =>
  typeof value === "object" &&
  value !== null &&
  typeof (value as AlertOut).application_id === "string" &&
  typeof (value as AlertOut).message === "string";

/** Les informations « même entreprise » reçues à l'ouverture de la fiche (rien si l'état n'en porte pas). */
export function openedInfo(state: unknown): AlertOut[] {
  if (typeof state !== "object" || state === null) return [];
  const info = (state as { info?: unknown }).info;
  return Array.isArray(info) ? info.filter(isAlert) : [];
}
