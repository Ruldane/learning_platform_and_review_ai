import { t } from "@/shared/i18n/t";
import type { KitKindView } from "../viewTypes";

/** Ce que le code a laissé à la place d'une réponse : sa prétention salariale, ou un fait absent. */
export type Blank = "salary" | "complete" | null;

/** Un morceau du texte d'une pièce, copiable et modifiable à part. */
export interface Part {
  key: string;
  /** Son nom (relance à 7 jours, question du formulaire) ; `null` pour une pièce d'un seul texte. */
  label: string | null;
  text: string;
  blank: Blank;
  blankMarker?: string;
}

export const SALARY_BLANK = "For you to fill in";
export const TO_COMPLETE = "To complete";
export const MAX_CONTENT = 20_000;
const SEPARATOR = /^\s*---\s*$/;
const QUESTION = /^### +(.*)$/;
const TWO_PARTS: readonly KitKindView[] = ["linkedin", "followups"];

/** Les pièces faites de deux textes que le serveur sépare par une ligne `---`. */
const isTwoParts = (kind: KitKindView): kind is "linkedin" | "followups" =>
  TWO_PARTS.includes(kind);

function twoParts(kind: "linkedin" | "followups", content: string): Part[] {
  const halves: string[][] = [[]];
  for (const line of content.split("\n")) {
    if (SEPARATOR.test(line)) halves.push([]);
    else halves.at(-1)?.push(line);
  }
  const texts = halves.map((lines) => lines.join("\n").trim());
  return [0, 1].map((rank) => ({
    key: `part${rank}`,
    label: t(`applications.kitPiece.part.${kind}_${rank as 0 | 1}`),
    text: texts[rank] ?? "",
    blank: null,
  }));
}

function blankOf(answer: string): Blank {
  if (answer === SALARY_BLANK || answer === "À remplir par toi") return "salary";
  return answer === TO_COMPLETE || answer === "À compléter" ? "complete" : null;
}

function formParts(content: string): Part[] | null {
  const items: { question: string; lines: string[] }[] = [];
  for (const line of content.split("\n")) {
    const match = QUESTION.exec(line);
    if (match) items.push({ question: (match[1] ?? "").trim(), lines: [] });
    else items.at(-1)?.lines.push(line);
  }
  if (items.length === 0) return null;
  return items.map(({ question, lines }, rank) => {
    const answer = lines.join("\n").trim();
    const blank = blankOf(answer);
    return {
      key: `q${rank}`,
      label: question,
      text: blank ? "" : answer,
      blank,
      blankMarker: blank ? answer : undefined,
    };
  });
}

/**
 * Le texte d'une pièce en morceaux : les deux textes d'un message LinkedIn ou des relances, une
 * réponse par question d'un formulaire (les réponses laissées par le code sont vides, marquées par
 * `blank`), sinon un seul morceau.
 */
export function splitParts(kind: KitKindView, content: string): Part[] {
  if (isTwoParts(kind)) return twoParts(kind, content);
  const form = kind === "form_answers" ? formParts(content) : null;
  return form ?? [{ key: "text", label: null, text: content, blank: null }];
}

/** Le texte de la pièce que le serveur relira : l'inverse de `splitParts`. */
export function joinParts(kind: KitKindView, parts: Part[]): string {
  if (isTwoParts(kind)) {
    const [first = "", second = ""] = parts.map((part) => part.text.trim());
    return first === "" && second === "" ? "" : `${first}\n\n---\n\n${second}`;
  }
  const form = parts.length > 0 && parts.every((part) => part.key.startsWith("q"));
  if (kind === "form_answers" && form) {
    return parts.map((part) => `### ${part.label ?? ""}\n${answerOf(part)}`).join("\n\n");
  }
  return parts.map((part) => part.text).join("\n\n");
}

function answerOf(part: Part): string {
  const text = part.text.trim();
  if (text !== "") return text;
  return part.blankMarker ?? (part.blank === "salary" ? SALARY_BLANK : TO_COMPLETE);
}
