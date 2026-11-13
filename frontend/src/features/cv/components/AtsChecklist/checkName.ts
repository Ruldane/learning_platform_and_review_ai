import { t } from "@/shared/i18n/t";
import type { AtsCheckIdView } from "../viewTypes";

const KNOWN: AtsCheckIdView[] = [
  "selectable_text",
  "reading_order",
  "standard_headings",
  "contact_in_body",
  "font_sizes",
];

/** Le nom d'un contrôle ; un contrôle inconnu garde son identifiant. */
export function checkName(id: string): string {
  return KNOWN.includes(id as AtsCheckIdView) ? t(`cv.ats.check.${id as AtsCheckIdView}`) : id;
}
