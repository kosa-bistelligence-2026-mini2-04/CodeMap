import { useCallback, useEffect, useState } from "react";
import type {
  JobStatusData,
  WorkspaceReport as WorkspaceReportData,
} from "@/common/types/contracts";
import type { RepoSource } from "@/features/repository/components/RepoInput";
import { fetchJobStatus, fetchParseDetails, startAnalysis, validateRepository } from "@/features/analysis/api/api";
import { mergeParseDetails } from "@/features/analysis/utils/mergeParseDetails";
import type { WorkspaceScope } from "@/features/team/components/WorkspaceSelector";

export type ViewStatus = "idle" | "loading" | "running" | "completed" | "failed";

export interface AnalysisSubmitInput {
  source: RepoSource;
  path: string;
  branch?: string;
  force_refresh?: boolean;
  model?: string;
  visibility?: WorkspaceScope;
  team_id?: string | null;
}

interface UseAnalysisJobOptions {
  preview: boolean;
  queryJobId: string | null;
  initialReport: WorkspaceReportData | null;
  isKo: boolean;
  workspaceScope: WorkspaceScope;
  selectedTeamId: string | null;
  confirm: (title: string, message: string, showCancel?: boolean) => Promise<boolean>;
  onRouteJob: (jobId: string) => void;
}

export function useAnalysisJob({
  preview,
  queryJobId,
  initialReport,
  isKo,
  workspaceScope,
  selectedTeamId,
  confirm,
  onRouteJob,
}: UseAnalysisJobOptions) {
  const [jobId, setJobId] = useState<string | null>(preview ? "preview-codemap" : queryJobId);
  const [job, setJob] = useState<JobStatusData | null>(null);
  const [report, setReport] = useState<WorkspaceReportData | null>(initialReport);
  const [status, setStatus] = useState<ViewStatus>(preview ? "completed" : queryJobId ? "loading" : "idle");
  const [error, setError] = useState<string | null>(null);
  const [showNewAnalysis, setShowNewAnalysis] = useState(!preview && !queryJobId);

  const loadJob = useCallback(async (id: string) => {
    try {
      const response = await fetchJobStatus(id);
      const nextJob = response.data;
      setJob(nextJob);
      if (nextJob.status === "COMPLETED") {
        if (nextJob.report) {
          try {
            const parseDetails = await fetchParseDetails(id);
            setReport(mergeParseDetails(nextJob.report, parseDetails));
          } catch {
            setReport(nextJob.report);
          }
        }
        setStatus("completed");
      } else if (nextJob.status === "FAILED") {
        setStatus("failed");
        setError(nextJob.statusMessage || "분석에 실패했습니다.");
      } else {
        setStatus("running");
      }
    } catch (requestError) {
      setStatus("failed");
      setError(requestError instanceof Error ? requestError.message : "분석 상태를 불러오지 못했습니다.");
    }
  }, []);

  useEffect(() => {
    if (!queryJobId || preview) return;
    queueMicrotask(() => void loadJob(queryJobId));
  }, [loadJob, preview, queryJobId]);

  useEffect(() => {
    if (!jobId || preview || status !== "running") return;
    const timer = window.setInterval(() => void loadJob(jobId), 1400);
    return () => window.clearInterval(timer);
  }, [jobId, loadJob, preview, status]);

  const submit = useCallback(async (input: AnalysisSubmitInput) => {
    setStatus("running");
    setError(null);
    setReport(null);
    setShowNewAnalysis(false);
    try {
      if (input.source === "github") {
        const valResp = await validateRepository({
          repoUrl: input.path,
          branch: input.branch,
        });

        if (valResp.data.isTruncated) {
          await confirm(
            isKo ? "분석 불가" : "Analysis Impossible",
            valResp.data.warningMessage || (isKo ? "저장소가 너무 커서 분석을 진행할 수 없습니다." : "Repository is too large to analyze."),
            false,
          );
          setStatus("idle");
          setShowNewAnalysis(true);
          return;
        }

        if (valResp.data.warningMessage) {
          const proceed = await confirm(
            isKo ? "경고" : "Warning",
            `${valResp.data.warningMessage}\n\n${isKo ? "계속해서 분석을 진행하시겠습니까?" : "Do you want to proceed with the analysis?"}`,
          );
          if (!proceed) {
            setStatus("idle");
            setShowNewAnalysis(true);
            return;
          }
        }
      }

      const visibility = input.visibility || workspaceScope;
      const response = await startAnalysis({
        repoUrl: input.path,
        branch: input.branch,
        model: input.model || "auto",
        forceRefresh: input.force_refresh || false,
        isPrivate: visibility !== "team",
        visibility,
        teamId: visibility === "team" ? input.team_id || selectedTeamId : null,
      });
      const id = response.data.jobId;
      setJobId(id);
      setJob({
        jobId: id,
        repoName: response.data.repoName,
        owner: response.data.owner,
        repoUrl: input.path,
        branch: response.data.branch,
        clonePath: "",
        status: "IN_PROGRESS",
        stage: "CLONE",
        progress: 0,
        statusMessage: "저장소 분석을 시작합니다.",
        model: response.data.model || "auto",
        report: null,
        createdAt: response.data.createdAt,
        updatedAt: response.data.createdAt,
      });
      onRouteJob(id);
    } catch (requestError) {
      setStatus("failed");
      setShowNewAnalysis(true);
      setError(requestError instanceof Error ? requestError.message : "분석 요청에 실패했습니다.");
    }
  }, [confirm, isKo, onRouteJob, selectedTeamId, workspaceScope]);

  const selectHistory = useCallback((id: string) => {
    setJobId(id);
    setReport(null);
    setError(null);
    setStatus("loading");
    setShowNewAnalysis(false);
    onRouteJob(id);
    void loadJob(id);
  }, [loadJob, onRouteJob]);

  return {
    jobId,
    job,
    report,
    status,
    error,
    showNewAnalysis,
    setShowNewAnalysis,
    submit,
    selectHistory,
  };
}
