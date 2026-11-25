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
 * The search settings form. The draft exists only while editing (`null`:
 * the server's settings are shown). Saving is by button, never on each keystroke:
 * the caps pass intermediate values (D79). On failure the draft stays.
 */
export function SearchSettingsEditor({ settings, usage }: SearchSettingsEditorProps) {
  const stored = toSearchSettingsView(settings);
  const [draft, setDraft] = useState<SearchSettingsView | null>(null);
  const saver = useSaveSearchSettings(settings);
  const value = draft ?? stored;
  const [capsInvalid, setCapsInvalid] = useState(false);
  const dirty = draft !== null && !sameSettings(draft, stored);

  const edit = (next: SearchSettingsView) => {
    saver.reset();
    setDraft(next);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    // Entry into an invalid cap: nothing is sent (the draft keeps the last valid value).
    if (!dirty || capsInvalid || saver.pending || draft === null) return;
    saver.save(draft).then(
      () => setDraft(null),
      () => undefined, // the error is shown from the mutation; the input is kept
    );
  };

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-8">
      <header>
        <h1 className="text-2xl font-semibold">{t("settings.search.title")}</h1>
        <p className="mt-2 text-muted-foreground">{t("settings.search.intro")}</p>
        <Link to="/settings/search/probe" className="mt-2 inline-block text-sm underline">
          {t("settings.search.tryBench")}
        </Link>
      </header>
      <SearchSettingsSections
        value={value}
        usage={usage}
        onChange={edit}
        onCapsInvalidChange={setCapsInvalid}
      />
      {saver.error ? <InlineError message={errorMessage(saver.error)} /> : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={!dirty || capsInvalid || saver.pending}>
          {saver.pending ? t("settings.search.saving") : t("settings.search.save")}
        </Button>
        <p role="status" className="text-sm text-muted-foreground">
          {saver.saved && !dirty ? t("settings.search.saved") : null}
          {dirty && !capsInvalid && !saver.pending ? t("settings.search.unsaved") : null}
        </p>
      </div>
    </form>
  );
}
