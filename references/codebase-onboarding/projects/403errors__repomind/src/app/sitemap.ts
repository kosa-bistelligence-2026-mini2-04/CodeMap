import { MetadataRoute } from "next";
import { getCanonicalSiteUrl } from "@/lib/site-url";
import { getPublishedPosts } from "@/lib/services/blog-service";
import { getCuratedRepos, getIndexableTopics } from "@/lib/repo-catalog";
import fs from "node:fs";
import path from "node:path";

export const dynamic = 'force-static';

/**
 * Helper to get the last modification date of a file.
 * Falls back to the current date if the file cannot be read.
 */
function getFileModDate(relativePath: string): Date {
    try {
        const fullPath = path.join(process.cwd(), relativePath);
        const stats = fs.statSync(fullPath);
        return stats.mtime;
    } catch {
        return new Date();
    }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
    const baseUrl = getCanonicalSiteUrl();
    const blogPosts = await getPublishedPosts();
    
    // Catalog data is the source of truth for repo/topic routes
    const catalogModDate = getFileModDate("public/data/top-repos.json");

    const defaultRoutes: MetadataRoute.Sitemap = [
        {
            url: baseUrl,
            lastModified: getFileModDate("src/app/page.tsx"),
            changeFrequency: "daily",
            priority: 1,
        },
        {
            url: `${baseUrl}/blog`,
            lastModified: getFileModDate("src/app/blog/page.tsx"),
            changeFrequency: "daily",
            priority: 0.9,
        },
        {
            url: `${baseUrl}/solutions`,
            lastModified: getFileModDate("src/app/solutions/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.85,
        },
        {
            url: `${baseUrl}/compare`,
            lastModified: getFileModDate("src/app/compare/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/explore`,
            lastModified: getFileModDate("src/app/explore/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.75,
        },
        {
            url: `${baseUrl}/trending`,
            lastModified: catalogModDate,
            changeFrequency: "weekly",
            priority: 0.9,
        },
        {
            url: `${baseUrl}/about`,
            lastModified: getFileModDate("src/app/about/page.tsx"),
            changeFrequency: "monthly",
            priority: 0.5,
        },
        {
            url: `${baseUrl}/faq`,
            lastModified: getFileModDate("src/app/faq/page.tsx"),
            changeFrequency: "monthly",
            priority: 0.7,
        },
        {
            url: `${baseUrl}/privacy`,
            lastModified: getFileModDate("src/app/privacy/page.tsx"),
            changeFrequency: "yearly",
            priority: 0.3,
        },
        {
            url: `${baseUrl}/terms`,
            lastModified: getFileModDate("src/app/terms/page.tsx"),
            changeFrequency: "yearly",
            priority: 0.3,
        },
        {
            url: `${baseUrl}/security-scanner`,
            lastModified: getFileModDate("src/app/security-scanner/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.85,
        },
        {
            url: `${baseUrl}/github-repository-analysis`,
            lastModified: getFileModDate("src/app/github-repository-analysis/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.85,
        },
        {
            url: `${baseUrl}/ai-code-review-tool`,
            lastModified: getFileModDate("src/app/ai-code-review-tool/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.85,
        },
        {
            url: `${baseUrl}/github-code-analyzer`,
            lastModified: getFileModDate("src/app/github-code-analyzer/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/typescript-code-analyzer`,
            lastModified: getFileModDate("src/app/typescript-code-analyzer/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/nodejs-security-scanner`,
            lastModified: getFileModDate("src/app/nodejs-security-scanner/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/open-source-security-scanner`,
            lastModified: getFileModDate("src/app/open-source-security-scanner/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/repository-risk-analysis`,
            lastModified: getFileModDate("src/app/repository-risk-analysis/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.8,
        },
        {
            url: `${baseUrl}/static-analysis-vs-repomind`,
            lastModified: getFileModDate("src/app/static-analysis-vs-repomind/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.75,
        },
        {
            url: `${baseUrl}/repomind-vs-sonarqube`,
            lastModified: getFileModDate("src/app/repomind-vs-sonarqube/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.75,
        },
        {
            url: `${baseUrl}/repomind-vs-snyk`,
            lastModified: getFileModDate("src/app/repomind-vs-snyk/page.tsx"),
            changeFrequency: "weekly",
            priority: 0.75,
        },
        ...blogPosts.map((post) => ({
            url: `${baseUrl}/blog/${post.slug}`,
            lastModified: post.updatedAt,
            changeFrequency: "monthly" as const,
            priority: 0.7,
        })),
    ];

    let repoRoutes: MetadataRoute.Sitemap = [];
    let topicRoutes: MetadataRoute.Sitemap = [];

    try {
        const [curatedRepos, indexableTopics] = await Promise.all([
            getCuratedRepos(),
            getIndexableTopics(),
        ]);

        repoRoutes = curatedRepos.map((repo) => ({
            url: `${baseUrl}/repo/${repo.owner}/${repo.repo}`,
            lastModified: catalogModDate,
            changeFrequency: "weekly",
            priority: 0.8,
        }));

        topicRoutes = indexableTopics.map((topic) => ({
            url: `${baseUrl}/topics/${encodeURIComponent(topic)}`,
            lastModified: catalogModDate,
            changeFrequency: "weekly",
            priority: 0.7,
        }));
    } catch (e) {
        console.error("Failed to generate sitemap routes from repo catalog", e);
    }

    return [...defaultRoutes, ...repoRoutes, ...topicRoutes];
}
