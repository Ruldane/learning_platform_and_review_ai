import { useMemo } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { SkillDrawer } from "../../components/SkillDrawer";
import { useSkillDetail } from "../../hooks/useSkillDetail";
import { toDetailView } from "../../toView";

interface SkillDetailSlotProps {
  /** `null` : rien d'ouvert. */
  skillId: string | null;
  onClose: () => void;
}

/** Le tiroir d'une compétence : chargement, erreur avec « Réessayer » et « Fermer », puis le détail. */
export function SkillDetailSlot({ skillId, onClose }: SkillDetailSlotProps) {
  const query = useSkillDetail(skillId);
  const view = useMemo(() => (query.data ? toDetailView(query.data) : null), [query.data]);
  if (skillId === null) return null;
  if (view) return <SkillDrawer detail={view} onClose={onClose} />;
  if (query.isError) {
    return (
      <div className="flex flex-col items-center gap-2">
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
        <Button variant="outline" onClick={onClose}>
          {t("skills.drawer.close")}
        </Button>
      </div>
    );
  }
  return <LoadingState label={t("skills.page.detailLoading")} />;
}
