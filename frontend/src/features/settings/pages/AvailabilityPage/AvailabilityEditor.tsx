import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { weeklyBudget } from "../../availabilitySettings";
import { AvailabilityFields } from "../../components/AvailabilityFields";
import { SaveBar } from "../../components/SaveBar";
import { useAvailabilityForm } from "../../hooks/useAvailabilityForm";
import type { SettingsOut } from "../../types";
import { Section } from "../../components/Section";
import { SessionFields } from "./SessionFields";

const SAVE_LABELS = {
  save: t("settings.availability.save"),
  saving: t("settings.availability.saving"),
  saved: t("settings.availability.saved"),
  unsaved: t("settings.availability.unsaved"),
};

/** Le formulaire de la disponibilité et du rythme (l'état est dans `useAvailabilityForm`). */
export function AvailabilityEditor({ settings }: { settings: SettingsOut }) {
  const form = useAvailabilityForm(settings);
  const { value, errors, refused, saver, edit } = form;
  return (
    <form onSubmit={form.submit} noValidate className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.availability.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.availability.intro")}</p>
      </header>
      <Section title={t("settings.availability.sections.time")}>
        <AvailabilityFields
          values={value}
          flags={errors}
          refused={{
            weekday: refused("weekday"),
            weekendMin: refused("weekendMin"),
            weekendMax: refused("weekendMax"),
          }}
          budget={weeklyBudget(value)}
          onChange={(key, text) => edit({ ...value, [key]: text })}
        />
      </Section>
      <SessionFields draft={value} errors={errors} refused={refused} onChange={edit} />
      {saver.error ? <InlineError message={errorMessage(saver.error)} /> : null}
      <SaveBar
        pending={saver.pending}
        saved={saver.saved}
        dirty={form.dirty}
        blocked={form.blocked}
        invalid={form.invalid}
        labels={SAVE_LABELS}
      />
    </form>
  );
}
