import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { withdraw, type Publication } from "../../api";
import { PortfolioConfirmation } from "./PortfolioConfirmation";

interface Props {
  value: Publication;
  reload: () => void;
  restoreFocus: () => void;
}

export function PortfolioWithdraw({ value, reload, restoreFocus }: Props) {
  const trigger = useRef<HTMLButtonElement>(null);
  const [removing, setRemoving] = useState(false);
  const remove = useMutation({
    mutationFn: () => withdraw(value),
    onSuccess: () => {
      restoreFocus();
      reload();
    },
  });
  const stop = () => {
    setRemoving(false);
    requestAnimationFrame(() => trigger.current?.focus());
  };
  return removing ? (
    <PortfolioConfirmation
      url={value.url}
      pending={remove.isPending}
      error={remove.error}
      onConfirm={() => remove.mutate()}
      onCancel={stop}
    />
  ) : (
    <Button
      ref={trigger}
      type="button"
      variant="outline"
      className="self-start"
      onClick={() => setRemoving(true)}
    >
      {t("portfolio.withdraw")}
    </Button>
  );
}
