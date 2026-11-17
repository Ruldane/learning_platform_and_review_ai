import { Navigate, useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { loginUrl } from "../../api";
import { LoginCard } from "../../components/LoginCard";
import { PublicPage } from "../../components/PublicPage";
import { useMe } from "../../hooks/useMe";
import { loginErrorMessage } from "../../loginErrors";

/**
 * `/connexion` (publique) : « Se connecter avec Google » et, au retour d'un échec,
 * `?erreur=<code>` en message français. En mode local il n'y a rien à ouvrir : retour à `/`.
 * Elle ne renvoie jamais vers `/` quand `me` répond 401 (la porte y renverrait aussitôt) ni quand
 * un compte Google est déjà ouvert : seul le mode local, qui ne répond jamais 401, repart.
 */
export function LoginPage() {
  const me = useMe();
  const [params] = useSearchParams();
  if (me.data?.auth_mode === "local") return <Navigate to="/" replace />;
  let body = <LoginCard href={loginUrl()} errorMessage={loginErrorMessage(params.get("erreur"))} />;
  if (me.isPending) body = <LoadingState label={t("auth.gate.checking")} />;
  else if (me.isError) {
    body = <ErrorState message={errorMessage(me.error)} onRetry={() => void me.refetch()} />;
  }
  return <PublicPage title={t("auth.login.title")}>{body}</PublicPage>;
}
