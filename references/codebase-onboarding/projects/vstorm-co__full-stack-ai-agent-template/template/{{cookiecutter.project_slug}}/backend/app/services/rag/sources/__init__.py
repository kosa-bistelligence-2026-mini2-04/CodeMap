{%- if cookiecutter.enable_rag %}
"""RAG document source connectors.

Provides integrations for fetching documents from external sources
(Google Drive, S3) for ingestion into the RAG pipeline.
"""
{%- if cookiecutter.enable_google_drive_ingestion %}
from app.services.rag.sources.google_drive import GoogleDriveSource
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
from app.services.rag.sources.s3 import S3Source
{%- endif %}

__all__ = [
{%- if cookiecutter.enable_google_drive_ingestion %}
    "GoogleDriveSource",
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
    "S3Source",
{%- endif %}
]
{%- endif %}
