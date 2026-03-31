import { useEffect, useMemo, useRef } from "react";
import DOMPurify from "dompurify";
import hljs from "highlight.js";
import MarkdownIt from "markdown-it";
import "highlight.js/styles/github.min.css";

const COLLAPSE_LINE_LIMIT = 18;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeLanguage(info: string): string {
  return info.trim().split(/\s+/)[0]?.toLowerCase() ?? "";
}

function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise<void>((resolve, reject) => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const copied = document.execCommand("copy");
    document.body.removeChild(textarea);
    if (copied) {
      resolve();
      return;
    }
    reject(new Error("copy_failed"));
  });
}

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});

md.renderer.rules.fence = (tokens, idx): string => {
  const token = tokens[idx];
  const code = token.content;
  const language = normalizeLanguage(token.info);
  const displayLanguage = language || "text";
  const lineCount = code.split(/\r?\n/).length;
  const collapsible = lineCount > COLLAPSE_LINE_LIMIT;

  let highlightedCode = md.utils.escapeHtml(code);
  if (language && hljs.getLanguage(language)) {
    highlightedCode = hljs.highlight(code, { language, ignoreIllegals: true }).value;
  }

  const codeClass = `hljs language-${escapeHtml(displayLanguage)}`;
  const preClass = collapsible ? "md-code-content is-collapsed" : "md-code-content";
  const toggleButton = collapsible
    ? '<button type="button" class="md-code-action md-toggle-btn" data-state="collapsed">展开</button>'
    : "";

  return `
<div class="md-code-block">
  <div class="md-code-header">
    <span class="md-code-lang">${escapeHtml(displayLanguage)}</span>
    <div class="md-code-actions">
      ${toggleButton}
      <button type="button" class="md-code-action md-copy-btn">复制</button>
    </div>
  </div>
  <pre class="${preClass}"><code class="${codeClass}">${highlightedCode}</code></pre>
</div>
`;
};

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const timeoutIdsRef = useRef<number[]>([]);

  const html = useMemo(() => {
    const rendered = md.render(content);
    return DOMPurify.sanitize(rendered, {
      USE_PROFILES: { html: true },
    });
  }, [content]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const handleClick = (event: Event): void => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      const copyButton = target.closest(".md-copy-btn");
      if (copyButton instanceof HTMLButtonElement) {
        const block = copyButton.closest(".md-code-block");
        const codeElement = block?.querySelector("pre code");
        const text = codeElement?.textContent ?? "";
        void copyText(text)
          .then(() => {
            copyButton.textContent = "已复制";
          })
          .catch(() => {
            copyButton.textContent = "复制失败";
          })
          .finally(() => {
            const timeoutId = window.setTimeout(() => {
              copyButton.textContent = "复制";
            }, 1200);
            timeoutIdsRef.current.push(timeoutId);
          });
        return;
      }

      const toggleButton = target.closest(".md-toggle-btn");
      if (toggleButton instanceof HTMLButtonElement) {
        const block = toggleButton.closest(".md-code-block");
        const pre = block?.querySelector("pre");
        if (!(pre instanceof HTMLPreElement)) {
          return;
        }
        const isCollapsed = pre.classList.contains("is-collapsed");
        if (isCollapsed) {
          pre.classList.remove("is-collapsed");
          toggleButton.dataset.state = "expanded";
          toggleButton.textContent = "收起";
          return;
        }
        pre.classList.add("is-collapsed");
        toggleButton.dataset.state = "collapsed";
        toggleButton.textContent = "展开";
      }
    };

    container.addEventListener("click", handleClick);
    return () => {
      container.removeEventListener("click", handleClick);
      timeoutIdsRef.current.forEach((id) => {
        window.clearTimeout(id);
      });
      timeoutIdsRef.current = [];
    };
  }, [html]);

  const mergedClassName = className ? `markdown-body ${className}` : "markdown-body";

  return <div ref={containerRef} className={mergedClassName} dangerouslySetInnerHTML={{ __html: html }} />;
}
