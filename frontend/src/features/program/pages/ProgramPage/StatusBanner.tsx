import { CircleCheck, Loader2 } from "lucide-react";
import { t } from "@/shared/i18n/t";

/** Le bandeau d'un programme qui n'attend plus rien de January : validé, ou en cours de mise à jour. */
export function StatusBanner({ kind }: { kind: "validated" | "working" }) {
  const validated = kind === "validated";
  const Icon = validated ? CircleCheck : Loader2;
  return (
    <div role="status" className="flex items-start gap-3 rounded-xl border bg-card p-4">
      <Icon
        aria-hidden="true"
        className={`mt-0.5 size-5 shrink-0 ${validated ? "text-primary" : "animate-spin motion-reduce:animate-none"}`}
      />
      <div>
        <p className="font-semibold">
          {t(validated ? "program.validation.validated" : "program.validation.working")}
        </p>
        <p className="text-sm text-muted-foreground">
          {t(validated ? "program.validation.validatedHint" : "program.validation.workingHint")}
        </p>
      </div>
    </div>
  );
}
