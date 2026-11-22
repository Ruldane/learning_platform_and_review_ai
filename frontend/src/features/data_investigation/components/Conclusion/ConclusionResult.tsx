import { t } from "@/shared/i18n/t";

interface Props {
  integrity: boolean;
  matches: boolean;
  expected: { deliveries: number; units: number };
  focus: boolean;
}

export function ConclusionResult({ integrity, matches, expected, focus }: Props) {
  return (
    <section className="grid gap-2 rounded border p-3">
      <h2
        className="font-semibold"
        tabIndex={-1}
        ref={focus ? (heading) => heading?.focus() : undefined}
      >
        {t("dataInvestigation.result")}
      </h2>
      <p>{t(integrity ? "dataInvestigation.pass" : "dataInvestigation.review")}</p>
      <p>{t(matches ? "dataInvestigation.matches" : "dataInvestigation.mismatch")}</p>
      <p>{t("dataInvestigation.expected", expected)}</p>
    </section>
  );
}
