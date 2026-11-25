import type { ReactNode } from "react";
import { useId } from "react";

/** A named block (region) of the panel; hidden when `count` is zero. */
export function SourcesBlock({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: ReactNode;
}) {
  const id = useId();
  if (count === 0) return null;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <div className="flex items-baseline gap-2">
        <h3 id={id} className="text-sm font-semibold">
          {title}
        </h3>
        <span aria-hidden="true" className="text-xs text-muted-foreground">
          {count}
        </span>
      </div>
      {children}
    </section>
  );
}
