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
    const title = container.dataset.alertTitle || "SAVE-US alert";
    const status = container.querySelector("[data-share-status]");
    let secureUrl = null;

    const showStatus = (message, isError = false) => {
      status.hidden = false;
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const getSecureUrl = async () => {
      if (secureUrl) return secureUrl;
      showStatus("Preparing a secure share link…");
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("The alert can no longer be shared.");
      const payload = await response.json();
      if (!payload.url) throw new Error("A secure share link could not be created.");
      secureUrl = payload.url;
      return secureUrl;
    };

    const shareText = (url) => `Source: SAVE-US — ${title}\n${url}`;
    const action = async (callback) => {
      try {
        const url = await getSecureUrl();
        await callback(url);
      } catch (error) {
        showStatus(error.message || "Sharing is currently unavailable.", true);
      }
    };

    container.querySelector('[data-share-action="copy"]').addEventListener("click", () => {
      action(async (url) => {
        await copyText(url);
        showStatus("Secure link copied. It contains only the approved public alert information.");
      });
    });

    container.querySelector('[data-share-action="web-share"]').addEventListener("click", () => {
      action(async (url) => {
        if (navigator.share) {
          try {
            await navigator.share({ title: "SAVE-US alert", text: `Source: SAVE-US — ${title}`, url });
            showStatus("Share options opened.");
            return;
          } catch (error) {
            if (error && error.name === "AbortError") {
              showStatus("Sharing cancelled.");
              return;
            }
          }
        }
        await copyText(url);
        showStatus("Sharing is not supported on this device. The secure link was copied instead.");
      });
    });

    container.querySelector('[data-share-action="whatsapp"]').addEventListener("click", () => {
      action(async (url) => {
        const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText(url))}`;
        window.location.assign(whatsappUrl);
      });
    });
  });
});
