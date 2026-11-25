import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";

interface LoginCardProps {
  /** The start address for Google (plain link: the browser leaves the app). */
  href: string;
  /** Why the previous sign-in failed, when returning from Google with an error. */
  errorMessage?: string | null;
}

/**
 * The login card: a « Se connecter avec Google » link and, if needed, the reason for a failure.
 */
export function LoginCard({ href, errorMessage }: LoginCardProps) {
  return (
    <section className="flex flex-col gap-4 rounded-xl border border-border bg-card px-6 py-8">
      <p className="text-muted-foreground">{t("auth.login.intro")}</p>
      {errorMessage ? (
        <p
          role="alert"
          className="rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive"
        >
          {errorMessage}
        </p>
      ) : null}
      <a href={href} className={cn(buttonVariants({ size: "lg" }), "self-start")}>
        {t("auth.login.google")}
      </a>
      <p className="text-sm text-muted-foreground">{t("auth.login.privacy")}</p>
    </section>
  );
}
