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

/* Poll a small private snapshot so badges and notification previews stay current. */
document.addEventListener("DOMContentLoaded", () => {
  const statusUrl = document.body.dataset.liveStatusUrl;
  if (!statusUrl) return;

  const notificationTrigger = document.querySelector(".notification-menu-trigger");
  const notificationList = document.querySelector(".notification-preview-list");
  const notificationHeading = document.querySelector("[data-notification-heading]");
  const notificationCount = document.querySelector("[data-notification-count]");
  const updateBanner = document.querySelector("[data-live-update-banner]");
  const updateAction = document.querySelector("[data-live-update-action]");
  let knownAlertCount = Number.parseInt(document.body.dataset.liveAlertCount || "", 10);
  let knownLatestAlertId = document.body.dataset.liveAlertLatestId || "";

  const setNotificationBadge = (count) => {
    if (!notificationTrigger) return;
    let badge = notificationTrigger.querySelector(".notification-badge");
    if (count > 0 && !badge) {
      badge = document.createElement("span");
      badge.className = "notification-badge";
      notificationTrigger.append(badge);
    }
    if (badge) {
      badge.textContent = count;
      badge.hidden = count === 0;
    }
    notificationTrigger.setAttribute("aria-label", count ? `Open notifications (${count} unread)` : "Open notifications");
  };

  const refreshNotificationPreview = (items) => {
    if (!notificationList) return;
    notificationList.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "notification-empty";
      empty.textContent = "No notifications yet. New eligible alerts and report updates will appear here.";
      notificationList.append(empty);
      return;
    }
    items.forEach((item) => {
      const link = document.createElement("a");
      link.className = `notification-preview ${item.is_read ? "is-read" : "is-unread"}`;
      link.href = item.open_url;
      if (item.photo_url) {
        const image = document.createElement("img");
        image.className = "notification-preview-image";
        image.src = item.photo_url;
        image.alt = "";
        image.loading = "lazy";
        link.append(image);
      } else {
        const dot = document.createElement("span");
        dot.className = `notification-type-dot ${item.type_value}`;
        link.append(dot);
      }
      const copy = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = item.title;
      const details = document.createElement("small");
      details.textContent = `${item.body} · ${item.location} · ${item.created_label}`;
      copy.append(title, details);
      link.append(copy);
      notificationList.append(link);
    });
  };

  const updateStaffCounters = (workload) => {
    Object.entries(workload).forEach(([name, count]) => {
      document.querySelectorAll(`[data-staff-counter="${name}"]`).forEach((counter) => {
        counter.textContent = count;
        counter.hidden = count === 0;
        counter.setAttribute("aria-label", `${count} pending ${name.replace("_", " ")}`);
      });
    });
  };

  const applyStatus = (status) => {
    setNotificationBadge(status.notification_count);
    if (notificationHeading) notificationHeading.textContent = `${status.notification_count} unread notification${status.notification_count === 1 ? "" : "s"}`;
    if (notificationCount) notificationCount.textContent = status.notification_count;
    refreshNotificationPreview(status.notification_items || []);
    updateStaffCounters(status.staff_workload || {});

    const receivedNewAlert = Number.isFinite(knownAlertCount)
      && (status.alert_count > knownAlertCount || (knownLatestAlertId && status.latest_alert_id && status.latest_alert_id !== knownLatestAlertId));
    if (receivedNewAlert && updateBanner) updateBanner.hidden = false;
    knownAlertCount = status.alert_count;
    knownLatestAlertId = status.latest_alert_id || knownLatestAlertId;
  };

  const poll = async () => {
    try {
      const response = await fetch(statusUrl, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) return;
      applyStatus(await response.json());
    } catch (_) {
      // A temporary network failure must not interrupt the rest of the interface.
    }
  };

  if (updateAction) updateAction.addEventListener("click", () => window.location.reload());
  window.setTimeout(poll, 1000);
  window.setInterval(poll, 30000);
});
