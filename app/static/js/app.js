/* Shared notification and account-popover behaviour. */
document.addEventListener("DOMContentLoaded", () => {
  const triggers = document.querySelectorAll("[data-popover-trigger]");
  const menus = document.querySelectorAll("[data-popover]");

  if (!triggers.length || !menus.length) return;

  const closeAll = () => {
    menus.forEach((menu) => {
      menu.hidden = true;
    });
    triggers.forEach((trigger) => {
      trigger.setAttribute("aria-expanded", "false");
    });
  };

  const markNotificationsSeen = async () => {
    try {
      const response = await fetch("/notifications/mark-seen", {
        method: "POST",
        credentials: "same-origin",
      });
      if (!response.ok) return;
      document.querySelectorAll(".notification-badge").forEach((badge) => badge.remove());
      document.querySelectorAll("[data-unread-count]").forEach((element) => {
        element.textContent = "0";
      });
    } catch {
      // Keep the badge unchanged if the local development request cannot complete.
    }
  };

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const menu = document.getElementById(trigger.dataset.popoverTrigger);
      if (!menu) return;
      const isOpen = !menu.hidden;
      closeAll();
      if (!isOpen) {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        if (trigger.dataset.markNotifications === "true") {
          markNotificationsSeen();
        }
      }
    });
  });

  document.addEventListener("click", (event) => {
    const clickedPopover = event.target.closest("[data-popover]");
    const clickedTrigger = event.target.closest("[data-popover-trigger]");
    if (!clickedPopover && !clickedTrigger) closeAll();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAll();
  });
});
