import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ExpiryDays, FeatureOption, TokenDraft, TokenMode } from "../viewTypes";
import { DurationSelect } from "./DurationSelect";
import { FeaturePicker } from "./FeaturePicker";
import { ModeChoice } from "./ModeChoice";
import { NameField } from "./NameField";

const DEFAULT_DAYS: ExpiryDays = 30;

interface TokenFormProps {
  features: FeatureOption[];
  pending: boolean;
  onSubmit: (draft: TokenDraft) => void;
}

const toggled = (list: string[], item: string) =>
  list.includes(item) ? list.filter((entry) => entry !== item) : [...list, item];

/**
 * Crée un jeton : un nom, les features ouvertes, le mode (lecture seule d'office) et la durée
 * (30 jours d'office). Rien n'est coché au départ : on n'ouvre que ce qu'on choisit.
 */
export function TokenForm({ features, pending, onSubmit }: TokenFormProps) {
  const [label, setLabel] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [mode, setMode] = useState<TokenMode>("read");
  const [days, setDays] = useState<ExpiryDays>(DEFAULT_DAYS);
  const hintId = useId();
  const complete = label.trim() !== "" && selected.length > 0;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || pending) return;
    onSubmit({ label: label.trim(), features: selected, mode, expiresInDays: days });
  }

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4"
    >
      <h3 className="font-medium">{t("mcp.form.title")}</h3>
      <NameField value={label} onChange={setLabel} />
      <FeaturePicker
        options={features}
        selected={selected}
        onToggle={(feature) => setSelected((list) => toggled(list, feature))}
        onSelectAll={() => setSelected(features.map((option) => option.id))}
      />
      <ModeChoice value={mode} onChange={setMode} />
      <DurationSelect value={days} onChange={setDays} />
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={!complete || pending} aria-describedby={hintId}>
          {pending ? t("mcp.form.submitting") : t("mcp.form.submit")}
        </Button>
        <p id={hintId} className="text-sm text-muted-foreground">
          {complete ? "" : t("mcp.form.incomplete")}
        </p>
      </div>
    </form>
  );
}
