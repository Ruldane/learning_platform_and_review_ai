import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface AccountMenuProps {
  email: string;
  onLogout: () => void;
  pending: boolean;
  failed: boolean;
}

/** Le compte connecté (barre du haut) : son adresse et « Se déconnecter ». */
export function AccountMenu({ email, onLogout, pending, failed }: AccountMenuProps) {
  return (
    <div role="group" aria-label={t("auth.account.label")} className="flex items-center gap-2">
      <span className="max-w-48 truncate text-sm text-muted-foreground" title={email}>
        {email}
      </span>
      <Button
        variant="ghost"
        size="sm"
        aria-disabled={pending}
        onClick={() => {
          if (!pending) onLogout();
        }}
      >
        {pending ? t("auth.account.loggingOut") : t("auth.account.logout")}
      </Button>
      {failed ? (
        <span role="alert" className="text-sm text-destructive">
          {t("auth.account.logoutFailed")}
        </span>
      ) : null}
    </div>
  );
}
