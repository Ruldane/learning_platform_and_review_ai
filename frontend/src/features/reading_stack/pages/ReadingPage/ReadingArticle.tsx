import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import type { ReadingDetail } from "../../api";

export function ReadingArticle({ article }: { article: ReadingDetail }) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => title.current?.focus(), [article.id]);
  return (
    <>
      <p className="text-sm text-muted-foreground">{t(`reading.kind.${article.kind}`)}</p>
      <h2
        id="reading-article-title"
        tabIndex={-1}
        ref={title}
        className="break-words text-xl font-semibold"
      >
        {article.title}
      </h2>
      <p className="text-sm">
        <strong>{t("reading.reason")}</strong>
        <span className="ml-2 break-words">{article.reason}</span>
      </p>
      <a
        className="self-start text-sm underline"
        href={article.url}
        target="_blank"
        rel="noreferrer"
      >
        {t("reading.source")}
      </a>
      {article.summary ? (
        <p className="break-words text-sm font-medium">{article.summary}</p>
      ) : null}
      <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
        {article.text || t("reading.contentUnavailable")}
      </p>
    </>
  );
}
