import { createContext } from "react";
import type { LineView, MasterProfileView } from "../viewTypes";

/** The 422 errors from saving: field path (`experiences.2.role`) → message. */
export const FieldErrorsContext = createContext<Record<string, string>>({});

/** Does an error concern this path or one of its descendants? */
export function hasErrorUnder(errors: Record<string, string>, prefix: string): boolean {
  return Object.keys(errors).some((path) => path === prefix || path.startsWith(`${prefix}.`));
}

const LINE_PATH = /^(experiences|education|projects)\.(\d+)\.(achievements|details)\.(\d+)(\..*)?$/;

interface WithLines {
  achievements?: LineView[];
  details?: LineView[];
}

/**
 * The server received the cleaned profile (empty rows removed): the index of a faulty row
 * counts without them. This path maps it back to the row shown, so the error lands under the
 * right field.
 */
function displayedPath(sent: MasterProfileView, path: string): string {
  const match = LINE_PATH.exec(path);
  if (!match) return path;
  const [, section, row, list, line, rest = ""] = match;
  const owner: WithLines | undefined = sent[section as "experiences"][Number(row)];
  const shown = (owner?.[list as "achievements"] ?? [])
    .map((item, index) => (item.text.trim() === "" ? -1 : index))
    .filter((index) => index >= 0);
  const index = shown[Number(line)];
  return index === undefined ? path : `${section}.${row}.${list}.${index}${rest}`;
}

/** The 422 errors of a cleaned profile sent, mapped back onto the rows as displayed. */
export function displayedErrors(
  sent: MasterProfileView,
  errors: Record<string, string>,
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(errors).map(([path, message]) => [displayedPath(sent, path), message]),
  );
}
