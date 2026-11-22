import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";

interface LessonVerificationProps {
  published: boolean;
  checking: boolean;
  failure: string | null | undefined;
}

export function LessonVerification({ published, checking, failure }: LessonVerificationProps) {
  const reason = checking ? null : failure;
  return (
    <section
      role={reason ? "alert" : "status"}
      aria-labelledby="lesson-verification-label"
      className={cn("rounded-xl border bg-card p-4", reason && "border-destructive/40")}
    >
      <p id="lesson-verification-label" className="font-semibold">
        {t(reason ? "lessons.verification.failed" : "lessons.status.verifying")}
      </p>
      <p className="mt-1 text-muted-foreground">
        {reason ??
          t(published ? "lessons.verification.revision" : "lessons.verification.firstDraft")}
      </p>
    </section>
  );
}
