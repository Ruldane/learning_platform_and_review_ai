import { useContext, useId, useState, type ReactNode } from "react";
import { FieldErrorsContext, hasErrorUnder } from "./fieldErrors";

interface SectionProps {
  title: string;
  /** Nombre de lignes, pour les sections en liste. */
  count?: number;
  /** Préfixe des chemins d'erreur de la section : elle reste ouverte tant qu'une erreur y est. */
  path: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

/** Une section repliable du formulaire : un bouton d'ouverture, le contenu dessous. */
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
