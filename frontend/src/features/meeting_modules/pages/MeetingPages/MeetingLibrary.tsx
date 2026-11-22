import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listMeetings, meetingPath, meetingsKey, prepareMeeting } from "../../api";
import { MeetingInput } from "../../components/MeetingInput";

export function MeetingLibrary() {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const history = useQuery({
    queryKey: meetingsKey,
    queryFn: ({ signal }) => listMeetings(signal),
  });
  const prepare = useMutation({
    mutationFn: prepareMeeting,
    onSuccess: (module) => {
      void cache.invalidateQueries({ queryKey: meetingsKey });
      void navigate(`${meetingPath}/${module.id}`);
    },
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <h1 className="text-2xl font-semibold">{t("meetingModules.title")}</h1>
      <p>{t("meetingModules.intro")}</p>
      {prepare.isError && <InlineError message={errorMessage(prepare.error)} />}
      <MeetingInput
        busy={prepare.isPending}
        onPrepare={(title, transcript) => prepare.mutate({ title, transcript })}
      />
      <h2 className="font-semibold">{t("meetingModules.library")}</h2>
      {history.isPending && <LoadingState label={t("meetingModules.loading")} />}
      {history.isError && (
        <ErrorState message={errorMessage(history.error)} onRetry={() => void history.refetch()} />
      )}
      {history.data?.length === 0 && <p>{t("meetingModules.empty")}</p>}
      <ul className="list-disc pl-5">
        {history.data?.map((item) => (
          <li key={item.id}>
            <Link className="underline" to={`${meetingPath}/${item.id}`}>
              {item.title}
            </Link>
            {" · "}
            {t(`meetingModules.${item.status}`)}
          </li>
        ))}
      </ul>
    </main>
  );
}
