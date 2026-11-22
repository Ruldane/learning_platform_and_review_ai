import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Packet = components["schemas"]["ProofPacketOut"];
export type PacketSummary = components["schemas"]["ProofPacketSummary"];
export type Manifest = components["schemas"]["ProofPacketManifest"];
export type Share = components["schemas"]["MentorShareOut"];
export type ShareDetail = components["schemas"]["MentorShareDetail"];
export type ShareCreate = components["schemas"]["MentorShareCreate"];
export type GuestReply = components["schemas"]["MentorCommentCreate"];

export async function listPackets(signal: AbortSignal) {
  return unwrap(await api.GET("/proof-packets", { signal }));
}

export async function readPacket(id: string) {
  return unwrap(await api.GET("/proof-packets/{packet_id}", { params: { path: { packet_id: id } } }));
}

export async function listShares(signal: AbortSignal) {
  return unwrap(await api.GET("/mentor-reviews/shares", { signal }));
}

export async function newShare(body: ShareCreate) {
  return unwrap(await api.POST("/mentor-reviews/shares", { body }));
}

export async function readShare(id: string) {
  return unwrap(await api.GET("/mentor-reviews/shares/{share_id}", {
    params: { path: { share_id: id } },
  }));
}

export async function revokeShare(id: string) {
  unwrap(await api.DELETE("/mentor-reviews/shares/{share_id}", {
    params: { path: { share_id: id } },
  }));
  return readShare(id);
}

function guest(token: string) {
  return {
    credentials: "omit", cache: "no-store", referrerPolicy: "no-referrer",
    headers: { Authorization: `Bearer ${token}` },
  } as const;
}

export async function sharedWork(token: string, signal: AbortSignal) {
  return unwrap(await api.GET("/mentor-reviews/shared", { ...guest(token), signal }));
}

export async function sendComment(token: string, body: GuestReply) {
  return unwrap(await api.POST("/mentor-reviews/shared/comments", { ...guest(token), body }));
}
