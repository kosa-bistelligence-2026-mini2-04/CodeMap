"""GitHub repository loader for CodeBase RAG."""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError

from ..utils import config, logger


@dataclass
class FileContent:
    """Represents a file from the repository."""
    
    path: str  # Relative path within repo
    content: str  # File content
    extension: str  # File extension
    language: str  # Programming language
    size: int  # File size in bytes
    
    # Metadata
    metadata: Dict = field(default_factory=dict)


class GitHubLoader:
    """Load and parse files from GitHub repositories."""
    
    # Language mapping by extension
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".md": "markdown",
        ".txt": "text",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
    }
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize the GitHub loader.
        
        Args:
            base_dir: Base directory to store cloned repos
        """
        self.base_dir = Path(base_dir or "./data/repos")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.supported_extensions = set(config.supported_extensions)
        self.ignore_patterns = config.ignore_patterns
    
    def clone_repo(
        self,
        repo_url: str,
        branch: Optional[str] = None,
        force: bool = False
    ) -> List[FileContent]:
        """Clone a GitHub repository and extract files.
        
        Args:
            repo_url: GitHub repository URL
            branch: Specific branch to clone (default: main/master)
            force: Force re-clone even if exists
            
        Returns:
            List of FileContent objects
        """
        # Parse repo URL
        repo_name = self._parse_repo_name(repo_url)
        repo_path = self.base_dir / repo_name
        
        logger.info(f"📦 Processing repository: {repo_name}")
        
        # Clone or update
        if repo_path.exists():
            if force:
                logger.info("🗑️ Removing existing repo (force=True)")
                shutil.rmtree(repo_path)
                self._clone(repo_url, repo_path, branch)
            else:
                logger.info("📂 Repository already exists, using cached version")
        else:
            self._clone(repo_url, repo_path, branch)
        
        # Extract files
        files = self._extract_files(repo_path, repo_name)
        logger.info(f"✅ Extracted {len(files)} files from {repo_name}")
        
        return files
    
    def load_local_directory(self, directory: str) -> List[FileContent]:
        """Load files from a local directory.
        
        Args:
            directory: Path to local directory
            
        Returns:
            List of FileContent objects
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"Directory not found: {directory}")
        
        repo_name = dir_path.name
        logger.info(f"📂 Loading local directory: {repo_name}")
        
        files = self._extract_files(dir_path, repo_name)
        logger.info(f"✅ Extracted {len(files)} files")
        
        return files
    
    def _parse_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        # Handle different URL formats
        # https://github.com/owner/repo
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        
        if repo_url.startswith("git@"):
            # SSH format
            path = repo_url.split(":")[-1]
        else:
            # HTTPS format
            parsed = urlparse(repo_url)
            path = parsed.path
        
        # Remove .git suffix and leading slash
        path = path.strip("/").removesuffix(".git")
        
        # Return owner_repo format
        return path.replace("/", "_")
    
    def _clone(
        self,
        repo_url: str,
        repo_path: Path,
        branch: Optional[str] = None
    ) -> None:
        """Clone repository from GitHub."""
        logger.info(f"🔄 Cloning {repo_url}...")
        
        try:
            clone_args = {"depth": 1}  # Shallow clone for speed
            if branch:
                clone_args["branch"] = branch
            
            Repo.clone_from(repo_url, repo_path, **clone_args)
            logger.info("✅ Clone successful")
            
        except GitCommandError as e:
            logger.error(f"❌ Failed to clone: {e}")
            raise
    
    def _extract_files(self, repo_path: Path, repo_name: str) -> List[FileContent]:
        """Extract all supported files from repository."""
        files = []
        
        for file_path in repo_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Check ignore patterns
            if self._should_ignore(file_path, repo_path):
                continue
            
            # Check extension
            ext = file_path.suffix.lower()
            if ext not in self.supported_extensions:
                continue
            
            # Read file content
            try:
                content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError) as e:
                logger.warning(f"⚠️ Skipping {file_path}: {e}")
                continue
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Create FileContent object
            relative_path = str(file_path.relative_to(repo_path))
            
            file_content = FileContent(
                path=relative_path,
                content=content,
                extension=ext,
                language=self.LANGUAGE_MAP.get(ext, "unknown"),
                size=len(content),
                metadata={
                    "repo_name": repo_name,
                    "full_path": str(file_path),
                    "line_count": content.count("\n") + 1,
                }
            )
            
            files.append(file_content)
        
        return files
    
    def _should_ignore(self, file_path: Path, repo_path: Path) -> bool:
        """Check if file should be ignored."""
        relative = file_path.relative_to(repo_path)
        path_str = str(relative)
        
        for pattern in self.ignore_patterns:
            # Check if any part of the path matches
            if pattern in path_str:
                return True
            
            # Check glob patterns
            if "*" in pattern:
                if file_path.match(pattern):
                    return True
        
        return False
