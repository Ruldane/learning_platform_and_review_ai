import { useId } from "react";
import { t } from "@/shared/i18n/t";

interface Reference {
  index: number;
  title: string;
  url: string;
}

interface Props {
  role: "researcher" | "practitioner" | "skeptic";
  text: string;
  citations: Reference[];
}

function isPublicLink(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol) && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
}

export function ExpertStatement({ role, text, citations }: Props) {
  const titleId = useId();
  const sources = citations.filter((citation) => isPublicLink(citation.url));
  return (
    <article
      aria-labelledby={titleId}
      className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
    >
      <h3 id={titleId} className="text-lg font-semibold">
        {t(`expertDebates.roles.${role}`)}
      </h3>
      <p className="whitespace-pre-wrap break-words">{text}</p>
      {sources.length > 0 ? (
        <>
          <h4 className="text-sm font-medium">{t("expertDebates.references")}</h4>
          <ul className="flex flex-col items-start gap-1 text-sm">
            {sources.map((source) => (
              <li key={source.index}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="break-words underline underline-offset-2"
                >
                  {t("expertDebates.reference", { index: source.index, title: source.title })}
                  <span className="sr-only">{t("expertDebates.newTab")}</span>
                </a>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">{t("expertDebates.noReferences")}</p>
      )}
    </article>
  );
}
