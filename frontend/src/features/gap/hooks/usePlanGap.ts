import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { t } from "@/shared/i18n/t";
import type { RunSource } from "@/shared/lib/runSource";
import { planGap, programOfSession } from "../api";
import { gapKeys } from "../queryKeys";

/** Ce que l'ajout au planning a donné : une replanification lancée ou déjà ouverte. */
export interface PlanOutcome {
  kind: "started" | "open";
  /** Le programme concerné (pour le lien vers la replanification) ; `null` si introuvable. */
  programId: string | null;
}

export interface PlanFailure {
  code: string;
  message: string;
}

function openSessionOf(details: unknown): string | null {
  if (typeof details !== "object" || details === null) return null;
  const id = (details as Record<string, unknown>).session_id;
  return typeof id === "string" && id !== "" ? id : null;
}

async function outcomeOf(kind: PlanOutcome["kind"], sessionId: string): Promise<PlanOutcome> {
  const programId = await programOfSession(sessionId).catch(() => null);
  return { kind, programId };
}

function failureOf(error: unknown): PlanFailure {
  if (!(error instanceof ApiError)) return { code: "unknown", message: errorMessage(error) };
  if (error.code === "no_program") return { code: error.code, message: t("gap.errors.no_program") };
  if (error.status === 422 && error.code === "gap_skill_unknown") {
    return { code: error.code, message: t("gap.errors.skills_stale") };
  }
  return { code: error.code, message: error.message };
}

/**
 * « Ajouter au planning » : lance la replanification pour les compétences cochées. Une
 * replanification déjà ouverte (409 `replan_open`) est rendue comme telle, avec son lien. Une
 * compétence qui n'est plus à ajouter (422) fait relire le tableau.
 */
export function usePlanGap(postingId: string, onPlanned: () => void, provider?: RunSource) {
  const client = useQueryClient();
  const [outcome, setOutcome] = useState<PlanOutcome | null>(null);
  const [failure, setFailure] = useState<PlanFailure | null>(null);
  const mutation = useMutation({
    mutationFn: async (body: components["schemas"]["PlanGapIn"]): Promise<PlanOutcome> => {
      try {
        return await outcomeOf("started", (await planGap(postingId, body, provider)).session_id);
      } catch (error) {
        const open =
          error instanceof ApiError && error.code === "replan_open"
            ? openSessionOf(error.details)
            : null;
        if (open) return outcomeOf("open", open);
        throw error;
      }
    },
    onSuccess: (result) => {
      setOutcome(result);
      onPlanned();
      void client.invalidateQueries({ queryKey: gapKeys.gap(postingId) });
    },
    onError: (error) => {
      setFailure(failureOf(error));
      if (error instanceof ApiError && error.status === 422) {
        void client.invalidateQueries({ queryKey: gapKeys.gap(postingId) });
      }
    },
  });
  const { mutate } = mutation;
  return {
    plan: (skills: string[], programId?: string) => {
      setOutcome(null);
      setFailure(null);
      mutate(programId ? { skills, program_id: programId } : { skills });
    },
    pending: mutation.isPending,
    outcome,
    failure,
  };
}
