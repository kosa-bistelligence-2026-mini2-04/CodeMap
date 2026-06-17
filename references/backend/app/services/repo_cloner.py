class RepoCloner:
    """Cloner utility to clone GitHub URLs or resolve local paths into structured workspaces."""
    
    def __init__(self, workspace_root: str = "/tmp/codemap"):
        self.workspace_root = workspace_root
        
    def clone(self, repo_url: str) -> str:
        return f"{self.workspace_root}/cloned_repo"
