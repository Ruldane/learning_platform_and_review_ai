import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ItemEdit, NewItem } from "../viewTypes";
import { buildValue, isValid, showLevel, toDraft, type Draft } from "./itemFormModel";
import { KindLevelFields } from "./KindLevelFields";
import { TextFields } from "./TextFields";

interface MemoryItemFormProps {
  initial: ItemEdit | null;
  chooseKind: boolean;
  disabled: boolean;
  onSubmit: (value: ItemEdit | NewItem) => void;
  onCancel: () => void;
}

/** Formulaire de création (type au choix) ou de modification d'un élément de mémoire. */
export function MemoryItemForm({
  initial,
  chooseKind,
  disabled,
  onSubmit,
  onCancel,
}: MemoryItemFormProps) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(initial));
  const patch = (change: Partial<Draft>) => setDraft((current) => ({ ...current, ...change }));
  const canSubmit = !disabled && isValid(draft);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit) onSubmit(buildValue(draft, chooseKind, initial));
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <KindLevelFields
        draft={draft}
        chooseKind={chooseKind}
        withLevel={showLevel(draft, chooseKind, initial)}
        disabled={disabled}
        onChange={patch}
      />
      <TextFields draft={draft} disabled={disabled} onChange={patch} />
      <div className="flex gap-2">
        <Button type="submit" disabled={!canSubmit}>
          {t("memory.button.save")}
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          {t("memory.button.cancel")}
        </Button>
      </div>
    </form>
  );
}
