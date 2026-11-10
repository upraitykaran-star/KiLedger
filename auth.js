(() => {
  "use strict";
  const form = document.querySelector("#auth-form");
  const nameField = document.querySelector("#name-field");
  const businessField = document.querySelector("#business-field");
  const title = document.querySelector("#auth-title");
  const subtitle = document.querySelector("#auth-subtitle");
  const submitLabel = document.querySelector("#submit-label");
  const toggle = document.querySelector("#mode-toggle");
  const switchCopy = document.querySelector("#switch-copy");
  const message = document.querySelector("#auth-message");
  const password = form.elements.password;
  let isSignup = new URLSearchParams(window.location.search).get("mode") === "signup";

  function showMessage(text, kind = "error") {
    message.textContent = text;
    message.dataset.kind = kind;
    message.classList.remove("hidden");
  }
  function renderMode() {
    nameField.classList.toggle("hidden", !isSignup);
    nameField.querySelector("input").required = isSignup;
    businessField.classList.toggle("hidden", !isSignup);
    businessField.querySelector("input").required = isSignup;
    password.autocomplete = isSignup ? "new-password" : "current-password";
    password.minLength = isSignup ? 12 : 1;
    title.textContent = isSignup ? "Create your account" : "Welcome back";
    subtitle.textContent = isSignup ? "Create your secure KiLedger business workspace." : "Sign in to open your business workspace.";
    submitLabel.textContent = isSignup ? "Create account" : "Sign in to workspace";
    switchCopy.firstChild.textContent = isSignup ? "Already have an account? " : "New to KiLedger? ";
    toggle.textContent = isSignup ? "Sign in" : "Create an account";
    document.title = `${isSignup ? "Create account" : "Sign in"} | KiLedger`;
  }
  toggle.addEventListener("click", () => { isSignup = !isSignup; message.classList.add("hidden"); renderMode(); });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    message.classList.add("hidden");
    try {
      const email = form.elements.email.value.trim().toLowerCase();
      if (isSignup) {
        await KiLedgerAPI.register({ name: form.elements.name.value.trim(), business_name: form.elements.businessName.value.trim(), email, password: password.value });
      } else {
        await KiLedgerAPI.login({ email, password: password.value });
      }
      window.location.href = "app.html";
    } catch (error) {
      showMessage(error.message || "Sign in could not be completed.");
      button.disabled = false;
    }
  });
  renderMode();
})();
