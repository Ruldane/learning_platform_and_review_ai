export interface TocHeading {
  /** 2 or 3: the section and subsection headings. */
  level: 2 | 3;
  text: string;
  /** Unique anchor in the lesson. */
  id: string;
  /** Line of the heading in the Markdown (from 1): links the contents to the rendering. */
  line: number;
}

/** Anchor of a heading: lowercase, no accents, dashes between words. */
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

/** Level 2 and 3 headings of a Markdown, outside code blocks, with unique anchors. */
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
