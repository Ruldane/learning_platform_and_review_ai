import { ApiError } from "@/shared/api/errors";
import { sendReview, verifyMobileAccount } from "./data";
import { applyReview, cachedMobile, mobileGeneration, pendingReviews } from "./storage";

const SETTLED = ["card_not_due", "card_not_found", "card_receipt_changed"];

export async function synchronizeReviews(
  owner: string,
): Promise<{ sent: number; skipped: number }> {
  let sent = 0;
  let skipped = 0;
  const generation = mobileGeneration();
  const current = () => mobileGeneration() === generation && cachedMobile()?.owner === owner;
  const pending = pendingReviews(owner);
  if (!pending.length || !current()) return { sent, skipped };
  try {
    if ((await verifyMobileAccount()) !== owner) return { sent, skipped };
  } catch (error) {
    if (current()) throw error;
    return { sent, skipped };
  }
  for (const review of pending) {
    if (!current()) break;
    try {
      await sendReview(review);
      if (!current()) break;
      sent++;
    } catch (error) {
      if (!current()) break;
      if (!(error instanceof ApiError) || !SETTLED.includes(error.code)) throw error;
      skipped++;
    }
    applyReview(review, generation);
  }
  return { sent, skipped };
}
