/* T53 safe alert sharing: public URLs are requested lazily and never expose media. */
document.addEventListener("DOMContentLoaded", () => {
  const controls = document.querySelectorAll("[data-alert-share]");

  const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const input = document.createElement("textarea");
    input.value = text;
    input.setAttribute("readonly", "");
    input.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    document.body.appendChild(input);
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    if (!copied) throw new Error("Copy is unavailable.");
  };

  controls.forEach((container) => {
    const endpoint = container.dataset.shareEndpoint;
    const status = container.querySelector("[data-share-status]");
    let sharePayload = null;

    const showStatus = (message, isError = false) => {
      status.hidden = false;
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const getSharePayload = async () => {
      if (sharePayload) return sharePayload;
      showStatus("Preparing a secure share link…");
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("The alert can no longer be shared.");
      const payload = await response.json();
      if (!payload.url || !payload.share_text || !payload.whatsapp_text) {
        throw new Error("A secure share message could not be created.");
      }
      sharePayload = payload;
      return sharePayload;
    };

    const action = async (callback, onError) => {
      try {
        const payload = await getSharePayload();
        await callback(payload);
      } catch (error) {
        if (onError) onError();
        showStatus(error.message || "Sharing is currently unavailable.", true);
      }
    };

    container.querySelector('[data-share-action="copy"]').addEventListener("click", () => {
      action(async (payload) => {
        await copyText(payload.url);
        showStatus("Secure link copied. It contains only the approved public alert information.");
      });
    });

    container.querySelector('[data-share-action="web-share"]').addEventListener("click", () => {
      action(async (payload) => {
        if (navigator.share) {
          try {
            // Keep the URL in the formatted text: some share targets otherwise keep only `url`.
            await navigator.share({ title: payload.share_title, text: payload.share_text });
            showStatus("Share options opened.");
            return;
          } catch (error) {
            if (error && error.name === "AbortError") {
              showStatus("Sharing cancelled.");
              return;
            }
          }
        }
        await copyText(payload.share_text);
        showStatus("Sharing is not supported on this device. The safe incident message was copied instead.");
      });
    });

    container.querySelector('[data-share-action="whatsapp"]').addEventListener("click", () => {
      // Open synchronously to avoid popup blockers, then navigate only that new tab.
      const whatsappWindow = window.open("about:blank", "_blank");
      action(async (payload) => {
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(payload.whatsapp_text)}`;
        if (whatsappWindow) {
          whatsappWindow.opener = null;
          whatsappWindow.location.replace(whatsappUrl);
          return;
        }
        const fallbackWindow = window.open(whatsappUrl, "_blank", "noopener");
        if (!fallbackWindow) {
          await copyText(payload.whatsapp_text);
          showStatus("WhatsApp could not open in a new tab. The safe incident message was copied instead.");
        }
      }, () => {
        if (whatsappWindow && !whatsappWindow.closed) whatsappWindow.close();
      });
    });
  });
});
