import { isStatus } from "./components/guards";
import { todayString } from "./dates";
import type { AlertOut } from "./types";

/** Ce que la création d'une fiche transmet à la fiche ouverte (`navigate(..., { state })`). */
export interface OpenedState {
  info: AlertOut[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isAlert = (value: unknown): value is AlertOut =>
  isRecord(value) && typeof value.application_id === "string" && typeof value.message === "string";

/** Les informations « même entreprise » reçues à l'ouverture de la fiche (rien si l'état n'en porte pas). */
export function openedInfo(state: unknown): AlertOut[] {
  if (!isRecord(state)) return [];
  const info = state.info;
  return Array.isArray(info) ? info.filter(isAlert) : [];
}

/** Une information jointe à `artifact.ready` (« même entreprise », SPEC 6.3) : celle que la saisie en une phrase annonce. */
export interface ArtifactInfoItem {
  application_id: string;
  company: string;
  title: string;
  status: string;
  message: string;
}

/** Les informations d'un `artifact.ready` en alertes `info` (une fiche d'un statut inconnu est ignorée). */
export function infoFromArtifact(items: ArtifactInfoItem[] | undefined): AlertOut[] {
  return (items ?? []).flatMap(({ status, ...item }) =>
    isStatus(status)
      ? [{ ...item, status, level: "info" as const, applied_on: null, created_on: todayString() }]
      : [],
  );
}
