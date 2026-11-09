(() => {
  const root = document.querySelector('[data-batch-page^="tihu-"]');
  const count = root?.querySelector('[data-batch-count]');
  const lang = document.documentElement.lang;
  if (!count || !['ru', 'pt-BR'].includes(lang)) return;
  const translate = () => {
    const match = count.textContent.match(/^(\d+) reference rows · (\d+) model labels · excluded from case count$/);
    if (match) count.textContent = lang === 'ru'
        ? `Образцов: ${match[1]} · Моделей: ${match[2]} · вне общего числа работ`
        : `Amostras: ${match[1]} · Modelos: ${match[2]} · fora do total de obras`;
    for (const label of root.querySelectorAll('[data-model-count]')) {
      const samples = label.textContent.match(/^(\d+) samples?$/);
      if (samples) label.textContent = lang === 'ru'
        ? `Образцов: ${samples[1]}` : `Amostras: ${samples[1]}`;
    }
    for (const button of root.querySelectorAll('[data-batch-expand]')) {
      const expand = button.dataset.batchExpand === 'true';
      const label = lang === 'ru'
        ? (expand ? 'Развернуть всё' : 'Свернуть всё')
        : (expand ? 'Expandir tudo' : 'Recolher tudo');
      if (button.textContent !== label) button.textContent = label;
    }
  };
  new MutationObserver(translate).observe(root, {childList: true, characterData: true, subtree: true});
  translate();
})();
