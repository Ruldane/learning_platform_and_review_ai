import { t } from "@/shared/i18n/t";
import type { ResearchBenchInput } from "../viewTypes";

export const MAX_URLS = 5;
const QUERY_MIN = 2;
const QUERY_MAX = 300;

interface Parsed {
  input: ResearchBenchInput;
  errors: { query?: string; urls?: string };
}

/** Rend l'adresse http(s) normalisée, ou `null` (autre schéma, adresse illisible). */
function httpUrl(raw: string): string | null {
  try {
    const url = new URL(raw);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

/** Valide la saisie : requête de 2 à 300 caractères, 5 adresses http(s) au plus (doublons fusionnés). */
export function parseBench(rawQuery: string, rawUrls: string): Parsed {
  const query = rawQuery.trim();
  const errors: Parsed["errors"] = {};
  if (query.length < QUERY_MIN || query.length > QUERY_MAX) {
    errors.query = t("research.bench.errors.query");
  }
  const lines = rawUrls
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");
  const urls: string[] = [];
  for (const line of lines) {
    const href = httpUrl(line);
    if (href === null) {
      errors.urls = t("research.bench.errors.urlScheme", { url: line });
      break;
    }
    if (!urls.includes(href)) urls.push(href);
  }
  if (!errors.urls && urls.length > MAX_URLS) {
    errors.urls = t("research.bench.errors.tooManyUrls", { max: MAX_URLS });
  }
  return { input: { query, urls }, errors };
}
