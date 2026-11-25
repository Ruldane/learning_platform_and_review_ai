interface FieldMessagesProps {
  /** The field's id: `${id}-hint` and `${id}-error` are the `aria-describedby` ones. */
  id: string;
  hint: string | undefined;
  error: string | undefined;
}

/** A field's hint and error; the error is announced (`role="alert"`). */
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
