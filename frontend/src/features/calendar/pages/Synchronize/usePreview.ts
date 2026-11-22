import { useMutation } from "@tanstack/react-query";
import { useLayoutEffect, useRef, useState } from "react";
import { confirm, propose, type Proposal, type Selection } from "../../api";

export function usePreview() {
  const [preview, setPreview] = useState<Proposal | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const draft = useMutation({
    mutationFn: propose,
    onSuccess: setPreview,
  });
  const previewId = preview?.id;
  useLayoutEffect(() => {
    if (previewId) heading.current?.focus();
  }, [previewId]);
  const sync = useMutation({ mutationFn: confirm, onSuccess: setPreview });
  const reset = () => {
    setPreview(null);
    draft.reset();
    sync.reset();
  };
  return {
    preview,
    heading,
    pending: draft.isPending || sync.isPending,
    error: draft.error ?? sync.error,
    reset,
    propose: (selection: Selection) => {
      reset();
      draft.mutate(selection);
    },
    confirm: (id: string) => sync.mutate(id),
  };
}
