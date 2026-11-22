import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Manifest } from "../../api";
import { ProofEvidence } from "../ProofEvidence";

interface Props {
  manifest: Manifest;
  digest: string;
  onSave?: () => void;
  onExport?: () => void;
  busy: boolean;
}

export function ManifestPreview({ manifest, digest, onSave, onExport, busy }: Props) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby="proof-manifest">
      <h2 id="proof-manifest" tabIndex={-1} className="text-lg font-semibold">
        {t("proofPackets.previewTitle")}
      </h2>
      <h3 className="font-semibold">{manifest.title}</h3>
      <dl className="space-y-1 text-sm">
        <dt>{t("proofPackets.digest")}</dt>
        <dd className="break-all font-mono">{digest}</dd>
      </dl>
      {manifest.proofs.map((proof) => <ProofEvidence key={proof.proof_id} proof={proof} />)}
      <h3 className="font-semibold">{t("proofPackets.procedure")}</h3>
      <ol className="list-decimal space-y-1 pl-5">
        {manifest.procedure.map((step) => <li key={step}>{step}</li>)}
      </ol>
      {onSave && (
        <Button type="button" className="self-start" onClick={onSave} disabled={busy}>
          {t("proofPackets.save")}
        </Button>
      )}
      {onExport && (
        <Button type="button" className="self-start" onClick={onExport} disabled={busy}>
          {t("proofPackets.export")}
        </Button>
      )}
    </section>
  );
}
