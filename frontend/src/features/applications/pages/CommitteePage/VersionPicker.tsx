import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ChoiceSelect } from "../../components/DraftField/ChoiceSelect";
import { Field } from "../../components/Field";
import type { ReadyVersion } from "../../hooks/useCvVersions";

function launchLabel(pending: boolean, hasRuns: boolean): string {
  if (pending) return t("applications.committeeControls.starting");
  return t(
    hasRuns ? "applications.committeeControls.relaunch" : "applications.committeeControls.launch",
  );
}

interface VersionPickerProps {
  versions: ReadyVersion[];
  selected: ReadyVersion;
  busy: boolean;
  hasRuns: boolean;
  pending: boolean;
  onChoose: (versionId: string) => void;
  onLaunch: (versionId: string) => void;
}

/** La liste des versions prêtes et le bouton qui lance (ou relance) le comité sur celle qui est choisie. */
export function VersionPicker({
  versions,
  selected,
  busy,
  hasRuns,
  pending,
  onChoose,
  onLaunch,
}: VersionPickerProps) {
  const choices = versions.map((version) => ({
    value: version.id,
    label: t("applications.committeeControls.versionOption", { number: version.number }),
  }));
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="w-56">
        <Field label={t("applications.committeeControls.version")}>
          {(control) => (
            <ChoiceSelect
              control={control}
              value={selected.id}
              choices={choices}
              disabled={busy}
              onChange={onChoose}
            />
          )}
        </Field>
      </div>
      <Button type="button" disabled={busy} onClick={() => onLaunch(selected.id)}>
        {launchLabel(pending, hasRuns)}
      </Button>
    </div>
  );
}
