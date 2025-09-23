function openModal(element) {
  element.classList.add("is-active");
}

function closeModal(element) {
  element.classList.remove("is-active");
}

function verificationPrompt(siteKey, message, callback) {
  const modal = "verification-modal";
  const target = document.getElementById(modal);

  document.querySelector(".turnstile-message").textContent = message;

  const widgetId = turnstile.render(".turnstile-container", {
    sitekey: siteKey,
    callback: async function (token) {
      const response = await fetch("/api/verification", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ turnstileResponse: token }),
      });
      const jsonData = await response.json();
      if (response.status != 200) {
        alertMessage(jsonData.detail);
        return;
      }
      closeModal(target);
      await callback();
    },
  });

  openModal(target);
}

document.addEventListener("DOMContentLoaded", () => {
  (
    document.querySelectorAll(
      ".modal-background, .modal-close, .modal-card-head .delete, .modal-card-foot .button"
    ) || []
  ).forEach(($close) => {
    const $target = $close.closest(".modal");

    $close.addEventListener("click", () => {
      closeModal($target);
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllModals();
    }
  });
});
