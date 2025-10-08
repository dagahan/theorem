import katex from 'katex';
import 'katex/dist/katex.min.css';

class LaTeXRenderer {
  constructor() {
    this.options = {
      throwOnError: false,
      displayMode: false,
      strict: false,
      trust: false,
      macros: {
        "\\f": "#1f(#2)",
        "\\RR": "\\mathbb{R}",
        "\\NN": "\\mathbb{N}",
        "\\ZZ": "\\mathbb{Z}",
        "\\QQ": "\\mathbb{Q}",
        "\\CC": "\\mathbb{C}",
        "\\lim": "\\lim\\limits",
        "\\sum": "\\sum\\limits",
        "\\prod": "\\prod\\limits",
        "\\int": "\\int\\limits"
      }
    };
  }

  renderInline(text) {
    try {
      return katex.renderToString(text, {
        ...this.options,
        displayMode: false
      });
    } catch (error) {
      console.warn('LaTeX inline render error:', error);
      return `<span class="latex-error" title="LaTeX Error: ${error.message}" data-original="${text}">${text}</span>`;
    }
  }

  renderDisplay(text) {
    try {
      return katex.renderToString(text, {
        ...this.options,
        displayMode: true
      });
    } catch (error) {
      console.warn('LaTeX display render error:', error);
      return `<div class="latex-error" title="LaTeX Error: ${error.message}" data-original="${text}">${text}</div>`;
    }
  }

  processText(text) {
    if (!text || typeof text !== 'string') {
      return text;
    }

    let processedText = text;
    
    // 1) Обрабатываем окружения (сначала, чтобы избежать конфликтов)
    processedText = processedText.replace(/\\begin\{align\}([\s\S]*?)\\end\{align\}/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderDisplay(cleanFormula);
        return `<div class="latex-display align" data-original="${match}">${rendered}</div>`;
      }
      return match;
    });

    processedText = processedText.replace(/\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderDisplay(cleanFormula);
        return `<div class="latex-display equation" data-original="${match}">${rendered}</div>`;
      }
      return match;
    });

    processedText = processedText.replace(/\\begin\{pmatrix\}([\s\S]*?)\\end\{pmatrix\}/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderDisplay(`\\begin{pmatrix}${cleanFormula}\\end{pmatrix}`);
        return `<div class="latex-display" data-original="${match}">${rendered}</div>`;
      }
      return match;
    });

    // 2) Обрабатываем display формулы
    processedText = processedText.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderDisplay(cleanFormula);
        return `<div class="latex-display" data-original="${match}">${rendered}</div>`;
      }
      return match;
    });

    processedText = processedText.replace(/\\\[([\s\S]*?)\\\]/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderDisplay(cleanFormula);
        return `<div class="latex-display" data-original="${match}">${rendered}</div>`;
      }
      return match;
    });

    // 3) Обрабатываем inline формулы
    processedText = processedText.replace(/\\\(([\s\S]*?)\\\)/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderInline(cleanFormula);
        return `<span class="latex-inline" data-original="${match}">${rendered}</span>`;
      }
      return match;
    });

    processedText = processedText.replace(/\$([^$\n]+?)\$/g, (match, formula) => {
      const cleanFormula = formula.trim();
      if (cleanFormula) {
        const rendered = this.renderInline(cleanFormula);
        return `<span class="latex-inline" data-original="${match}">${rendered}</span>`;
      }
      return match;
    });

    return processedText;
  }

  renderElement(element) {
    if (!element) return;

    // Обрабатываем текстовые узлы
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );

    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
      // Пропускаем текстовые узлы внутри уже отрендеренных LaTeX элементов
      const parent = node.parentNode;
      if (parent && (parent.classList.contains('latex-inline') || 
                     parent.classList.contains('latex-display') ||
                     parent.closest('.latex-inline, .latex-display'))) {
        continue;
      }
      textNodes.push(node);
    }

    textNodes.forEach(textNode => {
      const parent = textNode.parentNode;
      if (parent && parent.tagName !== 'SCRIPT' && parent.tagName !== 'STYLE') {
        const processedHTML = this.processText(textNode.textContent);
        if (processedHTML !== textNode.textContent) {
          const wrapper = document.createElement('span');
          wrapper.innerHTML = processedHTML;
          parent.replaceChild(wrapper, textNode);
        }
      }
    });
  }
}

export const latexRenderer = new LaTeXRenderer();