import { useState } from "react";
import { t } from "@/shared/i18n/t";

/** Les bornes du texte d'un brouillon côté serveur (`DraftPatchIn.content` : 1 à 3 000 caractères). */
const DRAFT_MAX = 3000;

function problem(value: string): string | null {
  if (value.trim() === "") return t("projects.draft.errorEmpty");
  return [...value].length > DRAFT_MAX
    ? t("projects.draft.errorTooLong", { max: DRAFT_MAX })
    : null;
}

/**
 * Le texte retouché d'un brouillon : il repart du texte du serveur quand celui-ci change. Un texte
 * vide ou trop long est dit sur la carte dès la première tentative d'enregistrement (`tryOk`), sans
 * rien envoyer ; `error` est le refus ou la panne du serveur pour ce brouillon.
 */
export function useDraftText(content: string, error: string | null) {
  const [value, setValue] = useState(content);
  const [seen, setSeen] = useState(content);
  const [tried, setTried] = useState(false);
  if (seen !== content) {
    setSeen(content);
    setValue(content);
  }
  const invalid = problem(value);
  return {
    value,
    setValue,
    message: (tried ? invalid : null) ?? error,
    /** À l'enregistrement : vrai si le texte peut partir ; sinon le message s'affiche. */
    tryOk: () => {
      setTried(true);
      return invalid === null;
    },
  };
}
