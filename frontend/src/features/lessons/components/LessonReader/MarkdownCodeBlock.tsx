import type { ReactNode } from "react";
import { MermaidSvg } from "@/shared/session-ui";
import { t } from "@/shared/i18n/t";

interface HastNode {
  type?: string;
  tagName?: string;
  value?: string;
  properties?: { className?: unknown };
  children?: HastNode[];
}

interface MarkdownCodeBlockProps {
  node?: unknown;
  children?: ReactNode;
}

function textOf(node: HastNode): string {
  return node.value ?? (node.children ?? []).map(textOf).join("");
}

function isMermaid(code: HastNode | undefined): boolean {
  const classes = code?.properties?.className;
  return code?.tagName === "code" && Array.isArray(classes) && classes.includes("language-mermaid");
}

/** Bloc de code : un bloc « mermaid » devient un schéma (rendu strict), les autres restent du code. */
export function MarkdownCodeBlock({ node, children }: MarkdownCodeBlockProps) {
  const code = (node as HastNode | undefined)?.children?.[0];
  if (code && isMermaid(code)) {
    return (
      <figure className="my-6">
        <MermaidSvg code={textOf(code).trimEnd()} title={t("lessons.reader.diagram")} />
      </figure>
    );
  }
  return <pre>{children}</pre>;
}
