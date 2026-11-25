import { useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { ApplicationCheck } from "../../components/ApplicationCheck";
import { useApplicationCheck } from "../../hooks/useApplicationCheck";
import { useCreateFromPosting } from "../../hooks/useCreateFromPosting";
import { toApplicationAlertView, toExistingApplicationView } from "../../toView";

const applicationPath = (applicationId: string) => `/applications/${applicationId}`;

/**
 * The posting's application: the existing one, and the duplicate alert when records
 * resemble it, and « Créer la candidature ». « C'est un autre poste » creates the record
 * despite the similar ones; the new record opens, with any « même entreprise » details.
 */
export function ApplicationBlock({ postingId }: { postingId: string }) {
  const navigate = useNavigate();
  const check = useApplicationCheck(postingId);
  const creation = useCreateFromPosting(postingId);
  const [dismissed, setDismissed] = useState(false);

  if (check.isPending) return <LoadingState label={t("applications.check.loading")} />;
  if (check.isError) {
    return (
      <InlineError
        message={`${t("applications.check.failed")} ${errorMessage(check.error)}`}
        onRetry={() => void check.refetch()}
      />
    );
  }

  const blocking = creation.conflict.length > 0 ? creation.conflict : check.data.alerts;
  const { own } = check.data;
  const open = (id: string) => void navigate(applicationPath(id));

  async function create(distinctFrom: string[] = []) {
    setDismissed(false);
    const created = await creation.create(distinctFrom);
    if (created) void navigate(applicationPath(created.id), { state: { info: created.info } });
  }

  return (
    <ApplicationCheck
      own={own ? toExistingApplicationView(own) : null}
      alerts={[...(dismissed ? [] : blocking), ...check.data.info].map(toApplicationAlertView)}
      creating={creation.pending}
      error={creation.error}
      onOpen={open}
      onCreate={() => void create()}
      onDistinct={() => void create(blocking.map((alert) => alert.application_id))}
      onCancel={() => setDismissed(true)}
    />
  );
}
