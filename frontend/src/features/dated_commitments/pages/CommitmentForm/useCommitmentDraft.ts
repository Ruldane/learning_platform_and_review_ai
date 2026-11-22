import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { createCommitment, detailKey, listKey, type Draft } from "../../api";
import { commitmentPath, normalizeMeasure } from "../../format";

const initial: Draft = {
  title: "",
  version: "",
  intention: "",
  indicator: "",
  unit: "",
  target: "",
  due_on: "",
};

export function useCommitmentDraft() {
  const [draft, setDraft] = useState(initial);
  const [requestId] = useState(() => crypto.randomUUID());
  const cache = useQueryClient();
  const navigate = useNavigate();
  const create = useMutation({
    mutationFn: () =>
      createCommitment({ ...draft, target: normalizeMeasure(String(draft.target)) }, requestId),
    onSuccess: (item) => {
      cache.setQueryData(detailKey(item.id), item);
      void cache.invalidateQueries({ queryKey: listKey, exact: true });
      void navigate(commitmentPath(item.id));
    },
  });
  const change = (field: keyof Draft, value: string) =>
    setDraft((current) => ({ ...current, [field]: value }));
  return { draft, change, create };
}
