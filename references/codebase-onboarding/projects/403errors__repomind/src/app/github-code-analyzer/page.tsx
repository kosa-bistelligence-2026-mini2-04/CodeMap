import type { Metadata } from "next";
import SeoLandingPage from "@/components/seo/SeoLandingPage";
import { getSeoPageMetadata, getSeoPageOrThrow } from "@/lib/seo-page-route";

const slug = "github-code-analyzer";

export const metadata: Metadata = getSeoPageMetadata(slug);

export default function GitHubCodeAnalyzerPage() {
  return <SeoLandingPage page={getSeoPageOrThrow(slug)} />;
}
