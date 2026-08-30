import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import {
  createUserWithEmailAndPassword,
  browserLocalPersistence,
  getAuth,
  GoogleAuthProvider,
  sendPasswordResetEmail,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from "https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js";

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

/**
 * Translate Firebase error codes into clear, user-friendly messages.
 */
function friendlyAuthError(error) {
  const code = error?.code || "";
  const map = {
    "auth/invalid-credential":       "Wrong email or password. Please check and try again.",
    "auth/user-not-found":           "No account found with this email. Please register first.",
    "auth/wrong-password":           "Incorrect password. Please try again or reset your password.",
    "auth/email-already-in-use":     "An account with this email already exists. Try logging in instead.",
    "auth/invalid-email":            "The email address is not valid. Please check the format.",
    "auth/weak-password":            "Password is too weak. Use at least 8 characters with letters and numbers.",
    "auth/too-many-requests":        "Too many failed attempts. Please wait a moment and try again.",
    "auth/network-request-failed":   "Network error. Check your internet connection and try again.",
    "auth/popup-closed-by-user":     "Google sign-in was cancelled. Try again when ready.",
    "auth/popup-blocked":            "Pop-up was blocked by your browser. Allow pop-ups for this site and try again.",
    "auth/account-exists-with-different-credential": "An account already exists with a different sign-in method. Try email/password or Google.",
    "auth/user-disabled":            "This account has been disabled. Contact support.",
    "auth/operation-not-allowed":    "This sign-in method is not enabled. Contact support.",
    "auth/requires-recent-login":    "Please log in again to complete this action.",
    "auth/credential-already-in-use":"This credential is already linked to another account.",
    "auth/invalid-action-code":      "This link has expired or already been used. Request a new one.",
    "auth/expired-action-code":      "This link has expired. Please request a new password reset.",
  };
  return map[code] || error?.message || "Authentication failed. Please try again.";
}

function setMessage(form, type, message) {
  const error = form.querySelector("[data-auth-error]");
  const success = form.querySelector("[data-auth-success]");
  if (error) error.hidden = true;
  if (success) success.hidden = true;
  const target = type === "error" ? error : success;
  if (target) {
    target.textContent = message;
    target.hidden = false;
    target.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

let matrixAnimId = null;
let progressBarAnimId = null;

function initMatrixStream() {
  const canvas = document.getElementById("binary-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  const chars = "01010101010101010189ABCDEF$#@%&*";
  const fontSize = 16;
  const columns = Math.floor(canvas.width / fontSize) + 1;
  const drops = Array(columns).fill(1);

  function draw() {
    ctx.fillStyle = "rgba(2, 8, 4, 0.1)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#66FF99";
    ctx.font = `${fontSize}px VT323, monospace`;

    for (let i = 0; i < drops.length; i++) {
      const text = chars.charAt(Math.floor(Math.random() * chars.length));
      ctx.fillText(text, i * fontSize, drops[i] * fontSize);
      if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
        drops[i] = 0;
      }
      drops[i]++;
    }
    matrixAnimId = requestAnimationFrame(draw);
  }
  draw();
}

function startProgressBarAnimation(statusText) {
  const statusEl = document.getElementById("loader-status-stream");
  const barEl = document.getElementById("loader-progress-bar");
  if (statusEl && statusText) statusEl.textContent = statusText;

  const totalBlocks = 20;
  let filled = 0;
  let direction = 1;

  const steps = [
    statusText || "AUTHENTICATING USER...",
    "VERIFYING CRYPTOGRAPHIC HANDSHAKE...",
    "ESTABLISHING D-OS SECURE SESSION...",
    "INITIALIZING MEMORY BUFFERS..."
  ];
  let stepIdx = 0;

  function update() {
    filled += direction;
    if (filled >= totalBlocks) {
      filled = totalBlocks;
      direction = -1;
      stepIdx = (stepIdx + 1) % steps.length;
      if (statusEl) statusEl.textContent = steps[stepIdx];
    } else if (filled <= 0) {
      filled = 0;
      direction = 1;
    }

    const blocks = "█".repeat(filled) + "░".repeat(totalBlocks - filled);
    if (barEl) barEl.textContent = `[${blocks}]`;

    progressBarAnimId = setTimeout(update, 80);
  }
  update();
}

function showTerminalLoader(statusText) {
  const loader = document.getElementById("terminal-loader");
  if (!loader) return;
  loader.classList.add("active");
  loader.setAttribute("aria-hidden", "false");
  initMatrixStream();
  startProgressBarAnimation(statusText);
}

function hideTerminalLoader() {
  const loader = document.getElementById("terminal-loader");
  if (!loader) return;
  loader.classList.remove("active");
  loader.setAttribute("aria-hidden", "true");
  if (matrixAnimId) cancelAnimationFrame(matrixAnimId);
  if (progressBarAnimId) clearTimeout(progressBarAnimId);
}

async function createServerSession(idToken) {
  const response = await fetch("/session-login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": decodeURIComponent(getCookie("dos_csrf") || ""),
    },
    body: JSON.stringify({ idToken }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Could not create secure session.");
  }
}

async function boot() {
  const form = document.querySelector("[data-auth-form]");
  if (!form) return;

  const configResponse = await fetch("/auth/firebase-config");
  const firebaseConfig = await configResponse.json();

  if (!firebaseConfig.configured) {
    setMessage(form, "error", "Firebase web configuration is missing.");
    form.querySelectorAll("button,input").forEach((element) => {
      if (element.type !== "button") element.disabled = true;
    });
    return;
  }

  const app = initializeApp(firebaseConfig.config);
  const auth = getAuth(app);
  await setPersistence(auth, browserLocalPersistence);
  const mode = form.dataset.authForm;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const email = String(data.get("email") || "").trim();
    const password = String(data.get("password") || "");
    try {
      if (mode === "login") {
        showTerminalLoader("AUTHENTICATING USER...");
        const credential = await signInWithEmailAndPassword(auth, email, password);
        const idToken = await credential.user.getIdToken();
        await createServerSession(idToken);
        window.location.assign("/");
      }
      if (mode === "register") {
        const confirm = String(data.get("confirm_password") || "");
        const username = String(data.get("username") || "").trim();
        if (password !== confirm) throw new Error("Passwords do not match.");
        showTerminalLoader("REGISTERING TERMINAL USER...");
        const credential = await createUserWithEmailAndPassword(auth, email, password);
        if (username) await updateProfile(credential.user, { displayName: username });
        const idToken = await credential.user.getIdToken();
        await createServerSession(idToken);
        window.location.assign("/");
      }
      if (mode === "forgot") {
        showTerminalLoader("TRANSMITTING RESET PROTOCOL...");
        await sendPasswordResetEmail(auth, email);
        hideTerminalLoader();
        setMessage(form, "success", "Password reset email sent.");
      }
    } catch (error) {
      hideTerminalLoader();
      setMessage(form, "error", friendlyAuthError(error));
    }
  });

  form.querySelectorAll("[data-google-login]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        showTerminalLoader("AUTHENTICATING GOOGLE OAUTH...");
        const credential = await signInWithPopup(auth, new GoogleAuthProvider());
        const idToken = await credential.user.getIdToken();
        await createServerSession(idToken);
        window.location.assign("/");
      } catch (error) {
        hideTerminalLoader();
        setMessage(form, "error", friendlyAuthError(error));
      }
    });
  });
}

function initPasswordToggles() {
  const eyeOpen = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeSlash = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

  document.querySelectorAll('[data-toggle-password]').forEach(function(btn) {
    if (btn.dataset.bound === 'true') return;
    btn.dataset.bound = 'true';
    // Set initial icon
    btn.innerHTML = eyeOpen;
    btn.addEventListener('click', function() {
      var wrap = this.closest('.password-input-wrap');
      if (!wrap) return;
      var input = wrap.querySelector('input');
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        this.innerHTML = eyeSlash;
        this.setAttribute('aria-label', 'Hide password');
        this.setAttribute('title', 'Hide password');
        this.classList.add('active');
      } else {
        input.type = 'password';
        this.innerHTML = eyeOpen;
        this.setAttribute('aria-label', 'Show password');
        this.setAttribute('title', 'Show password');
        this.classList.remove('active');
      }
    });
  });
}

initPasswordToggles();
boot();

