(() => {
  const root = document.documentElement;
  const themeIcon = document.getElementById('theme-icon');
  const themeLabel = document.getElementById('theme-label');

  const themes = {
    light: { icon: '🌞', label: 'Light' },
    dark: { icon: '🌙', label: 'Dark' },
    auto: { icon: '⚙️', label: 'Auto' }
  };

  const getStoredTheme = () => localStorage.getItem('theme') || 'auto';
  const setStoredTheme = (theme) => localStorage.setItem('theme', theme);

  const applyTheme = (theme) => {
    if (theme === 'auto') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    root.setAttribute('data-bs-theme', theme);
  };

  const updateUI = (theme) => {
    themeIcon.textContent = themes[theme]?.icon || themes.auto.icon;
    themeLabel.textContent = themes[theme]?.label || themes.auto.label;
  };

  const init = () => {
    let theme = getStoredTheme();
    applyTheme(theme);
    updateUI(theme);

    document.querySelectorAll('[data-theme]').forEach(button => {
      button.addEventListener('click', () => {
        const newTheme = button.dataset.theme;
        setStoredTheme(newTheme);
        applyTheme(newTheme);
        updateUI(newTheme);
      });
    });

    // Auto update if system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (getStoredTheme() === 'auto') applyTheme('auto');
    });
  };

  init();
})();

const prev = document.getElementById("prev-btn");
const next = document.getElementById("next-btn");
const list = document.getElementById("horizontal-container");
const itemWidth = 300;
const padding = 10;

if (prev !== null) {
  prev.addEventListener("click", () => {
    list.scrollLeft -= itemWidth + padding;
    console.log(list.scrollLeft);
  });

  next.addEventListener("click", () => {
    list.scrollLeft += itemWidth + padding;
    console.log(list.scrollLeft);
  });
}
