import { STATUS_ORDER } from "./components/viewTypes";
import { todayString } from "./dates";
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
  return (items ?? []).flatMap((item) =>
    (STATUS_ORDER as readonly string[]).includes(item.status)
      ? [
          {
            ...item,
            status: item.status as AlertOut["status"],
            level: "info" as const,
            applied_on: null,
            created_on: todayString(),
          },
        ]
      : [],
  );
}
