import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { httpUrlOnly, markdownComponents } from "./markdownComponents";
import { remarkRawHtmlAsText } from "./rawHtmlAsText";
import type { TocHeading } from "./toc";

interface LessonMarkdownProps {
  markdown: string;
  headings: TocHeading[];
}

const REMARK_PLUGINS = [remarkGfm, remarkRawHtmlAsText];

/**
 * Rendu du Markdown d'une leçon (GFM : tables, listes de tâches). Le contenu n'est pas fiable
 * (SPEC 17.2) : un bloc HTML brut s'affiche en texte (`remarkRawHtmlAsText`), le HTML en ligne est
 * retiré, rien n'est jamais interprété (`skipHtml` en dernier recours) ; seules les adresses
 * http(s) passent (`urlTransform`).
 */
export function LessonMarkdown({ markdown, headings }: LessonMarkdownProps) {
  const components = useMemo(
    () => markdownComponents(new Map(headings.map((heading) => [heading.line, heading.id]))),
    [headings],
  );
  return (
    <ReactMarkdown
      remarkPlugins={REMARK_PLUGINS}
      skipHtml
      urlTransform={httpUrlOnly}
      components={components}
    >
      {markdown}
    </ReactMarkdown>
  );
}
