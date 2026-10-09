(() => {
  document.querySelectorAll("pre code").forEach(block => {
    block.textContent = block.textContent.replaceAll("https://ednai-6znf.onrender.com", window.location.origin);
  });
  const code = document.getElementById("heroCodeSample");
  const more = document.getElementById("heroMoreCodeBtn");
  const options = document.getElementById("heroMoreCodeOptions");
  const timers = new WeakMap();

  async function writeClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (_) {
      // Older browsers and clipboard permissions can require the selection API.
      const focus = document.activeElement;
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      try {
        area.select();
        if (!document.execCommand("copy")) throw new Error("Clipboard unavailable");
      } finally {
        area.remove();
        if (focus instanceof HTMLElement) focus.focus({ preventScroll: true });
      }
    }
  }

  function resetCopy(button, label) {
    clearTimeout(timers.get(button));
    button.textContent = label;
  }

  function attachCopy(button, source, label) {
    button.addEventListener("click", async () => {
      resetCopy(button, label);
      try {
        await writeClipboard(source.textContent);
        button.textContent = "Copied";
      } catch (_) {
        button.textContent = "Copy failed";
      }
      timers.set(button, setTimeout(() => { button.textContent = label; }, 1600));
    });
  }

  if (code && more && options) {
    const samples = {
      curl: code.textContent,
      python: `import os
from ednai import EDNAi

ai = EDNAi(
    base_url="${window.location.origin}",
    api_key=os.environ["EDNAI_API_KEY"]
)
result = ai.generate("Explain APIs simply.")
print(result.text)`,
      javascript: `import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "${window.location.origin}",
  apiKey: process.env.EDNAI_API_KEY
});
const result = await ai.generate("Explain APIs simply.");
console.log(result.text);`,
      typescript: `import { EDNAi } from "@ednai/sdk";

const ai = new EDNAi({
  baseUrl: "${window.location.origin}",
  apiKey: process.env.EDNAI_API_KEY
});
const prompt: string = "Explain APIs simply.";
const result = await ai.generate(prompt);
console.log(result.text);`
    };
    const copy = document.getElementById("heroCopyCodeBtn");
    const selectors = document.querySelectorAll("[data-hero-stack]");
    const closeOptions = () => {
      options.hidden = true;
      more.setAttribute("aria-expanded", "false");
    };

    selectors.forEach(button => {
      button.addEventListener("click", () => {
        const stack = button.dataset.heroStack;
        if (!samples[stack]) return;
        code.textContent = samples[stack];
        code.dataset.language = stack;
        selectors.forEach(item => {
          const selected = item.dataset.heroStack === stack;
          item.classList.toggle("active", selected);
          item.setAttribute("aria-pressed", String(selected));
        });
        more.classList.toggle("active", stack === "typescript");
        more.textContent = stack === "typescript" ? "TypeScript⌄" : "More⌄";
        resetCopy(copy, "▣ Copy");
        closeOptions();
        if (stack === "typescript") more.focus();
      });
    });
    more.addEventListener("click", () => {
      const opening = options.hidden;
      options.hidden = !opening;
      more.setAttribute("aria-expanded", String(opening));
      if (opening) options.querySelector("button").focus();
    });
    document.addEventListener("click", event => {
      if (!more.contains(event.target) && !options.contains(event.target)) closeOptions();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !options.hidden) {
        closeOptions();
        more.focus();
      }
    });
    options.addEventListener("focusout", event => {
      if (!options.contains(event.relatedTarget) && event.relatedTarget !== more) closeOptions();
    });
    if (copy) attachCopy(copy, code, "▣ Copy");
  }

  document.querySelectorAll(".docs-code").forEach(block => {
    const source = block.querySelector("code");
    if (!source) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "docs-copy-button";
    button.textContent = "Copy";
    button.setAttribute("aria-live", "polite");
    const heading = block.closest("section")?.querySelector("h2")?.textContent || "code example";
    button.setAttribute("aria-label", `Copy ${heading}`);
    block.appendChild(button);
    attachCopy(button, source, "Copy");
  });
})();
