import type { ReactNode } from "react";

interface ProposalSectionProps {
  title: string;
  /** Une liste à puces… */
  items?: string[];
  /** …ou un texte. */
  children?: ReactNode;
}

/** Une rubrique d'une carte : son titre, puis une liste ou un texte. */
export function ProposalSection({ title, items, children }: ProposalSectionProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {title}
      </h4>
      {items ? (
        <ul className="list-disc pl-4">
          {items.map((item, index) => (
            // Deux puces peuvent porter le même texte : la position les distingue.
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        children
      )}
    </div>
  );
}
