import { useId } from "react";
import type { ReactNode } from "react";

interface DiffSectionProps {
  title: string;
  count: number;
  children: ReactNode;
}

/** Une rubrique du diff (Ajoutées, Retirées ou Déplacées) ; absente quand elle est vide. */
export function DiffSection({ title, count, children }: DiffSectionProps) {
  const headingId = useId();
  if (count === 0) return null;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h3 id={headingId} className="text-base font-semibold">
          {title}
        </h3>
        <span className="text-sm text-muted-foreground tabular-nums">{count}</span>
      </div>
      <ul className="flex flex-col gap-3 rounded-lg border bg-card p-3">{children}</ul>
    </section>
  );
}
