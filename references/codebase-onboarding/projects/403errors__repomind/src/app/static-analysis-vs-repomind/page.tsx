import type { Metadata } from "next";
import SeoLandingPage from "@/components/seo/SeoLandingPage";
import { getSeoPageMetadata, getSeoPageOrThrow } from "@/lib/seo-page-route";

const slug = "static-analysis-vs-repomind";

export const metadata: Metadata = getSeoPageMetadata(slug);

export default function StaticAnalysisVsRepoMindPage() {
  return <SeoLandingPage page={getSeoPageOrThrow(slug)} />;
}
