{%- if cookiecutter.enable_brand_from_config %}
"use client";

import { useEffect } from "react";

// Map colour name → OKLCH hue value (mirrors CLI --brand-color choices).
const HUE_MAP: Record<string, string> = {
  blue: "250",
  green: "155",
  red: "25",
  violet: "295",
  orange: "55",
};

/**
 * Reads NEXT_PUBLIC_BRAND_COLOR (e.g. "blue") and NEXT_PUBLIC_BRAND_LOGO_URL
 * from the environment and applies them as CSS variable overrides on <html>.
 * This allows white-label deployments to set the brand at runtime without
 * rebuilding the frontend.
 */
export function BrandOverride() {
  useEffect(() => {
    const color = process.env.NEXT_PUBLIC_BRAND_COLOR ?? "";
    const logoUrl = process.env.NEXT_PUBLIC_BRAND_LOGO_URL ?? "";
    const hue = HUE_MAP[color.toLowerCase()] ?? "";

    if (hue) {
      document.documentElement.style.setProperty("--brand-h", hue);
    }
    if (logoUrl) {
      document.documentElement.style.setProperty("--brand-logo-url", `url(${logoUrl})`);
    }
  }, []);

  return null;
}
{%- else %}
export {};
{%- endif %}
