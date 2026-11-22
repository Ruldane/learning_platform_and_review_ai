import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface Props {
  sessionId: string;
  path: string;
  save: () => Promise<boolean>;
}

export function FeynmanFileLink({ sessionId, path, save }: Props) {
  const navigate = useNavigate();
  const open = async () => {
    if (await save()) {
      await navigate(`/code/${encodeURIComponent(sessionId)}/explique-moi`, { state: { path } });
    }
  };
  return (
    <Button type="button" variant="link" className="self-start p-0" onClick={() => void open()}>
      {t("feynman.title")}
    </Button>
  );
}
