import { fetchGithubRepos } from '@/services/http/github'
import { fetchRepo, fetchRepoAnalyses, fetchRepos, upsertRepo } from '@/services/http/repos'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export function useRepositories() {
  return useQuery({ queryKey: ['repos'], queryFn: fetchRepos })
}

export function useGithubRepos(enabled = true) {
  return useQuery({ queryKey: ['github-repos'], queryFn: fetchGithubRepos, enabled })
}

export function useRepository(id: string) {
  return useQuery({ queryKey: ['repos', id], queryFn: () => fetchRepo(id), enabled: !!id })
}

export function useRepoAnalyses(id: string) {
  return useQuery({
    queryKey: ['repos', id, 'analyses'],
    queryFn: () => fetchRepoAnalyses(id),
    enabled: !!id,
  })
}

export function useAddRepository() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: upsertRepo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['repos'] }),
  })
}
