import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Draft = components["schemas"]["ProjectHandoffDraft"];
export type Approval = components["schemas"]["ProjectHandoffApproval"];
export type HandoffSummary = components["schemas"]["ProjectHandoffSummary"];

export async function listProjects(signal: AbortSignal) {
  return unwrap(await api.GET("/projects", { signal }));
}

export async function readSource(projectId: string, signal: AbortSignal) {
  return unwrap(await api.GET("/project-handoffs/source/{project_id}", {
    params: { path: { project_id: projectId } }, signal,
  }));
}

export async function previewGuide(body: Draft) {
  return unwrap(await api.POST("/project-handoffs/preview", { body }));
}

export async function approveGuide(body: Approval) {
  return unwrap(await api.POST("/project-handoffs", { body }));
}

export async function listGuides(signal: AbortSignal) {
  return unwrap(await api.GET("/project-handoffs", { signal }));
}

export async function readGuide(handoffId: string, signal: AbortSignal) {
  return unwrap(await api.GET("/project-handoffs/{handoff_id}", {
    params: { path: { handoff_id: handoffId } }, signal,
  }));
}

export async function downloadGuide(handoffId: string) {
  const payload = unwrap(await api.GET("/project-handoffs/{handoff_id}/export", {
    params: { path: { handoff_id: handoffId } },
    parseAs: "blob",
  }));
  const url = URL.createObjectURL(payload);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "guide-de-reprise.md";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
