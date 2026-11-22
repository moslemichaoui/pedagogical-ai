/* Lesson creation: progressive generation feedback + request handling. */
(function () {
  "use strict";

  const form = document.getElementById("lesson-form");
  if (!form) return;

  const overlay = document.getElementById("gen-overlay");
  const progress = document.getElementById("gen-progress");
  const steps = Array.from(document.querySelectorAll("#gen-steps .gen-step"));
  const note = document.getElementById("gen-note");
  const errorBox = form.querySelector("[data-form-error]");
  const sourcesField = document.getElementById("sources-field");
  const useDocuments = document.getElementById("use_documents");
  const submit = form.querySelector('[type="submit"]');
  const progressTrack = document.querySelector("#gen-overlay .progress");
  const genTitle = document.getElementById("gen-title");

  const DRAFT_KEY = "pedagogical.draft.v1";
  const tracked = ["topic", "objectives", "teacher_instructions"];

  /* --- Draft persistence ------------------------------------------------ */
  try {
    const saved = JSON.parse(localStorage.getItem(DRAFT_KEY) || "{}");
    tracked.forEach((name) => {
      const field = form.elements[name];
      if (field && !field.value && saved[name]) field.value = saved[name];
    });
  } catch (error) {
    /* ignore corrupted draft */
  }

  form.addEventListener("input", (event) => {
    if (event.target === form.elements.topic) {
      form.elements.topic.removeAttribute("aria-invalid");
      form.elements.topic.setAttribute("aria-describedby", "topic-hint");
    }
    const draft = {};
    tracked.forEach((name) => {
      if (form.elements[name]) draft[name] = form.elements[name].value;
    });
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch (error) {
      /* storage may be unavailable */
    }
  });

  /* --- Source toggle ---------------------------------------------------- */
  if (useDocuments && sourcesField) {
    const sync = () => {
      const enabled = useDocuments.checked;
      sourcesField.classList.toggle("is-disabled", !enabled);
      sourcesField.querySelectorAll("input").forEach((input) => {
        input.disabled = !enabled;
      });
    };
    useDocuments.addEventListener("change", sync);
    sync();
  }

  /* --- Progress choreography ------------------------------------------- */
  let timers = [];
  const milestones = [
    { at: 900, step: 1, width: 26, note: "نحلّل طلبك ونختار الأهداف." },
    { at: 4200, step: 2, width: 58, note: "نسترجع المقاطع الأقرب من وثائقك." },
    { at: 11000, step: 3, width: 82, note: "نبني أقسام الجذاذة ومراحلها." },
    {
      at: 24000,
      step: 3,
      note: "النموذج ما زال يعمل… شكراً لصبرك.",
      indeterminate: true,
    },
  ];

  function setProgress(width) {
    if (progress) progress.style.width = width + "%";
    if (progressTrack) {
      progressTrack.classList.remove("is-indeterminate");
      progressTrack.setAttribute("aria-valuenow", String(width));
      progressTrack.removeAttribute("aria-valuetext");
    }
  }

  function startProgress() {
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    steps.forEach((step, index) => {
      step.classList.toggle("is-active", index === 0);
      step.classList.remove("is-done");
    });
    setProgress(8);
    if (note) note.textContent = "لا تغلق الصفحة.";
    if (genTitle) genTitle.focus();
    timers = milestones.map((milestone) =>
      window.setTimeout(() => {
        steps.forEach((step, index) => {
          step.classList.toggle("is-active", index === milestone.step);
          step.classList.toggle("is-done", index < milestone.step);
        });
        if (milestone.indeterminate) {
          if (progressTrack) {
            progressTrack.classList.add("is-indeterminate");
            progressTrack.removeAttribute("aria-valuenow");
            progressTrack.setAttribute("aria-valuetext", "جارٍ العمل، الوقت التقريبي غير معروف");
          }
        } else {
          setProgress(milestone.width);
        }
        if (milestone.note && note) note.textContent = milestone.note;
      }, milestone.at)
    );
  }

  function stopProgress() {
    timers.forEach((timer) => window.clearTimeout(timer));
    timers = [];
    overlay.hidden = true;
    document.body.style.overflow = "";
    if (progressTrack) progressTrack.classList.remove("is-indeterminate");
    if (submit) submit.focus();
  }

  function showError(message) {
    if (!errorBox) {
      window.App.toast(message, "error");
      return;
    }
    errorBox.hidden = false;
    errorBox.textContent = message;
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    errorBox.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "center" });
    const topic = form.elements.topic;
    if (topic && /موضوع الدرس/.test(message)) {
      topic.setAttribute("aria-invalid", "true");
      topic.setAttribute("aria-describedby", "topic-hint create-error");
    }
  }

  /* --- Submit ----------------------------------------------------------- */
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (errorBox) {
      errorBox.hidden = true;
      errorBox.textContent = "";
    }
    const topicField = form.elements.topic;
    if (topicField) {
      topicField.removeAttribute("aria-invalid");
      if (topicField.getAttribute("aria-describedby") === "topic-hint create-error") {
        topicField.setAttribute("aria-describedby", "topic-hint");
      }
    }

    const topic = (form.elements.topic.value || "").trim();
    if (topic.length < 2) {
      showError("اكتب موضوع الدرس أولاً (حرفان على الأقل).");
      form.elements.topic.focus();
      return;
    }

    if (submit) submit.disabled = true;
    startProgress();

    /* Never leave the modal spinner up forever if the server stalls. */
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const timeoutId = controller
      ? window.setTimeout(() => controller.abort(), 180000)
      : null;

    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
        ...(controller ? { signal: controller.signal } : {}),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || payload.success === false) {
        throw new Error(payload.error || "تعذّر توليد الجذاذة. أعد المحاولة.");
      }

      steps.forEach((step) => {
        step.classList.remove("is-active");
        step.classList.add("is-done");
      });
      setProgress(100);
      if (note) note.textContent = "تم! نفتح جذاذتك…";

      try {
        localStorage.removeItem(DRAFT_KEY);
      } catch (error) {
        /* ignore */
      }

      window.setTimeout(() => {
        window.location.href = payload.redirect_url || "/library";
      }, 550);
    } catch (error) {
      stopProgress();
      if (submit) submit.disabled = false;
      const message =
        error && error.name === "AbortError"
          ? "استغرق التوليد وقتاً طويلاً. أعد المحاولة وتأكّد من ضبط مفتاح Gemini."
          : (error && error.message) || "تعذّر توليد الجذاذة. أعد المحاولة.";
      showError(message);
      if (window.App && typeof window.App.toast === "function") {
        window.App.toast(message, "error");
      }
    } finally {
      if (timeoutId) window.clearTimeout(timeoutId);
    }
  });
})();
