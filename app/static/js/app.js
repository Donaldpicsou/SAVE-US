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

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const menu = document.getElementById(trigger.dataset.popoverTrigger);
      if (!menu) return;
      const isOpen = !menu.hidden;
      closeAll();
      if (!isOpen) {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
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
