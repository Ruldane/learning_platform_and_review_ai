/** Erreur d'une action, affichée dans la page sans la remplacer (annoncée par `role="alert"`). */
export function InlineError({ message }: { message: string }) {
  return (
    <p
      role="alert"
      className="rounded-lg border border-destructive/40 bg-card px-3 py-2 text-sm text-destructive"
    >
      {message}
    </p>
  );
}
