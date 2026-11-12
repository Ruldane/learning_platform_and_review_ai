interface ProgressBarProps {
  /** Nom accessible de la barre. */
  label: string;
  /** Part faite, de 0 à 100. */
  percent: number;
}

/** Barre d'avancement ; la valeur reste lisible en texte à côté, jamais seulement par la couleur. */
export function ProgressBar({ label, percent }: ProgressBarProps) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-200 motion-reduce:transition-none"
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}
