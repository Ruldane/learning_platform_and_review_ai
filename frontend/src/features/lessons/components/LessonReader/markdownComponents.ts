import { createElement } from "react";
import type { Components } from "react-markdown";
import { t } from "@/shared/i18n/t";
import { MarkdownCodeBlock } from "./MarkdownCodeBlock";
import { MarkdownHeading } from "./MarkdownHeading";
import type { HeadingTag } from "./MarkdownHeading";
import { MarkdownLink } from "./MarkdownLink";

type HeadingComponent = NonNullable<Components["h2"]>;

function heading(as: HeadingTag, idsByLine: ReadonlyMap<number, string>): HeadingComponent {
  const Heading: HeadingComponent = ({ node, children }) =>
    createElement(
      MarkdownHeading,
      { as, id: idsByLine.get(node?.position?.start.line ?? -1) },
      children,
    );
  return Heading;
}

/**
 * Éléments Markdown remplacés : titres à ancres (le `h1` du Markdown passe en `h2`, la page a déjà
 * le sien), liens sûrs, blocs de code et schémas Mermaid. Les images ne sont pas chargées : la page
 * n'ouvre aucune connexion vers un site tiers, seule leur description s'affiche.
 */
export function markdownComponents(idsByLine: ReadonlyMap<number, string>): Components {
  return {
    h1: heading("h2", idsByLine),
    h2: heading("h2", idsByLine),
    h3: heading("h3", idsByLine),
    h4: heading("h4", idsByLine),
    h5: heading("h5", idsByLine),
    h6: heading("h6", idsByLine),
    a: MarkdownLink,
    pre: MarkdownCodeBlock,
    img: ({ alt }) => (alt ? t("lessons.reader.image", { alt }) : null),
  };
}

/** Seules les adresses http(s) passent : `javascript:`, `data:`, adresses relatives et ancres tombent. */
export function httpUrlOnly(url: string): string {
  return /^https?:\/\//i.test(url) ? url : "";
}
