import { useId, type ReactNode } from "react";

interface SummarySectionProps {
  title: string;
  /** Une ligne par élément ; `key` doit être unique dans la liste. */
  items: { key: string; content: ReactNode }[];
  /** Phrase affichée quand la liste est vide. */
  empty: string;
}

/** Un titre `h3` et sa liste (nommée par ce titre) ou, à défaut, une phrase « rien à signaler ». */
export function SummarySection({ title, items, empty }: SummarySectionProps) {
  const id = useId();
  return (
    <div>
      <h3 id={id} className="text-sm font-medium">
        {title}
      </h3>
      {items.length > 0 ? (
        <ul aria-labelledby={id} className="mt-1 flex flex-col gap-1 text-sm">
          {items.map((item) => (
            <li key={item.key}>{item.content}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-sm text-muted-foreground">{empty}</p>
      )}
    </div>
  );
}
