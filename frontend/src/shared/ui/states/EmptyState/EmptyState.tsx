import { Button } from "@/shared/ui/button";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  /** `h1` quand l'état remplace toute la page (ex. fiche introuvable) ; `h2` sinon. */
  as?: "h1" | "h2";
}

/** État « rien à afficher » : titre, explication facultative et action facultative. */
export function EmptyState({ title, description, action, as: Heading = "h2" }: EmptyStateProps) {
  return (
    <section className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center">
      <Heading className="text-lg font-medium">{title}</Heading>
      {description ? <p className="max-w-prose text-muted-foreground">{description}</p> : null}
      {action ? (
        <Button className="mt-2" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </section>
  );
}
