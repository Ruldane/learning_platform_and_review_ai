import { useState } from "react";
import { t } from "@/shared/i18n/t";

/** Server-side bounds of a draft's text (`DraftPatchIn.content`: 1 to 3,000 characters). */
const DRAFT_MAX = 3000;

function problem(value: string): string | null {
  if (value.trim() === "") return t("projects.draft.errorEmpty");
  return [...value].length > DRAFT_MAX
    ? t("projects.draft.errorTooLong", { max: DRAFT_MAX })
    : null;
}

/**
 * A draft's edited text: it restarts from the server's text when that changes. An empty
 * or too-long text is reported on the card at the first save attempt (`tryOk`), without
 * sending anything; `error` is the server's refusal or failure for this draft.
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
    /** On save: true if the text may go out; otherwise the message is shown. */
    tryOk: () => {
      setTried(true);
      return invalid === null;
    },
  };
}
