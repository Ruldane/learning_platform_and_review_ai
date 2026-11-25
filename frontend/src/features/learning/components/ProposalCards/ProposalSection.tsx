import type { ReactNode } from "react";

interface ProposalSectionProps {
  title: string;
  /** A bullet list… */
  items?: string[];
  /** …or a text. */
  children?: ReactNode;
}

/** A card section: its title, then a list or a text. */
export function ProposalSection({ title, items, children }: ProposalSectionProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {title}
      </h4>
      {items ? (
        <ul className="list-disc pl-4">
          {items.map((item, index) => (
            // Two bullets can carry the same text: the position tells them apart.
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        children
      )}
    </div>
  );
}
