import { useRef, useState } from "react";
import { useLabPreferences } from "@/features/lab/hooks/useLabPreferences";
import { t } from "@/shared/i18n/t";
import { usePrefersReducedMotion } from "@/shared/session-ui/Board/usePrefersReducedMotion";
import { Button } from "@/shared/ui/button";

const STEPS = ["home", "learn", "memory", "lab"] as const;

export function Tour() {
  const reduced = usePrefersReducedMotion();
  const { preferences, save } = useLabPreferences(!reduced);
  const [step, setStep] = useState<number | null>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  if (reduced || !preferences.data) return null;
  const disabled = preferences.data.tour === "disabled";
  const close = () => {
    setStep(null);
    trigger.current?.focus();
  };
  return (
    <section aria-label={t("navigation.tour.title")} className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        <Button ref={trigger} type="button" size="sm" variant="outline" disabled={save.isPending}
          onClick={() => {
            if (disabled) save.mutate({ tour: "pending" });
            setStep(0);
          }}>
          {t(preferences.data.tour === "pending" ? "navigation.tour.start" : "navigation.tour.restart")}
        </Button>
        {disabled ? null : <Button type="button" size="sm" variant="ghost" disabled={save.isPending}
          onClick={() => { close(); save.mutate({ tour: "disabled" }); }}>
          {t("navigation.tour.disable")}
        </Button>}
      </div>
      {step === null ? null : (
        <div className="grid gap-2 rounded-xl border bg-card p-4">
          <p aria-live="polite" className="text-sm font-medium">
            {t("navigation.tour.step", { step: step + 1, total: STEPS.length })}
            {" · "}{t(`navigation.tour.${STEPS[step] ?? "home"}`)}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" disabled={step === 0}
              onClick={() => setStep(step - 1)}>{t("navigation.tour.previous")}</Button>
            <Button type="button" size="sm" onClick={() => {
              if (step < STEPS.length - 1) setStep(step + 1);
              else { close(); save.mutate({ tour: "done" }); }
            }}>{t(step === STEPS.length - 1 ? "navigation.tour.finish" : "navigation.tour.next")}</Button>
            <Button type="button" size="sm" variant="ghost" onClick={close}>{t("navigation.tour.close")}</Button>
          </div>
        </div>
      )}
    </section>
  );
}
