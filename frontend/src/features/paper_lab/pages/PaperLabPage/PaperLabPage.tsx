import { useParams } from "react-router";
import { t } from "@/shared/i18n/t";
import { PaperLabDetail } from "./PaperLabDetail";
import { PaperLabIndex } from "./PaperLabIndex";

export function PaperLabPage() {
  const { labId } = useParams();
  return (
    <div className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("paperLab.title")}</h1>
      {labId ? <PaperLabDetail key={labId} labId={labId} /> : <PaperLabIndex />}
    </div>
  );
}
