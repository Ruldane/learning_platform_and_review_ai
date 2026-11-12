import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { httpUrlOnly, markdownComponents } from "./markdownComponents";
import type { TocHeading } from "./toc";

interface LessonMarkdownProps {
  markdown: string;
  headings: TocHeading[];
}

const REMARK_PLUGINS = [remarkGfm];

/**
 * Rendu du Markdown d'une leçon (GFM : tables, listes de tâches). Le contenu n'est pas fiable
 * (SPEC 17.2) : le HTML brut est ignoré (`skipHtml`) et seules les adresses http(s) passent
 * (`urlTransform`).
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
