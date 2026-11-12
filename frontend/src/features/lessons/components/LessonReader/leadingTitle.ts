const TITLE = /^ {0,3}#[ \t]+\S/;
const SECTION = /^ {0,3}#{2,6}[ \t]/;
const FENCE = /^ {0,3}(```|~~~)/;

/**
 * Le Markdown sans son titre de tête (`# Titre` placé avant toute section) : la page l'affiche
 * déjà en `<h1>`. La ligne est vidée, pas retirée : les numéros de ligne du sommaire restent justes.
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
