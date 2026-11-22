import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { InlineError } from "@/shared/ui/states/InlineError";
import { answerTransfer, prepareTransfer, type Transfer } from "../../api";
import { TransferCard } from "../../components/TransferCard";
import { TRANSFERS } from "../../queryKeys";
import { transferView } from "../../toView";

export function TransferRow({ row }: { row: Transfer }) {
  const heading = useRef<HTMLHeadingElement>(null);
  const queries = useQueryClient();
  const request = useMutation({
    mutationFn: (answer: string | null) =>
      answer === null ? prepareTransfer(row.id) : answerTransfer(row.id, answer),
    onSuccess: async () => {
      heading.current?.focus();
      await queries.invalidateQueries({ queryKey: TRANSFERS });
    },
  });
  return (
    <li className="grid gap-2">
      <TransferCard
        view={transferView(row)}
        busy={request.isPending}
        headingRef={heading}
        onPrepare={() => request.mutate(null)}
        onAnswer={(answer) => request.mutate(answer)}
      />
      {request.error ? <InlineError message={errorMessage(request.error)} /> : null}
    </li>
  );
}
