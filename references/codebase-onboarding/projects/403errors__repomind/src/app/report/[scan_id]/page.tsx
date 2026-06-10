import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { auth } from '@/lib/auth';
import { isAdminUser } from "@/lib/admin-auth";
import { trackReportConversionEvent } from "@/lib/analytics";
import { getPreviousScan, getScanResultWithStatus } from '@/lib/services/scan-storage';
import { canAccessPrivateReport } from '@/lib/services/report-access';
import { buildReportViewData } from '@/lib/services/report-service';
import { ReportExpiredState } from '@/app/report/components/ReportExpiredState';
import { ReportContent } from './ReportContent';
import { buildOgImageUrl, buildReportSummaryDescription, createSeoMetadata, estimateSecurityHealthScore } from '@/lib/seo';

export async function generateMetadata({ params }: { params: Promise<{ scan_id: string }> }): Promise<Metadata> {
    const resolvedParams = await params;
    const scanResult = await getScanResultWithStatus(resolvedParams.scan_id);

    if (scanResult.status === "not_found") {
        return createSeoMetadata({
            title: "Report Not Found",
            description: "This security report could not be found.",
            canonical: `/report/${resolvedParams.scan_id}`,
            ogImage: buildOgImageUrl("marketing", { variant: "home" }),
            ogTitle: "Report Not Found",
            ogDescription: "This security report could not be found.",
            noIndex: true,
        });
    }
    const scan = scanResult.scan;

    const session = await auth();
    if (!canAccessPrivateReport(session, scan)) {
        const metadata = createSeoMetadata({
            title: "Private Security Report",
            description: "Sign in to view this security report.",
            canonical: `/report/${resolvedParams.scan_id}`,
            ogImage: buildOgImageUrl("marketing", { variant: "home" }),
            ogTitle: "Private Security Report",
            ogDescription: "Sign in to view this security report.",
            noIndex: true,
        });
        return metadata;
    }

    if (scanResult.status === "expired") {
        return createSeoMetadata({
            title: "Report Expired",
            description: "This scan report has expired. Run a new scan to regenerate it.",
            canonical: `/report/${resolvedParams.scan_id}`,
            ogImage: buildOgImageUrl("marketing", { variant: "home" }),
            ogTitle: "Report Expired",
            ogDescription: "This scan report has expired. Run a new scan to regenerate it.",
            noIndex: true,
        });
    }

    const { owner, repo, summary } = scan;
    const health = estimateSecurityHealthScore({
        critical: summary.critical,
        high: summary.high,
        medium: summary.medium,
        low: summary.low,
    });
    const desc = buildReportSummaryDescription({
        critical: summary.critical,
        high: summary.high,
        medium: summary.medium,
        low: summary.low,
        score: health.score,
        grade: health.grade,
    });

    return createSeoMetadata({
        title: `Security Report: ${owner}/${repo}`,
        description: desc,
        canonical: `/report/${resolvedParams.scan_id}`,
        ogImage: buildOgImageUrl("report", {
            owner,
            repo,
            critical: summary.critical,
            high: summary.high,
            medium: summary.medium,
            low: summary.low,
            health: health.score,
            grade: health.grade,
            depth: scan.depth,
        }),
        ogTitle: `Security Report: ${owner}/${repo}`,
        ogDescription: desc,
        ogType: "website",
        noIndex: true,
    });
}

export default async function PrivateReportPage({ params }: { params: Promise<{ scan_id: string }> }) {
    const resolvedParams = await params;
    const scanResult = await getScanResultWithStatus(resolvedParams.scan_id);

    if (scanResult.status === "not_found") {
        notFound();
    }
    const scan = scanResult.scan;

    const session = await auth();
    if (!canAccessPrivateReport(session, scan)) {
        notFound();
    }

    if (scanResult.status === "expired") {
        await trackReportConversionEvent("report_expired_viewed", scan.id, {
            actorUsername: session?.user?.username ?? null,
        });
        return (
            <ReportExpiredState
                owner={scan.owner}
                repo={scan.repo}
                expiresAt={scan.expiresAt}
            />
        );
    }

    const previousScan = await getPreviousScan(scan.owner, scan.repo, scan.id, scan.timestamp);
    const reportView = buildReportViewData(scan, previousScan);

    return (
        <ReportContent
            scan={scan}
            priorScanDiff={reportView.priorScanDiff}
            topFixes={reportView.topFixes}
            findingViews={reportView.findingViews}
            globalFixPrompt={reportView.globalFixPrompt}
            globalChatHref={reportView.globalChatHref}
            hasPreviousScan={Boolean(previousScan)}
            isSharedView={false}
            canShareReport={true}
            canGenerateOutreach={isAdminUser(session)}
            shareMode="canonical"
            reportExpiresAt={scan.expiresAt}
        />
    );
}
