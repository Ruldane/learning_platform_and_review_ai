import { fieldClass } from "@/shared/ui/fieldClass";

interface DraftFieldProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  /** Ce qui ne va pas avec ce brouillon (client ou serveur), dit sous le texte. */
  message: string | null;
}

/** Le texte modifiable d'un brouillon et son message d'erreur. */
export function DraftField({ id, value, onChange, message }: DraftFieldProps) {
  return (
    <>
      <textarea
        id={id}
        rows={6}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={message !== null}
        aria-describedby={message ? `${id}-error` : undefined}
        className={`${fieldClass} h-auto py-2`}
      />
      {message ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {message}
        </p>
      ) : null}
    </>
  );
}
