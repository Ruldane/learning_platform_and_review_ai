import { t } from "@/shared/i18n/t";
import type { Manifest } from "../../api";

export function ProofEvidence({ proof }: { proof: Manifest["proofs"][number] }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <h4 className="font-semibold">
        {t("proofPackets.source", { title: proof.title, revision: proof.revision })}
      </h4>
      <dl className="grid gap-1 text-sm">
        <dt>{t("proofPackets.identifier")}</dt>
        <dd className="break-all font-mono">{proof.proof_id}</dd>
        <dt>{t("proofPackets.artifactDigest")}</dt>
        <dd className="break-all font-mono">{proof.artifact_digest}</dd>
      </dl>
      <p className="whitespace-pre-wrap break-words">{proof.artifact}</p>
      <p className="text-sm font-semibold">{t("proofPackets.measurements")}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        {proof.measurements.map((measure) => (
          <li key={measure.index}>
            {measure.label} · {t("proofPackets.measure", {
              observed: measure.observed, target: measure.target,
            })}
          </li>
        ))}
      </ul>
    </article>
  );
}
