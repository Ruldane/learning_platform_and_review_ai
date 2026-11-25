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
 * Shows Google sign-in and callback errors. A local account goes straight to the app.
 */
export function LoginPage() {
  const me = useMe();
  const [params] = useSearchParams();
  if (me.data?.auth_mode === "local") return <Navigate to="/" replace />;
  const code = params.get("error") ?? params.get("erreur");
  let body = <LoginCard href={loginUrl()} errorMessage={loginErrorMessage(code)} />;
  if (me.isPending) body = <LoadingState label={t("auth.gate.checking")} />;
  else if (me.isError) {
    body = <ErrorState message={errorMessage(me.error)} onRetry={() => void me.refetch()} />;
  }
  return (
    <PublicPage title={t("auth.login.title")} settled={!me.isError}>
      {body}
    </PublicPage>
  );
}
