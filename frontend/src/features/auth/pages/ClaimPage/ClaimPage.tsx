import { useNavigate } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ClaimChoice, type Choice } from "../../components/ClaimChoice";
import { PublicPage } from "../../components/PublicPage";
import { useClaim } from "../../hooks/useClaim";

/** These refusals return to sign-in: no choice left to make (or no cookie). */
const BACK_TO_LOGIN = new Set(["claim_expired", "local_already_claimed"]);

function sendsBackToLogin(error: unknown): error is ApiError {
  return error instanceof ApiError && BACK_TO_LOGIN.has(error.code);
}

/**
 * `/login/claim` (public): the very first Google sign-in choice. On success, the
 * app opens; an expired cookie (409 `claim_expired`) returns to `/login` with its
 * message; any other error stays here, under the buttons.
 */
export function ClaimPage() {
  const navigate = useNavigate();
  const claim = useClaim();
  const choose = (choice: Choice) =>
    claim.mutate(choice, {
      onSuccess: () => void navigate("/", { replace: true }),
      onError: (error) => {
        if (sendsBackToLogin(error))
          void navigate(`/login?error=${error.code}`, { replace: true });
      },
    });
  const failed = claim.isError && !sendsBackToLogin(claim.error);
  return (
    <PublicPage title={t("auth.claim.title")}>
      <ClaimChoice
        onChoose={choose}
        pending={claim.isPending}
        error={failed ? errorMessage(claim.error) : null}
      />
    </PublicPage>
  );
}
