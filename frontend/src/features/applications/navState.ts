import { isStatus } from "./components/guards";
import { todayString } from "./dates";
import type { AlertOut } from "./types";

/** What creating a record passes to the open record (`navigate(..., { state })`). */
export interface OpenedState {
  info: AlertOut[];
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const isAlert = (value: unknown): value is AlertOut =>
  isRecord(value) && typeof value.application_id === "string" && typeof value.message === "string";

/** « même entreprise » info received when the record opens (none if the state lacks it). */
export function openedInfo(state: unknown): AlertOut[] {
  if (!isRecord(state)) return [];
  const info = state.info;
  return Array.isArray(info) ? info.filter(isAlert) : [];
}

/** Info attached to `artifact.ready` (« même entreprise », SPEC 6.3): what the one-sentence entry
 * announces. */
export interface ArtifactInfoItem {
  application_id: string;
  company: string;
  title: string;
  status: string;
  message: string;
}

/** The info of an `artifact.ready` as `info` alerts (a record with an unknown status is
 * ignored). */
export function infoFromArtifact(items: ArtifactInfoItem[] | undefined): AlertOut[] {
  return (items ?? []).flatMap(({ status, ...item }) =>
    isStatus(status)
      ? [{ ...item, status, level: "info" as const, applied_on: null, created_on: todayString() }]
      : [],
  );
}
