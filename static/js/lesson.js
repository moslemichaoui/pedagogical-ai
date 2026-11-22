/* Lesson detail: on-demand exercise and assessment generation. */
(function () {
  "use strict";

  const App = window.App;

  async function run(button, url, body, successMessage) {
    App.busy(button, true, "جارٍ التوليد…");
    try {
      const result = await App.request(url, { method: "POST", json: body || {} });
      App.toast(successMessage, "ok");
      window.setTimeout(() => window.location.reload(), 600);
      return result;
    } catch (error) {
      App.toast(error.message, "error");
      App.busy(button, false);
      throw error;
    }
  }

  document.querySelectorAll("[data-generate-exercises]").forEach((button) => {
    button.addEventListener("click", () => {
      const select = document.getElementById("exercise-count");
      const count = select ? Number(select.value) : 8;
      run(button, button.dataset.generateExercises, { count }, "تم توليد التمارين وحفظها.").catch(
        () => {}
      );
    });
  });

  document.querySelectorAll("[data-generate-assessments]").forEach((button) => {
    button.addEventListener("click", () => {
      run(
        button,
        button.dataset.generateAssessments,
        { count: 6, kinds: ["formative", "summative"] },
        "تم توليد أسئلة التقويم."
      ).catch(() => {});
    });
  });
})();
