import { getAnalysis, getLatestAnalysis, startAnalysis } from '@/services/http/analysis'
import type { StartAnalysisRequest } from '@repo/shared'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export function useStartAnalysis(repoId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body?: StartAnalysisRequest) => startAnalysis(repoId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos', repoId, 'analyses'] })
      queryClient.invalidateQueries({ queryKey: ['repos'] })
    },
  })
}

export function useLatestAnalysis(repoId: string) {
  return useQuery({
    queryKey: ['latest-analysis', repoId],
    queryFn: () => getLatestAnalysis(repoId),
    staleTime: 1000 * 60 * 5,
  })
}

export function useAnalysis(analysisId: string | null) {
  return useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => getAnalysis(analysisId ?? ''),
    enabled: !!analysisId,
    staleTime: 0,
  })
}
