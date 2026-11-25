import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import {
  HISTORY, OPTIONS, PREFERENCES, listOffers, loadRules, previewComparison, saveComparison, storeRules,
  type Pair, type Rules,
} from "../../api";

export function useComparison() {
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [draft, setDraft] = useState<Rules | null>(null);
  const options = useQuery({ queryKey: OPTIONS, queryFn: ({ signal }) => listOffers(signal) });
  const criteria = useQuery({ queryKey: PREFERENCES, queryFn: ({ signal }) => loadRules(signal) });
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const preview = useMutation({ mutationFn: previewComparison });
  const rulesSave = useMutation({
    mutationFn: storeRules,
    onSuccess: (rules) => queryClient.setQueryData(PREFERENCES, rules),
  });
  const save = useMutation({
    mutationFn: saveComparison,
    onSuccess: ({ id }) => {
      void queryClient.invalidateQueries({ queryKey: HISTORY });
      void navigate(`/career/offer-comparison/${id}`);
    },
  });
  const change = (set: () => void) => {
    set();
    preview.reset();
    save.reset();
    rulesSave.reset();
  };
  const editable = draft ?? criteria.data;
  const rules = editable && { ...editable, preferred_location: editable.preferred_location?.trim() || null };
  const validWeights = Boolean(
    (rules?.weights?.match ?? 50) || (rules?.weights?.work_mode ?? 50) || (rules?.weights?.location ?? 50),
  );
  const pair: Pair | null = rules && validWeights && first && second && first !== second
    ? { first_id: first, second_id: second, preferences: rules }
    : null;
  return {
    options, criteria, first, second, rules, editable, pair, preview, save, rulesSave, validWeights,
    busy: preview.isPending || save.isPending || rulesSave.isPending,
    setFirst: (id: string) => change(() => setFirst(id)),
    setSecond: (id: string) => change(() => setSecond(id)),
    setRules: (value: Rules) => change(() => setDraft(value)),
  };
}
