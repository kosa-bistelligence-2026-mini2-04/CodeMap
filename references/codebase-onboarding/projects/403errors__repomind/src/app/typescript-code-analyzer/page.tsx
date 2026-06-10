import type { Metadata } from "next";
import SeoLandingPage from "@/components/seo/SeoLandingPage";
import { getSeoPageMetadata, getSeoPageOrThrow } from "@/lib/seo-page-route";

const slug = "typescript-code-analyzer";

export const metadata: Metadata = getSeoPageMetadata(slug);

export default function TypeScriptCodeAnalyzerPage() {
  return <SeoLandingPage page={getSeoPageOrThrow(slug)} />;
}
