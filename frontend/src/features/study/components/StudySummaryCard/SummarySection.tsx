import { useId, type ReactNode } from "react";

interface SummarySectionProps {
  title: string;
  /** One line per item; `key` must be unique in the list. */
  items: { key: string; content: ReactNode }[];
  /** Sentence shown when the list is empty. */
  empty: string;
}

/** An `h3` title and its list (named by it), or else a « rien à signaler » sentence. */
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
