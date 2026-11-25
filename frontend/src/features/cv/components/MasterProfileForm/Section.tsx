import { useContext, useId, useState, type ReactNode } from "react";
import { FieldErrorsContext, hasErrorUnder } from "./fieldErrors";

interface SectionProps {
  title: string;
  /** Number of rows, for list sections. */
  count?: number;
  /** Prefix of the section's error paths: it stays open while an error is in it. */
  path: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** A collapsible form section: an open button, the content below it. */
export function Section({ title, count, path, defaultOpen = false, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  const errors = useContext(FieldErrorsContext);
  const shown = open || hasErrorUnder(errors, path);
  return (
    <section className="rounded-xl border bg-card">
      <h3>
        <button
          type="button"
          aria-expanded={shown}
          aria-controls={`${id}-body`}
          onClick={() => setOpen(!shown)}
          className="flex w-full items-center justify-between rounded-xl px-4 py-3 text-left font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring"
        >
          <span>
            {title}
            {count === undefined ? "" : ` (${count})`}
          </span>
          <span aria-hidden="true">{shown ? "−" : "+"}</span>
        </button>
      </h3>
      {shown ? (
        <div id={`${id}-body`} className="flex flex-col gap-3 border-t px-4 py-3">
          {children}
        </div>
      ) : null}
    </section>
  );
}
