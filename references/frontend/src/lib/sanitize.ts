/**
 * Lightweight client-side HTML sanitizer using native DOMParser.
 * Avoids heavy dompurify npm dependency while protecting from basic XSS.
 */
export function sanitizeReport(html: string): string {
  if (typeof window === "undefined") return html;
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    // Remove forbidden tags
    const forbiddenTags = ["script", "style", "iframe", "object", "embed"];
    forbiddenTags.forEach((tag) => {
      doc.querySelectorAll(tag).forEach((el) => el.remove());
    });

    // Clean attributes
    const allElements = doc.querySelectorAll("*");
    allElements.forEach((el) => {
      const attrs = Array.from(el.attributes);
      attrs.forEach((attr) => {
        const name = attr.name.toLowerCase();
        // Remove on* handlers and javascript: links
        if (name.startsWith("on") || attr.value.trim().toLowerCase().startsWith("javascript:")) {
          el.removeAttribute(attr.name);
        }
      });

      // Target="_blank" security for anchor tags
      if (el.tagName === "A") {
        el.setAttribute("rel", "noopener noreferrer");
        el.setAttribute("target", "_blank");
      }

      // Filter local image sources
      if (el.tagName === "IMG") {
        const src = el.getAttribute("src") ?? "";
        if (!/^https?:\/\//i.test(src) && !src.startsWith("data:image/")) {
          el.removeAttribute("src");
        }
      }
    });

    return doc.body.innerHTML;
  } catch {
    return html;
  }
}
