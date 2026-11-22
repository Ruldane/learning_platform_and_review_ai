import { useRef, type FormEvent } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { ComparisonButtons } from "../ComparisonButtons";
import { OfferPairFields } from "../OfferPairFields";
import { RuleFields } from "../RuleFields";
import type { useComparison } from "../useComparison";

type Screen = ReturnType<typeof useComparison>;

function useEditorCommands(screen: Screen) {
  const status = useRef<HTMLParagraphElement>(null);
  function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!screen.pair) return;
    status.current?.focus();
    screen.preview.mutate(screen.pair);
  }
  function saveRules() {
    if (!screen.rules) return;
    status.current?.focus();
    screen.rulesSave.mutate(screen.rules);
  }
  function save() {
    if (!screen.pair) return;
    status.current?.focus();
    screen.save.mutate(screen.pair);
  }
  return { status, compare, saveRules, save };
}

export function ComparisonEditor({ screen }: { screen: Screen }) {
  const { status, compare, saveRules, save } = useEditorCommands(screen);
  const { options, rules, editable } = screen;
  const error = screen.preview.error ?? screen.rulesSave.error ?? screen.save.error;
  if (!options.data || !rules || !editable) return null;
  const notice = screen.preview.isSuccess
    ? "computed"
    : screen.rulesSave.isSuccess
      ? "rulesSaved"
      : null;
  return (
    <form className="grid gap-3 rounded-xl border bg-card p-4" onSubmit={compare}>
      <fieldset className="grid gap-3" disabled={screen.busy}>
        <OfferPairFields
          options={options.data}
          first={screen.first}
          second={screen.second}
          onFirst={screen.setFirst}
          onSecond={screen.setSecond}
        />
        <RuleFields rules={editable} onChange={screen.setRules} />
        {!screen.validWeights && <p className="text-sm">{t("offerComparison.needWeight")}</p>}
        <ComparisonButtons
          canSaveRules={screen.validWeights}
          canCompare={Boolean(screen.pair)}
          canSave={Boolean(screen.pair && screen.preview.data)}
          onSaveRules={saveRules}
          onSave={save}
        />
      </fieldset>
      <p
        tabIndex={-1}
        ref={status}
        role="status"
        className="focus:outline focus:outline-2 focus:outline-ring"
      >
        {screen.busy ? t("offerComparison.loading") : notice ? t(`offerComparison.${notice}`) : ""}
      </p>
      {error && <InlineError message={errorMessage(error)} />}
    </form>
  );
}
