import { useLocation, useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import type { FeynmanEntry } from "../../feynmanApi";
import { FeynmanThread } from "./FeynmanThread";

function selectedFile(value: unknown): string | undefined {
  if (typeof value === "object" && value && "path" in value && typeof value.path === "string") {
    return value.path;
  }
}

export function FeynmanPage() {
  const { lessonId, sessionId, turnId } = useParams();
  const path = selectedFile(useLocation().state);
  const entry: FeynmanEntry | null = lessonId
    ? { kind: "lesson", id: lessonId }
    : sessionId
      ? { kind: "ide", id: sessionId, path }
      : turnId
        ? { kind: "saved", id: turnId }
        : null;
  return (
    <section className="flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-semibold">{t("feynman.title")}</h1>
      {entry && <FeynmanThread key={`${entry.kind}:${entry.id}:${path ?? ""}`} entry={entry} />}
    </section>
  );
}
