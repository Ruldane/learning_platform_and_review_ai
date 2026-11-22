import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { listEditions, listPrograms, listPublishedLessons, prepareEdition, readEdition } from "../../api";
import { formats, type Format } from "../../components/VariantReading";

export function useLessonVariants() {
  const [programId, setProgramId] = useState("");
  const [lessonId, setLessonId] = useState("");
  const [search, navigate] = useSearchParams();
  const editionId = search.get("edition") ?? "";
  const format = formats.find((value) => value === search.get("format")) ?? "review";
  const queryClient = useQueryClient();
  const programs = useQuery({
    queryKey: ["lessonVariants", "programs"], queryFn: ({ signal }) => listPrograms(signal),
  });
  const lessons = useQuery({
    queryKey: ["lessonVariants", "lessons", programId], enabled: !!programId,
    queryFn: ({ signal }) => listPublishedLessons(programId, signal),
  });
  const history = useQuery({
    queryKey: ["lessonVariants", "history"], queryFn: ({ signal }) => listEditions(signal),
  });
  const edition = useQuery({
    queryKey: ["lessonVariants", "edition", editionId], enabled: !!editionId,
    queryFn: ({ signal }) => readEdition(editionId, signal),
  });
  const prepare = useMutation({
    mutationFn: prepareEdition,
    onSuccess: (created) => {
      queryClient.setQueryData(["lessonVariants", "edition", created.id], created);
      void queryClient.invalidateQueries({ queryKey: ["lessonVariants", "history"] });
      navigate({ edition: created.id });
      requestAnimationFrame(() => document.getElementById("variant-reading")?.focus());
    },
  });
  return {
    programs, lessons, history, edition, prepare, programId, lessonId, editionId, format,
    setLessonId,
    setProgramId: (id: string) => { setProgramId(id); setLessonId(""); },
    setFormat: (next: Format) => navigate({ edition: editionId, format: next }, { replace: true }),
  };
}
