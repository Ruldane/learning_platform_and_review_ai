import { t } from "@/shared/i18n/t";
import type { FrozenWatchView } from "../viewTypes";

interface Props {
  experiment: FrozenWatchView;
  focusResult?: boolean;
}

export function FrozenExperiment({ experiment, focusResult }: Props) {
  const methods = [
    [t("contradictoryWatch.protocol"), experiment.protocol],
    [t("contradictoryWatch.criterion"), experiment.criterion],
  ];
  return (
    <div className="grid gap-4">
      <ol className="grid gap-3 sm:grid-cols-2">
        {experiment.sources.map((source) => (
          <li
            key={JSON.stringify([source.link, source.version])}
            className="grid gap-1 rounded border p-3"
          >
            <a className="break-all underline" href={source.link} rel="noreferrer">
              {source.link}
            </a>
            <span className="text-sm text-muted-foreground">{source.version}</span>
            <blockquote className="whitespace-pre-wrap break-words">{source.claim}</blockquote>
          </li>
        ))}
      </ol>
      <dl className="grid gap-2">
        {methods.map(([label, value]) => (
          <div key={label}>
            <dt className="font-medium">{label}</dt>
            <dd className="whitespace-pre-wrap break-words">{value}</dd>
          </div>
        ))}
      </dl>
      {experiment.result && (
        <section
          className="grid gap-2 rounded border p-3"
          aria-label={t("contradictoryWatch.completed")}
        >
          <h2
            className="font-semibold focus-visible:outline"
            tabIndex={-1}
            ref={focusResult ? (heading) => heading?.focus() : undefined}
          >
            {t("contradictoryWatch.completed")}
          </h2>
          <p className="whitespace-pre-wrap break-words">{experiment.result.text}</p>
          <p>{t(`contradictoryWatch.outcomes.${experiment.result.verdict}`)}</p>
        </section>
      )}
    </div>
  );
}
