import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { compare, listScenarios, readScenario, save } from "../../api";
import type { AssumptionFields, ComparisonView } from "../../components/viewTypes";
import { assumptionsIn, assumptionsOut, comparisonOut, historyOut } from "../../toView";

const HISTORY = ["decision_lab", "scenarios"] as const;
const INITIAL: AssumptionFields = {
  rate: 100,
  duration: 60,
  outage: 10,
  first: { replicas: 1, capacityPerReplica: 100, hourlyCents: 10 },
  second: { replicas: 2, capacityPerReplica: 60, hourlyCents: 8 },
};

interface Preview {
  assumptions: AssumptionFields;
  results: ComparisonView;
}

export function useDecisionLab() {
  const [assumptions, setAssumptions] = useState(INITIAL);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [title, setTitle] = useState("");
  const [critique, setCritique] = useState("");
  const queryClient = useQueryClient();
  const history = useQuery({
    queryKey: HISTORY, queryFn: ({ signal }) => listScenarios(signal), select: historyOut,
  });
  const comparison = useMutation({
    mutationFn: (fields: AssumptionFields) => compare(assumptionsIn(fields)),
    onSuccess: (results, compared) => setPreview({ assumptions: compared, results: comparisonOut(results) }),
  });
  const saved = useMutation({
    mutationFn: save,
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: HISTORY }); },
  });
  const opened = useMutation({
    mutationFn: readScenario,
    onSuccess: (item) => {
      saved.reset();
      const fields = assumptionsOut(item.assumptions);
      setAssumptions(fields);
      setPreview({ assumptions: fields, results: comparisonOut(item.results) });
      setTitle(item.title);
      setCritique(item.critique);
    },
  });
  const result = preview?.assumptions === assumptions ? preview.results : null;
  return { assumptions, setAssumptions, result, title, setTitle, critique, setCritique, history,
    comparison, saved, opened };
}
