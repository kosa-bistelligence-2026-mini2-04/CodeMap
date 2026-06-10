import type { Metadata } from "next";
import SeoLandingPage from "@/components/seo/SeoLandingPage";
import { getSeoPageMetadata, getSeoPageOrThrow } from "@/lib/seo-page-route";

const slug = "repomind-vs-snyk";

export const metadata: Metadata = getSeoPageMetadata(slug);

export default function RepoMindVsSnykPage() {
  return <SeoLandingPage page={getSeoPageOrThrow(slug)} />;
}
