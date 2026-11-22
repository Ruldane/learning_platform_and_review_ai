export async function showMobileAlert(kind: "offers" | "agenda", id: string, title: string, body: string) {
  const key = "tremplin:mobile:notification:" + kind;
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  if (!navigator.serviceWorker || localStorage.getItem(key) === id) return;
  const worker = await navigator.serviceWorker.getRegistration();
  if (worker?.active) {
    await worker.showNotification(title, { body, tag: "tremplin-" + kind, icon: "/mobile-icon-192.png" });
    localStorage.setItem(key, id);
  }
}
