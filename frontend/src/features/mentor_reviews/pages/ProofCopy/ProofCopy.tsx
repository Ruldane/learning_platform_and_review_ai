import { t } from "@/shared/i18n/t";
import type { Manifest } from "../../api";

export function ProofCopy({ manifest, digest }: { manifest: Manifest; digest: string }) {
  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-semibold">{manifest.title}</h3>
      <dl className="space-y-1 text-sm">
        <dt>{t("mentorReviews.digest")}</dt>
        <dd className="break-all font-mono">{digest}</dd>
      </dl>
      {manifest.proofs.map((proof) => (
        <article className="rounded-lg border border-border p-4" key={proof.proof_id}>
          <h4 className="font-semibold">
            {t("mentorReviews.source", { title: proof.title, revision: proof.revision })}
          </h4>
          <p className="mt-2 whitespace-pre-wrap break-words">{proof.artifact}</p>
          <dl className="mt-2 space-y-1 text-sm">
            <dt>{t("proofPackets.identifier")}</dt>
            <dd className="break-all font-mono">{proof.proof_id}</dd>
            <dt>{t("proofPackets.artifactDigest")}</dt>
            <dd className="break-all font-mono">{proof.artifact_digest}</dd>
          </dl>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {proof.measurements.map((measure) => (
              <li key={measure.index}>
                {measure.label} · {t("proofPackets.measure", {
                  observed: measure.observed, target: measure.target,
                })}
              </li>
            ))}
          </ul>
        </article>
      ))}
      <h4 className="font-semibold">{t("proofPackets.procedure")}</h4>
      <ol className="list-decimal pl-5">
        {manifest.procedure.map((step) => <li key={step}>{step}</li>)}
      </ol>
    </div>
  );
}
