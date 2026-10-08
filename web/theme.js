// Run before styles render so the saved choice also covers loading and error states.
(() => {
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const valid = value => ['system', 'light', 'dark'].includes(value);
  let choice = 'system';
  try {
    const saved = localStorage.getItem('marchlab.theme');
    if (valid(saved)) choice = saved;
  } catch (_) { /* The system choice still works when storage is unavailable. */ }

  function apply() {
    root.dataset.themeChoice = choice;
    root.dataset.theme = choice === 'system' ? (system.matches ? 'dark' : 'light') : choice;
  }
  apply();
  system.addEventListener('change', () => { if (choice === 'system') apply(); });
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.querySelector('#theme-choice');
    select.value = choice;
    select.addEventListener('change', () => {
      if (!valid(select.value)) return;
      choice = select.value;
      apply();
      try { localStorage.setItem('marchlab.theme', choice); } catch (_) { /* Keep the current choice for this visit. */ }
    });
  });
})();
