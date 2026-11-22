import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Evidence } from "../../api";
import { EvidenceCard } from "../EvidenceCard";
import { EvidencePicker } from "../EvidencePicker";
import { HypothesisFields, type HypothesisDraft } from "../HypothesisFields";
import { useObservation } from "./useObservation";

export function ObservationForm({ evidence }: { evidence: Evidence[] }) {
  const [selected, setSelected] = useState("");
  const [draft, setDraft] = useState<HypothesisDraft>({ label: "", confidence: "low" });
  const add = useObservation();
  const source = evidence.find(({ reference }) => JSON.stringify(reference) === selected);
  const canSave = source && draft.label.trim().length >= 2 && !add.isPending;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSave)
          add.mutate({
            reference: source.reference,
            hypothesis: draft.label,
            confidence: draft.confidence,
          });
      }}
    >
      <EvidencePicker
        evidence={evidence}
        selected={selected}
        onChange={(key) => {
          add.reset();
          setSelected(key);
        }}
      />
      {source && <EvidenceCard value={source} />}
      <HypothesisFields draft={draft} onChange={setDraft} />
      {add.isSuccess && <p role="status">{t("errorAtlas.saved")}</p>}
      {add.isError && <p role="alert">{errorMessage(add.error)}</p>}
      <Button type="submit" className="self-start" aria-disabled={!canSave}>
        {t("errorAtlas.record")}
      </Button>
    </form>
  );
}
