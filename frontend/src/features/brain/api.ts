import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Folder = components["schemas"]["FolderOut"];
export type FolderIn = components["schemas"]["FolderIn"];
export type FolderPatch = components["schemas"]["FolderPatch"];
export type FolderStatus = components["schemas"]["FolderStatus"];
export type RelayStatus = components["schemas"]["BrainRelayStatus"];

const ref = (id: string) => ({ path: { folder_id: id } });

export async function fetchFolders(signal?: AbortSignal) {
  return unwrap(await api.GET("/brain/folders", { signal }));
}

export async function fetchFolderStatus(signal?: AbortSignal) {
  return unwrap(await api.GET("/brain/status", { signal }));
}

export async function fetchRelayStatus(signal?: AbortSignal) {
  return unwrap(await api.GET("/brain/relay", { signal }));
}

export async function addFolder(body: FolderIn) {
  return unwrap(await api.POST("/brain/folders", { body }));
}

export async function changeFolder(id: string, body: FolderPatch) {
  return unwrap(await api.PATCH("/brain/folders/{folder_id}", { params: ref(id), body }));
}

export async function deleteFolder(id: string) {
  unwrap(await api.DELETE("/brain/folders/{folder_id}", { params: ref(id) }));
}

export async function issueSyncToken() {
  return unwrap(await api.POST("/brain/sync-token"));
}
