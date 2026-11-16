interface FieldMessagesProps {
  /** L'identifiant du champ : `${id}-hint` et `${id}-error` sont ceux de `aria-describedby`. */
  id: string;
  hint: string | undefined;
  error: string | undefined;
}

/** L'indication et l'erreur d'un champ ; l'erreur est annoncée (`role="alert"`). */
export function FieldMessages({ id, hint, error }: FieldMessagesProps) {
  return (
    <>
      {hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </>
  );
}
