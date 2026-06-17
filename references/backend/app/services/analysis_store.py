class AnalysisStore:
    """Storage system to persist analysis metadata and generated Markdown reports on disks."""
    
    def __init__(self, storage_dir: str = "./data"):
        self.storage_dir = storage_dir
        
    def save(self, job_id: str, report: dict) -> None:
        pass
        
    def load(self, job_id: str) -> dict | None:
        return None
