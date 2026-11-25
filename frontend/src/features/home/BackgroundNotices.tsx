import { NoticeToasts } from "./components/NoticeToasts";
import { useBackgroundNotices, type NoticeOptions } from "./hooks/useBackgroundNotices";

/**
 * The home `overlay` slot (all pages): re-reads the activity feed in a background task and
 * shows new items in an `aria-live="polite"` region. Delays are set only
 * in tests; a notification hovered or focused stays.
 */
export function BackgroundNotices(options: NoticeOptions) {
  const { notices, dismiss, hold } = useBackgroundNotices(options);
  return <NoticeToasts notices={notices} onDismiss={dismiss} onHold={hold} />;
}
