export interface TocHeading {
  /** 2 ou 3 : les titres de section et de sous-section. */
  level: 2 | 3;
  text: string;
  /** Ancre unique dans la leçon. */
  id: string;
  /** Ligne du titre dans le Markdown (à partir de 1) : relie le sommaire au rendu. */
  line: number;
}

/** Ancre d'un titre : minuscules, sans accents, tirets entre les mots. */
export function slugify(text: string): string {
  const slug = text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "section";
}

function plainText(markdown: string): string {
  return markdown
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[*_`~]/g, "")
    .trim();
}

const HEADING = /^(#{2,3})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/;
const FENCE = /^ {0,3}(```|~~~)/;

/** Titres de niveau 2 et 3 d'un Markdown, hors blocs de code, avec des ancres uniques. */
export function extractHeadings(markdown: string): TocHeading[] {
  const seen = new Map<string, number>();
  const headings: TocHeading[] = [];
  let fence: string | null = null;
  markdown.split(/\r?\n/).forEach((line, index) => {
    const marker = FENCE.exec(line)?.[1];
    if (marker) {
      fence = fence === null ? marker : fence === marker ? null : fence;
      return;
    }
    const match = fence === null ? HEADING.exec(line) : null;
    if (!match) return;
    const [, hashes = "", raw = ""] = match;
    const text = plainText(raw);
    if (!text) return;
    const base = slugify(text);
    const count = (seen.get(base) ?? 0) + 1;
    seen.set(base, count);
    headings.push({
      level: hashes.length as 2 | 3,
      text,
      id: count === 1 ? base : `${base}-${count}`,
      line: index + 1,
    });
  });
  return headings;
}
