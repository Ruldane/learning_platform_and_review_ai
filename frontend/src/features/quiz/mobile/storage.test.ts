import { expect, it, vi } from "vitest";
import { resetLocalState } from "@/shared/lib/localReset";
import { pinSnapshot } from "../pages/MobilePage/useMobileReview";
import * as data from "./data";
import { cachedMobile, mobileGeneration, pendingReviews, queueReview, saveMobile } from "./storage";

const snapshot = {
  owner: "account-a", day: "2026-11-22", lesson: "Leçon privée", minutes: 15, offers: [], cards: [],
};

it("ignores a device preparation whose account check completes after logout", async () => {
  let confirm!: (owner: string) => void;
  const verification = new Promise<string>((resolve) => { confirm = resolve; });
  const account = vi.spyOn(data, "verifyMobileAccount").mockReturnValueOnce(verification);
  const pending = pinSnapshot(snapshot);
  expect(account).toHaveBeenCalledOnce();
  resetLocalState();
  confirm("account-a");
  await pending;
  expect(cachedMobile()).toBeNull();
});

it("discards a write crossing a reset in another tab", () => {
  const previous = mobileGeneration();
  const setItem = Storage.prototype.setItem;
  const crossing = vi.spyOn(Storage.prototype, "setItem").mockImplementationOnce(
    function (this: Storage, key, value) {
      setItem.call(this, key, value);
      setItem.call(this, "tremplin:mobile-generation", "other-tab");
    },
  );
  expect(saveMobile(snapshot, previous)).toBe(false);
  crossing.mockRestore();
  expect(mobileGeneration()).toBe("other-tab");
  expect(cachedMobile()).toBeNull();
  expect(Object.values(localStorage).some((value) => value.includes(snapshot.lesson))).toBe(false);
  expect(saveMobile(snapshot, previous)).toBe(false);
  resetLocalState();
});

it("keeps one receipt per card and removes private data when the account is forgotten", () => {
  const card = { id: "card-id", front: "Question", back: "Réponse", due: "2026-11-22" };
  saveMobile({ owner: "account-a", day: card.due, lesson: null, minutes: null, offers: [], cards: [card] });
  const first = queueReview("account-a", card, "ok");
  expect(queueReview("account-a", card, "fail")).toEqual(first);
  expect(pendingReviews("account-b")).toEqual([]);

  resetLocalState();
  expect(cachedMobile()).toBeNull();
  expect(pendingReviews("account-a")).toEqual([]);
});
