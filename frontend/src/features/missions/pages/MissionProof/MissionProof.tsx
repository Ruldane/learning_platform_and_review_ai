import { t } from "@/shared/i18n/t";
import type { Mission } from "../../api";

export function MissionProof({ submission }: { submission: NonNullable<Mission["submission"]> }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="font-semibold">{t("missions.proof")}</h3>
      <p className="break-words font-mono">{submission.proof_id}</p>
      <h3 className="font-semibold">{t("missions.artifact")}</h3>
      <p className="whitespace-pre-wrap break-words">{submission.artifact}</p>
    </section>
  );
}
