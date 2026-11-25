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
 * Renders a lesson's Markdown (GFM: tables, task lists). The content is not trusted
 * (SPEC 17.2): a raw HTML block shows as text (`remarkRawHtmlAsText`), inline HTML is
 * removed, nothing is ever interpreted (`skipHtml` as a last resort); only the addresses
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
