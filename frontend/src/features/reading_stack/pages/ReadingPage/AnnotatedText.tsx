import { Fragment, useEffect, useRef, useState, type RefObject } from "react";
import { t } from "@/shared/i18n/t";
import type { ReadingDetail } from "../../api";
import { GlossaryTerm } from "../../components/GlossaryTerm";
import { ReadingDefinition } from "../../components/ReadingDefinition";

type Annotation = NonNullable<ReadingDetail["annotations"]>[number];

function usePassage(
  root: RefObject<HTMLParagraphElement | null>,
  onPassage: (passage: string) => void,
) {
  useEffect(() => {
    function report() {
      const selection = document.getSelection();
      if (!selection?.rangeCount || !root.current || selection.isCollapsed) {
        onPassage("");
        return;
      }
      const range = selection.getRangeAt(0);
      const inside = root.current.contains(range.commonAncestorContainer);
      const text = inside ? range.toString().trim() : "";
      onPassage(text);
    }
    document.addEventListener("selectionchange", report);
    return () => document.removeEventListener("selectionchange", report);
  }, [root, onPassage]);
}

interface Props {
  article: ReadingDetail;
  onPassage: (passage: string) => void;
}

export function AnnotatedText({ article, onPassage }: Props) {
  const root = useRef<HTMLParagraphElement>(null);
  const [open, setOpen] = useState<Annotation | null>(null);
  usePassage(root, onPassage);
  if (!article.text) return <p>{t("reading.contentUnavailable")}</p>;
  const items = article.annotations ?? [];
  function closeDefinition() {
    root.current?.querySelector<HTMLButtonElement>('button[aria-expanded="true"]')?.focus();
    setOpen(null);
  }
  function openDefinition(item: Annotation) {
    setOpen(item);
    window.requestAnimationFrame(() => {
      document.getElementById("reading-definition")?.focus();
    });
  }
  return (
    <>
      <p ref={root} className="whitespace-pre-wrap break-words text-sm leading-relaxed">
        {items.map((item, index) => (
          <Fragment key={item.start}>
            {article.text.slice(items[index - 1]?.end ?? 0, item.start)}
            <GlossaryTerm
              text={article.text.slice(item.start, item.end)}
              active={open?.start === item.start}
              onPreview={() => setOpen(item)}
              onOpen={() => openDefinition(item)}
              onClose={() => setOpen(null)}
            />
          </Fragment>
        ))}
        {article.text.slice(items.at(-1)?.end ?? 0)}
      </p>
      {open ? (
        <ReadingDefinition
          term={open.term}
          text={open.definition}
          chapter={open.chapter}
          lessonId={open.lesson_id}
          onClose={closeDefinition}
        />
      ) : null}
    </>
  );
}
