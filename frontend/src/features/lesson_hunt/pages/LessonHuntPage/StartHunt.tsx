import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { startHunt } from "../../api";
export function StartHunt({ lessonId }: { lessonId: string }) {
  const navigate = useNavigate();
  const start = useMutation({
    mutationFn: () => startHunt(lessonId),
    onSuccess: ({ hunt_id }) => void navigate("/apprendre/erreurs/" + encodeURIComponent(hunt_id)),
  });
  return (
    <>
      <p>{t("lessonHunt.intro")}</p>
      <Button
        type="button"
        className="w-fit"
        disabled={start.isPending}
        onClick={() => start.mutate()}
      >
        {t("lessonHunt.start")}
      </Button>
      {start.isError ? <p role="alert">{errorMessage(start.error)}</p> : null}
    </>
  );
}
