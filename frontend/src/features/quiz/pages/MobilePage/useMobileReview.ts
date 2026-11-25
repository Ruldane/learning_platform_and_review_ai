import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { useOnline } from "../../mobile/connectivity";
import {
  loadMobile, sendReview, verifyMobileAccount, type Answer, type MobileCard, type MobileSnapshot,
} from "../../mobile/data";
import {
  cachedMobile, clearMobile, mobileGeneration, mobileRevision, pendingReviews, queueReview, saveMobile,
  subscribeMobile,
} from "../../mobile/storage";
import { synchronizeReviews } from "../../mobile/sync";

const ACCESS = ["mobile", "account"];
const DATA = ["mobile", "snapshot"];

function netDown(error: unknown) {
  return error instanceof ApiError && error.status === 0;
}

export function useMobileAccess() {
  const network = useOnline();
  useSyncExternalStore(subscribeMobile, mobileRevision);
  const generation = mobileGeneration();
  const cached = cachedMobile();
  const account = useQuery({
    queryKey: [...ACCESS, generation],
    queryFn: ({ signal }) => verifyMobileAccount(signal),
    enabled: network,
    retry: false,
    staleTime: 0,
  });
  const owner = !account.isError && network ? account.data : undefined;
  const data = useQuery({
    queryKey: [...DATA, owner, generation],
    queryFn: ({ signal }) => loadMobile(owner ?? "", signal),
    enabled: Boolean(owner),
    retry: false,
  });
  const offline = !network || netDown(account.error) || netDown(data.error);
  const pinned = Boolean(cached && (offline || cached.owner === owner));
  useEffect(() => {
    if (!network || !cached) return;
    if ((owner && owner !== cached.owner) || (account.error instanceof ApiError && account.error.status === 401)) {
      clearMobile();
    }
  }, [account.error, cached, network, owner]);
  useEffect(() => {
    if (offline || !pinned || !data.data || data.data.owner !== owner) return;
    try {
      saveMobile(data.data, generation);
    } catch {
      // A copy already saved can still serve for the next cut-off.
    }
  }, [data.data, generation, offline, owner, pinned]);
  return {
    snapshot: offline ? (pinned ? cached : null) : owner ? data.data ?? null : null,
    owner: offline ? cached?.owner : owner,
    pinned,
    offline,
    loading: !offline && (account.isPending || (owner && data.isPending)),
    error: !offline ? account.error ?? data.error : null,
  };
}

export function useMobileReview(owner: string | undefined, pinned: boolean, offline: boolean) {
  const cache = useQueryClient();
  const generation = mobileGeneration();
  const syncing = useRef(false);
  const refresh = useCallback(async () => {
    await cache.invalidateQueries({ queryKey: DATA });
  }, [cache]);
  const sync = useMutation({
    mutationFn: async (id: string) => {
      if (syncing.current) return null;
      syncing.current = true;
      try {
        return await synchronizeReviews(id);
      } finally {
        syncing.current = false;
      }
    },
    onSuccess: refresh,
  });
  const { mutate: synchronize } = sync;
  useEffect(() => {
    if (!offline && owner && pinned && pendingReviews(owner).length) synchronize(owner);
  }, [offline, owner, pinned, synchronize]);
  const answer = useMutation({
    networkMode: "always",
    mutationFn: async ({ card, result }: { card: MobileCard; result: Answer }) => {
      if (!owner || generation !== mobileGeneration()) return;
      if (pinned) {
        if (queueReview(owner, card, result, generation) && !offline) synchronize(owner);
      } else if (!offline) {
        await sendReview({ owner, id: crypto.randomUUID(), card: card.id, due: card.due, result });
      }
    },
    onSuccess: () => { if (!offline) void refresh(); },
  });
  return { answer, sync, synchronize };
}

export async function pinSnapshot(snapshot: MobileSnapshot) {
  const generation = mobileGeneration();
  if (await verifyMobileAccount() === snapshot.owner) saveMobile(snapshot, generation);
}
