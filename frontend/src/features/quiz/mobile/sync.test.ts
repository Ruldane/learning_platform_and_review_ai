import { afterEach, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/api/errors";
import * as data from "./data";
import { clearMobile, queueReview, saveMobile } from "./storage";
import { synchronizeReviews } from "./sync";

const owner = "account-a";
const date = "2026-11-22";
const card = { id: "card-id", front: "Question", back: "Réponse", due: date };
const snapshot = { owner, day: date, lesson: null, minutes: null, offers: [], cards: [card] };

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

afterEach(() => {
  vi.restoreAllMocks();
  clearMobile();
});

it("discards a queued review if the same account is prepared again while checking identity", async () => {
  const account = deferred<string>();
  vi.spyOn(data, "verifyMobileAccount").mockReturnValueOnce(account.promise);
  const send = vi
    .spyOn(data, "sendReview")
    .mockRejectedValue(
      new ApiError({ status: 409, code: "card_not_due", message: "Déjà traitée." }),
    );
  saveMobile(snapshot);
  queueReview(owner, card, "ok");
  const running = synchronizeReviews(owner);
  clearMobile();
  saveMobile(snapshot);
  account.resolve(owner);
  await running;
  expect(send).not.toHaveBeenCalled();
});

it("does not send the rest of a discarded batch after a review already sent settles", async () => {
  vi.spyOn(data, "verifyMobileAccount").mockResolvedValue(owner);
  const inFlight = deferred<never>();
  const closed = new ApiError({ status: 409, code: "card_not_due", message: "Déjà traitée." });
  const send = vi
    .spyOn(data, "sendReview")
    .mockReturnValueOnce(inFlight.promise)
    .mockRejectedValue(closed);
  saveMobile(snapshot);
  queueReview(owner, card, "ok");
  queueReview(owner, { ...card, id: "another-card" }, "fail");
  const running = synchronizeReviews(owner);
  await vi.waitFor(() => expect(send).toHaveBeenCalledOnce());
  clearMobile();
  saveMobile(snapshot);
  inFlight.reject(closed);
  await running;
  expect(send).toHaveBeenCalledOnce();
});
