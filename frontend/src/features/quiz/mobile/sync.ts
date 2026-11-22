import { ApiError } from "@/shared/api/errors";
import { sendReview, verifyMobileAccount } from "./data";
import { applyReview, cachedMobile, pendingReviews } from "./storage";

const SETTLED = ["card_not_due", "card_not_found", "card_receipt_changed"];

export async function synchronizeReviews(owner: string): Promise<{ sent: number; skipped: number }> {
  let sent = 0;
  let skipped = 0;
  const pending = pendingReviews(owner);
  if (!pending.length || cachedMobile()?.owner !== owner || await verifyMobileAccount() !== owner) {
    return { sent, skipped };
  }
  for (const review of pending) {
    if (cachedMobile()?.owner !== owner) break;
    try {
      await sendReview(review);
      sent++;
    } catch (error) {
      if (!(error instanceof ApiError) || !SETTLED.includes(error.code)) throw error;
      skipped++;
    }
    applyReview(review);
  }
  return { sent, skipped };
}
