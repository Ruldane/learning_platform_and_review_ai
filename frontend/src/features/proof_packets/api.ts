import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Source = components["schemas"]["ProofPacketSource"];
export type Selection = components["schemas"]["ProofPacketSelection"];
export type Manifest = components["schemas"]["ProofPacketManifest"];
export type StoredPacket = components["schemas"]["ProofPacketOut"];
export type PacketSummary = components["schemas"]["ProofPacketSummary"];
export type PacketCreate = components["schemas"]["ProofPacketCreate"];

export async function listSources(signal: AbortSignal) {
  return unwrap(await api.GET("/proof-packets/sources", { signal }));
}

export async function previewPacket(selection: Selection) {
  return unwrap(await api.POST("/proof-packets/preview", { body: selection }));
}

export async function savePacket(input: PacketCreate) {
  return unwrap(await api.POST("/proof-packets", { body: input }));
}

export async function listPackets(signal: AbortSignal) {
  return unwrap(await api.GET("/proof-packets", { signal }));
}

export async function readPacket(id: string) {
  return unwrap(await api.GET("/proof-packets/{packet_id}", {
    params: { path: { packet_id: id } },
  }));
}

export async function downloadPacket(id: string) {
  const payload = unwrap(await api.GET("/proof-packets/{packet_id}/export", {
    params: { path: { packet_id: id } },
    parseAs: "blob",
  }));
  const url = URL.createObjectURL(payload);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "dossier-de-preuves.json";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
