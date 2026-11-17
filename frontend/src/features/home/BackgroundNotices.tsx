import { NoticeToasts } from "./components/NoticeToasts";
import { useBackgroundNotices, type NoticeOptions } from "./hooks/useBackgroundNotices";

/**
 * L'emplacement `overlay` de l'accueil (toutes les pages) : relit le fil d'activité en tâche de fond
 * et montre les nouveautés dans une région `aria-live="polite"`. Les délais ne se règlent qu'en test ; une notification survolée ou au focus reste.
 */
export function BackgroundNotices(options: NoticeOptions) {
  const { notices, dismiss, hold } = useBackgroundNotices(options);
  return <NoticeToasts notices={notices} onDismiss={dismiss} onHold={hold} />;
}
