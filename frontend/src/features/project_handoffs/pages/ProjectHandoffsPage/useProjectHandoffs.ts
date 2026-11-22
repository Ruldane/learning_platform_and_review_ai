import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { approveGuide, downloadGuide, listGuides, listProjects, previewGuide, readGuide, readSource,
  type Draft } from "../../api";

const EMPTY: Draft = { project_id: "", commands: "", limitations: "", steps: "" };
const HISTORY = ["projectHandoffs", "history"] as const;

function focusPreview() {
  requestAnimationFrame(() => document.getElementById("handoff-preview")?.focus());
}

export function useProjectHandoffs() {
  const [draft, setDraft] = useState(EMPTY);
  const [search, navigate] = useSearchParams();
  const guideId = search.get("guide") ?? "";
  const queryClient = useQueryClient();
  const projects = useQuery({
    queryKey: ["projectHandoffs", "projects"], queryFn: ({ signal }) => listProjects(signal),
  });
  const source = useQuery({
    queryKey: ["projectHandoffs", "source", draft.project_id], enabled: !!draft.project_id,
    queryFn: ({ signal }) => readSource(draft.project_id, signal), retry: false,
  });
  const history = useQuery({ queryKey: HISTORY, queryFn: ({ signal }) => listGuides(signal) });
  const saved = useQuery({
    queryKey: ["projectHandoffs", "guide", guideId], enabled: !!guideId,
    queryFn: ({ signal }) => readGuide(guideId, signal),
  });
  const preview = useMutation({
    mutationFn: async (input: Draft) => ({ input, guide: await previewGuide(input) }),
    onSuccess: () => { navigate({}); focusPreview(); },
  });
  const approve = useMutation({
    mutationFn: approveGuide,
    onSuccess: (guide) => {
      queryClient.setQueryData(["projectHandoffs", "guide", guide.id], guide);
      void queryClient.invalidateQueries({ queryKey: HISTORY });
      navigate({ guide: guide.id });
      focusPreview();
    },
  });
  const download = useMutation({ mutationFn: downloadGuide });
  const proposed = !guideId && preview.data?.input === draft ? preview.data.guide : undefined;
  const chooseProject = (id: string) => { setDraft({ ...EMPTY, project_id: id }); navigate({}); };
  return { projects, source, history, saved, preview, approve, download, guideId, draft, setDraft,
    proposed, chooseProject };
}
