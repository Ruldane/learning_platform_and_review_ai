import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";

export type HeadingTag = "h2" | "h3" | "h4" | "h5" | "h6";

interface MarkdownHeadingProps {
  as: HeadingTag;
  id?: string;
  children?: ReactNode;
}

const SIZE: Record<HeadingTag, string> = {
  h2: "mt-10 mb-3 text-2xl",
  h3: "mt-8 mb-2 text-xl",
  h4: "mt-6 mb-2 text-lg",
  h5: "mt-4 mb-1 text-base",
  h6: "mt-4 mb-1 text-base",
};

/** Titre d'une section : porte l'ancre du sommaire. Le `h1` de la page est le titre de la leçon. */
export function MarkdownHeading({ as: Tag, id, children }: MarkdownHeadingProps) {
  return (
    <Tag id={id} className={cn("scroll-mt-6 font-semibold", SIZE[Tag])}>
      {children}
    </Tag>
  );
}
