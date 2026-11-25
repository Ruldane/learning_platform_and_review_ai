const TITLE = /^ {0,3}#[ \t]+\S/;
const SECTION = /^ {0,3}#{2,6}[ \t]/;
const FENCE = /^ {0,3}(```|~~~)/;

/**
 * The Markdown without its leading title (`# Title` placed before any section): the page shows it
 * already as `<h1>`. The line is emptied, not removed: the outline's line numbers stay correct.
 */
export function withoutLeadingTitle(markdown: string): string {
  const lines = markdown.split("\n");
  let fence = false;
  for (const [index, line] of lines.entries()) {
    if (FENCE.test(line)) fence = !fence;
    if (fence) continue;
    if (SECTION.test(line)) return markdown;
    if (TITLE.test(line)) {
      lines[index] = "";
      return lines.join("\n");
    }
  }
  return markdown;
}
