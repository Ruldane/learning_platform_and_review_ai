import { t } from "@/shared/i18n/t";
import { buttonVariants } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";

interface LoginCardProps {
  /** L'adresse de départ vers Google (lien plein : le navigateur quitte l'application). */
  href: string;
  /** Pourquoi la connexion précédente a échoué, quand on revient de Google avec une erreur. */
  errorMessage?: string | null;
}

/** La carte de connexion : un lien « Se connecter avec Google » et, au besoin, la raison d'un échec. */
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
