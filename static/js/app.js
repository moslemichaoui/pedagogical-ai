/* ==========================================================================
   منصة الإعداد التربوي — shared browser behaviour.
   No framework. Every hook is declared with data-* attributes so the Content
   Security Policy can stay strict (script-src 'self').
   ========================================================================== */
(function () {
  "use strict";

  const App = {};

  /* --- Toasts ---------------------------------------------------------- */
  App.toast = function (message, kind) {
    const region = document.getElementById("toast-region");
    if (!region) return;
    const node = document.createElement("div");
    node.className = "toast" + (kind ? " toast--" + kind : "");
    const text = document.createElement("span");
    text.textContent = message;
    const close = document.createElement("button");
    close.type = "button";
    close.setAttribute("aria-label", "إغلاق");
    close.textContent = "×";
    close.addEventListener("click", () => node.remove());
    node.append(text, close);
    region.append(node);
    /* The region already announces politely: one live region, no nested role. */
    let timer = window.setTimeout(() => node.remove(), 6000);
    node.addEventListener("mouseenter", () => window.clearTimeout(timer));
    node.addEventListener("focusin", () => window.clearTimeout(timer));
    const resume = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => node.remove(), 3000);
    };
    node.addEventListener("mouseleave", resume);
    node.addEventListener("focusout", resume);
  };

  /* --- Confirm dialog --------------------------------------------------- */
  let confirmResolver = null;
  let confirmTrigger = null;
  const modal = document.getElementById("confirm-modal");

  function modalFocusables() {
    if (!modal) return [];
    return Array.from(
      modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter((node) => !node.disabled && node.offsetParent !== null);
  }

  App.confirm = function (message, options) {
    const settings = Object.assign({ title: "تأكيد", danger: true }, options || {});
    if (!modal) return Promise.resolve(window.confirm(message));
    confirmTrigger = document.activeElement;
    modal.querySelector("#confirm-title").textContent = settings.title;
    modal.querySelector("#confirm-text").textContent = message;
    const yes = modal.querySelector("[data-confirm-yes]");
    yes.className = "btn " + (settings.danger ? "btn--danger" : "btn--primary");
    modal.hidden = false;
    yes.focus();
    return new Promise((resolve) => {
      confirmResolver = resolve;
    });
  };

  function settleConfirm(value) {
    if (modal) modal.hidden = true;
    if (confirmTrigger && typeof confirmTrigger.focus === "function") {
      confirmTrigger.focus();
    }
    confirmTrigger = null;
    if (confirmResolver) {
      confirmResolver(value);
      confirmResolver = null;
    }
  }

  if (modal) {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) settleConfirm(false);
      if (event.target.closest("[data-confirm-no]")) settleConfirm(false);
      if (event.target.closest("[data-confirm-yes]")) settleConfirm(true);
    });
    document.addEventListener("keydown", (event) => {
      if (modal.hidden) return;
      if (event.key === "Escape") {
        settleConfirm(false);
        return;
      }
      if (event.key !== "Tab") return;
      const items = modalFocusables();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  /* --- HTTP ------------------------------------------------------------- */
  App.request = async function (url, options) {
    const settings = Object.assign({ method: "GET", headers: {} }, options || {});
    if (settings.json !== undefined) {
      settings.body = JSON.stringify(settings.json);
      settings.headers["Content-Type"] = "application/json";
      delete settings.json;
    }
    settings.headers["Accept"] = "application/json";
    let response;
    try {
      response = await fetch(url, settings);
    } catch (error) {
      throw Object.assign(new Error("تعذّر الاتصال بالخادم. تحقّق من الشبكة."), {
        code: "network_error",
      });
    }
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
    if (!response.ok || (payload && payload.success === false)) {
      const message =
        (payload && (payload.error || payload.message)) ||
        "حدث خطأ غير متوقع (" + response.status + ").";
      const failure = new Error(message);
      failure.code = payload && payload.code;
      failure.details = payload && (payload.details || payload.validation_errors);
      failure.status = response.status;
      throw failure;
    }
    return payload || {};
  };

  /* --- Busy state ------------------------------------------------------- */
  App.busy = function (button, on, label) {
    if (!button) return;
    if (on) {
      button.dataset.originalHtml = button.innerHTML;
      button.disabled = true;
      button.classList.add("is-busy");
      button.innerHTML =
        '<span class="spinner" aria-hidden="true"></span><span>' +
        (label || "جارٍ العمل…") +
        "</span>";
    } else {
      button.disabled = false;
      button.classList.remove("is-busy");
      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
      }
    }
  };

  /* --- Tabs ------------------------------------------------------------- */
  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach((group) => {
      const tabs = Array.from(group.querySelectorAll("[data-tab]"));
      if (!tabs.length) return;
      const scope = group.parentElement || document;
      const panels = Array.from(scope.querySelectorAll("[data-panel]"));

      const activate = (tab) => {
        tabs.forEach((item) => {
          const active = item === tab;
          item.classList.toggle("is-active", active);
          item.setAttribute("aria-selected", active ? "true" : "false");
          item.tabIndex = active ? 0 : -1;
          const panel = panels.find((node) => node.dataset.panel === item.dataset.tab);
          if (!panel) return;
          panel.hidden = !active;
          panel.setAttribute("aria-labelledby", item.id);
        });
      };

      tabs.forEach((tab, index) => {
        tab.addEventListener("click", () => activate(tab));
        tab.addEventListener("keydown", (event) => {
          let next = null;
          /* RTL: ArrowLeft advances, ArrowRight goes back (WAI-ARIA APG). */
          if (event.key === "ArrowLeft") next = (index + 1) % tabs.length;
          else if (event.key === "ArrowRight") next = (index - 1 + tabs.length) % tabs.length;
          else if (event.key === "Home") next = 0;
          else if (event.key === "End") next = tabs.length - 1;
          if (next === null) return;
          event.preventDefault();
          tabs[next].focus();
          activate(tabs[next]);
        });
      });

      const initial = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      activate(initial);
    });
  }

  /* --- Range labels ----------------------------------------------------- */
  function initRanges() {
    document.querySelectorAll("[data-range]").forEach((input) => {
      const output = document.querySelector(input.dataset.range);
      const sync = () => {
        if (output) output.textContent = input.value + (input.dataset.suffix || "");
      };
      input.addEventListener("input", sync);
      sync();
    });
  }

  /* --- Copy ------------------------------------------------------------- */
  function initCopy() {
    document.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", async () => {
        const text = button.dataset.copy;
        try {
          await navigator.clipboard.writeText(text);
          App.toast("تم النسخ إلى الحافظة.", "ok");
        } catch (error) {
          App.toast("تعذّر النسخ. حدّد النص يدوياً.", "error");
        }
      });
    });
  }

  /* --- Dropzones -------------------------------------------------------- */
  function initDropzones() {
    document.querySelectorAll("[data-dropzone]").forEach((zone) => {
      const input = zone.querySelector('input[type="file"]');
      const label = zone.querySelector("[data-file-name]");
      if (!input) return;
      const update = () => {
        if (label) {
          label.textContent = input.files.length
            ? input.files[0].name
            : label.dataset.empty || "لم يتم اختيار ملف";
        }
        zone.classList.toggle("is-drag", false);
      };
      input.addEventListener("change", update);
      ["dragenter", "dragover"].forEach((name) =>
        zone.addEventListener(name, (event) => {
          event.preventDefault();
          zone.classList.add("is-drag");
        })
      );
      ["dragleave", "drop"].forEach((name) =>
        zone.addEventListener(name, (event) => {
          event.preventDefault();
          zone.classList.remove("is-drag");
        })
      );
      zone.addEventListener("drop", (event) => {
        if (event.dataTransfer && event.dataTransfer.files.length) {
          input.files = event.dataTransfer.files;
          update();
        }
      });
    });
  }

  /* --- Generic delete buttons ------------------------------------------- */
  function initDelete() {
    document.querySelectorAll("[data-delete-url]").forEach((button) => {
      button.addEventListener("click", async () => {
        const ok = await App.confirm(
          button.dataset.confirmText || "سيتم الحذف نهائياً. هل تريد المتابعة؟",
          { title: button.dataset.confirmTitle || "حذف" }
        );
        if (!ok) return;
        App.busy(button, true, "جارٍ الحذف…");
        try {
          await App.request(button.dataset.deleteUrl, { method: "DELETE" });
          App.toast(button.dataset.successText || "تم الحذف.", "ok");
          const target = button.closest("[data-row]");
          if (target) {
            target.style.transition = "opacity 200ms ease, transform 200ms ease";
            target.style.opacity = "0";
            target.style.transform = "translateY(-6px)";
            window.setTimeout(() => {
              target.remove();
              if (!document.querySelector("[data-row]")) window.location.reload();
            }, 220);
          } else if (button.dataset.redirect) {
            window.location.href = button.dataset.redirect;
          } else {
            window.setTimeout(() => window.location.reload(), 400);
          }
        } catch (error) {
          App.toast(error.message, "error");
          App.busy(button, false);
        }
      });
    });
  }

  /* --- Fetch forms ------------------------------------------------------ */
  function initFetchForms() {
    document.querySelectorAll("form[data-fetch]").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector('[type="submit"]');
        App.busy(button, true, form.dataset.busyLabel || "جارٍ الإرسال…");
        const body = new FormData(form);
        try {
          const result = await App.request(form.action, {
            method: form.method || "POST",
            body,
          });
          App.toast(form.dataset.success || "تم بنجاح.", "ok");
          const redirect = form.dataset.redirect || result.redirect_url;
          if (redirect) {
            window.setTimeout(() => (window.location.href = redirect), 350);
          } else if (form.dataset.reload !== "false") {
            window.setTimeout(() => window.location.reload(), 600);
          }
          form.dispatchEvent(
            new CustomEvent("app:success", { detail: result, bubbles: true })
          );
        } catch (error) {
          App.toast(error.message, "error");
          const errorBox = form.querySelector("[data-form-error]");
          if (errorBox) {
            errorBox.hidden = false;
            errorBox.textContent = error.message;
          }
        } finally {
          App.busy(button, false);
        }
      });
    });
  }

  /* --- Flash messages from query string --------------------------------- */
  function initFlash() {
    const params = new URLSearchParams(window.location.search);
    const message = params.get("toast");
    if (message) App.toast(message, params.get("toast_kind") || "ok");
  }

  /* --- Print ------------------------------------------------------------ */
  function initPrint() {
    document.querySelectorAll("[data-print]").forEach((button) => {
      button.addEventListener("click", () => window.print());
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTabs();
    initRanges();
    initCopy();
    initDropzones();
    initDelete();
    initFetchForms();
    initPrint();
    initFlash();
  });

  window.App = App;
})();
