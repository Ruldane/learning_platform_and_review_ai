import { useId } from "react";
import { fieldClass } from "@/shared/ui/fieldClass";

interface ModelFieldProps {
  /** Étiquette lue par les lecteurs d'écran (le champ n'a pas de texte visible). */
  label: string;
  /** Modèles proposés, ou `null` pour une saisie libre. */
  models: string[] | null;
  /** Modèle en vigueur (saisie libre : vide quand on attend un nouveau modèle). */
  value: string;
  disabled?: boolean;
  /** Liste : à chaque choix. Saisie libre : à la perte du focus ou à Entrée, une fois par saisie. */
  onCommit: (model: string) => void;
}

/** Modèle d'un niveau : liste déroulante, ou champ texte quand le fournisseur n'a pas de liste. */
export function ModelField({ label, models, value, disabled = false, onCommit }: ModelFieldProps) {
  const id = useId();
  return (
    <>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      {models ? (
        <select
          id={id}
          className={`${fieldClass} sm:max-w-64`}
          value={value}
          disabled={disabled}
          onChange={(event) => onCommit(event.target.value)}
        >
          {models.includes(value) ? null : <option value={value}>{value}</option>}
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      ) : (
        <input
          // La clé remet le champ à jour quand la valeur enregistrée change.
          key={value}
          id={id}
          type="text"
          className={`${fieldClass} sm:max-w-64`}
          defaultValue={value}
          disabled={disabled}
          spellCheck={false}
          onBlur={(event) => onCommit(event.currentTarget.value)}
          onKeyDown={(event) => {
            // Entrée valide comme la perte du focus (un seul chemin : onBlur).
            if (event.key === "Enter") event.currentTarget.blur();
          }}
        />
      )}
    </>
  );
}
