(() => {
  "use strict";

  const getStoredTheme = () => localStorage.getItem("theme");
  const setStoredTheme = (theme) => localStorage.setItem("theme", theme);

  const getPreferredTheme = () => {
    const storedTheme = getStoredTheme();
    if (storedTheme) {
      return storedTheme;
    }

    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  };

  const setTheme = (theme) => {
    if (theme === "auto") {
      document.documentElement.setAttribute(
        "data-bs-theme",
        window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light"
      );
    } else {
      document.documentElement.setAttribute("data-bs-theme", theme);
    }
  };

  setTheme(getPreferredTheme());

  const showActiveTheme = (theme, focus = false) => {
    const themeSwitcher = document.querySelector("#bd-theme");

    if (!themeSwitcher) {
      return;
    }

    const themeSwitcherText = document.querySelector("#bd-theme-text");
    const activeThemeIcon = document.querySelector(".theme-icon-active use");
    const btnToActive = document.querySelector(
      `[data-bs-theme-value="${theme}"]`
    );
    const svgOfActiveBtn = btnToActive
      .querySelector("svg use")
      .getAttribute("href");

    document.querySelectorAll("[data-bs-theme-value]").forEach((element) => {
      element.classList.remove("active");
      element.setAttribute("aria-pressed", "false");
    });

    btnToActive.classList.add("active");
    btnToActive.setAttribute("aria-pressed", "true");
    activeThemeIcon.setAttribute("href", svgOfActiveBtn);
    const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`;
    themeSwitcher.setAttribute("aria-label", themeSwitcherLabel);

    if (focus) {
      themeSwitcher.focus();
    }
  };

  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", () => {
      const storedTheme = getStoredTheme();
      if (storedTheme !== "light" && storedTheme !== "dark") {
        setTheme(getPreferredTheme());
      }
    });

  window.addEventListener("DOMContentLoaded", () => {
    showActiveTheme(getPreferredTheme());

    document.querySelectorAll("[data-bs-theme-value]").forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const theme = toggle.getAttribute("data-bs-theme-value");
        setStoredTheme(theme);
        setTheme(theme);
        showActiveTheme(theme, true);
      });
    });
  });
})();

document
  .getElementById("upcoming-button")
  .addEventListener("click", function () {});
document.getElementById("filter-button").addEventListener("click", function () {
  fetch("filter-workshops/")
    .then((response) => response.json())
    .then((data) => {
      const workshopsList = document.getElementById("workshops-list");
      workshopsList.innerHTML = ""; // Clear existing list items
      data.forEach((workshop) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.classList.add(
          "d-flex",
          "flex-column",
          "flex-lg-row",
          "gap-3",
          "align-items-start",
          "align-items-lg-center",
          "py-3",
          "link-body-emphasis",
          "text-decoration-none",
          "border-bottom"
        );
        a.href = "#";
        const div = document.createElement("div");
        div.classList.add("col-lg-12");
        const h5 = document.createElement("h5");
        h5.classList.add("mb-1", "text-primary-emphasis");
        h5.textContent = workshop.workshopname;
        const small = document.createElement("small");
        small.classList.add("text-body-secondary");
        small.textContent =
          workshop.workshopstartdate + " - " + workshop.workshopenddate;
        div.appendChild(h5);
        div.appendChild(small);
        a.appendChild(div);
        li.appendChild(a);
        workshopsList.appendChild(li);
      });
    })
    .catch((error) => console.error("Error:", error));
});

const prev = document.getElementById("prev-btn");
const next = document.getElementById("next-btn");
const list = document.getElementById("horizontal-container");

const itemWidth = 300;
const padding = 10;

prev.addEventListener("click", () => {
  list.scrollLeft -= itemWidth + padding;
  console.log(list.scrollLeft);
});

next.addEventListener("click", () => {
  list.scrollLeft += itemWidth + padding;
  console.log(list.scrollLeft);
});
