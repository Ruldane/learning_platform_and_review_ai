import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

export function LabReadiness({
  missing,
  pending,
  unavailable,
}: {
  missing: string[];
  pending: boolean;
  unavailable: boolean;
}) {
  const needsAudio = missing.includes("openai_audio");
  const status = pending
    ? "checking"
    : unavailable
      ? "unknown"
      : missing.length
        ? "configure"
        : "ready";
  return (
    <div className="grid gap-1">
      <p className="text-sm font-medium text-muted-foreground">{t(`navigation.${status}`)}</p>
      {needsAudio && <p className="text-sm">{t("navigation.podcastAudioKey")}</p>}
      {(needsAudio || missing.includes("models")) && (
        <Link to="/reglages/modeles" className="text-sm underline">
          {t("navigation.modelsLink")}
        </Link>
      )}
    </div>
  );
}
