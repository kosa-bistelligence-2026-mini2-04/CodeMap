import type { Metadata } from "next";
import SeoLandingPage from "@/components/seo/SeoLandingPage";
import { getSeoPageMetadata, getSeoPageOrThrow } from "@/lib/seo-page-route";

const slug = "repository-risk-analysis";

export const metadata: Metadata = getSeoPageMetadata(slug);

export default function RepositoryRiskAnalysisPage() {
  return <SeoLandingPage page={getSeoPageOrThrow(slug)} />;
}
