import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { BraveUsageView, SearchSettingsView, SettingsOut } from "../../types";
import { toSearchSettingsView } from "../../userSettings";
import { useSaveSearchSettings } from "../../hooks/useSaveSearchSettings";
import { SearchSettingsSections } from "./SearchSettingsSections";

interface SearchSettingsEditorProps {
  settings: SettingsOut;
  usage: BraveUsageView;
}

const sameSettings = (a: SearchSettingsView, b: SearchSettingsView) =>
  JSON.stringify(a) === JSON.stringify(b);

/**
 * Le formulaire des réglages de recherche. Le brouillon n'existe que pendant l'édition (`null` :
 * on montre les réglages du serveur). L'enregistrement se fait par bouton, jamais à la frappe :
 * les plafonds transmettent des valeurs intermédiaires (D79). En cas d'échec le brouillon reste.
 */
export function SearchSettingsEditor({ settings, usage }: SearchSettingsEditorProps) {
  const stored = toSearchSettingsView(settings);
  const [draft, setDraft] = useState<SearchSettingsView | null>(null);
  const saver = useSaveSearchSettings(settings);
  const value = draft ?? stored;
  const dirty = draft !== null && !sameSettings(draft, stored);

  const edit = (next: SearchSettingsView) => {
    saver.reset();
    setDraft(next);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!dirty || saver.pending || draft === null) return;
    saver.save(draft).then(
      () => setDraft(null),
      () => undefined, // l'erreur est affichée depuis la mutation ; la saisie est gardée
    );
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.search.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.search.intro")}</p>
        <Link to="/reglages/recherche/essai" className="mt-2 inline-block text-sm underline">
          {t("settings.search.tryBench")}
        </Link>
      </header>
      <SearchSettingsSections value={value} usage={usage} onChange={edit} />
      {saver.error ? <InlineError message={errorMessage(saver.error)} /> : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={!dirty || saver.pending}>
          {saver.pending ? t("settings.search.saving") : t("settings.search.save")}
        </Button>
        <p role="status" className="text-sm text-muted-foreground">
          {saver.saved && !dirty ? t("settings.search.saved") : null}
          {dirty && !saver.pending ? t("settings.search.unsaved") : null}
        </p>
      </div>
    </form>
  );
}
