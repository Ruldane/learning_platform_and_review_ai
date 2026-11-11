import { Button } from "@/shared/ui/button";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

/** État « rien à afficher » : titre, explication facultative et action facultative. */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-card px-6 py-10 text-center">
      <h2 className="text-lg font-medium">{title}</h2>
      {description ? <p className="max-w-prose text-muted-foreground">{description}</p> : null}
      {action ? (
        <Button className="mt-2" onClick={action.onClick}>
          {action.label}
        </Button>
      ) : null}
    </section>
  );
}
