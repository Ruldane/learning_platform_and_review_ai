export type DiffKind = "same" | "add" | "del";

export interface DiffSegment {
  kind: DiffKind;
  text: string;
}

/** Au-delà, la table de comparaison serait trop grosse : le texte est donné en bloc. */
const MAX_CELLS = 250_000;

const words = (text: string): string[] => text.split(/\s+/).filter(Boolean);

function push(segments: DiffSegment[], kind: DiffKind, word: string): void {
  const last = segments[segments.length - 1];
  if (last && last.kind === kind) last.text += ` ${word}`;
  else segments.push({ kind, text: word });
}

/** Longueur de la plus longue sous-suite commune de `a[i:]` et `b[j:]`, table remplie de la fin. */
function lcsLengths(a: string[], b: string[]): (i: number, j: number) => number {
  const width = b.length + 1;
  const table = new Uint32Array((a.length + 1) * width);
  const at = (i: number, j: number): number => table[i * width + j] ?? 0;
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      table[i * width + j] =
        a[i] === b[j] ? at(i + 1, j + 1) + 1 : Math.max(at(i + 1, j), at(i, j + 1));
    }
  }
  return at;
}

/**
 * Compare deux textes mot à mot : les mots communs (`same`), ceux qui disparaissent (`del`) et ceux
 * qui apparaissent (`add`), les mots voisins de même sorte regroupés.
 */
export function wordDiff(before: string, after: string): DiffSegment[] {
  const a = words(before);
  const b = words(after);
  const segments: DiffSegment[] = [];
  if ((a.length + 1) * (b.length + 1) > MAX_CELLS) {
    if (a.length > 0) segments.push({ kind: "del", text: a.join(" ") });
    if (b.length > 0) segments.push({ kind: "add", text: b.join(" ") });
    return segments;
  }
  const lcs = lcsLengths(a, b);
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    const left = a[i];
    const right = b[j];
    if (left !== undefined && left === right) {
      push(segments, "same", left);
      i++;
      j++;
    } else if (left !== undefined && (right === undefined || lcs(i + 1, j) >= lcs(i, j + 1))) {
      push(segments, "del", left);
      i++;
    } else if (right !== undefined) {
      push(segments, "add", right);
      j++;
    }
  }
  return segments;
}
