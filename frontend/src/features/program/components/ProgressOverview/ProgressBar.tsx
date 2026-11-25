interface ProgressBarProps {
  /** Accessible name of the bar. */
  label: string;
  /** Share done, from 0 to 100. */
  percent: number;
}

/** Progress bar; the value stays readable as text beside it, never by colour alone. */
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
