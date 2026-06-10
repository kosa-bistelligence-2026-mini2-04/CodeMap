"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiClient, ApiError } from "@/lib/api-client";
import type {
  ConnectorInfo,
  ConnectorList,
  SyncSourceCreate,
  SyncSourceList,
  SyncSourceRead,
} from "@/lib/rag-api";
import type {
  CreateKnowledgeBaseInput,
  KBDocument,
  KBDocumentList,
  KnowledgeBase,
  KnowledgeBaseList,
} from "@/types";

export function useKnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchKBs = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.get<KnowledgeBaseList>("/kb");
      setKbs(data.items);
    } catch {
      toast.error("Failed to load knowledge bases");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const createKB = useCallback(
    async (input: CreateKnowledgeBaseInput): Promise<KnowledgeBase | null> => {
      try {
        const kb = await apiClient.post<KnowledgeBase>("/kb", input);
        setKbs((prev) => [kb, ...prev]);
        toast.success("Knowledge base created");
        return kb;
      } catch {
        toast.error("Failed to create knowledge base");
        return null;
      }
    },
    [],
  );

  const patchKB = useCallback(
    async (id: string, patch: Partial<Pick<KnowledgeBase, "name" | "description">>) => {
      try {
        const updated = await apiClient.patch<KnowledgeBase>(`/kb/${id}`, patch);
        setKbs((prev) => prev.map((k) => (k.id === id ? updated : k)));
        toast.success("Knowledge base updated");
        return updated;
      } catch {
        toast.error("Failed to update knowledge base");
        return null;
      }
    },
    [],
  );

  const deleteKB = useCallback(async (id: string) => {
    try {
      await apiClient.delete(`/kb/${id}`);
      setKbs((prev) => prev.filter((k) => k.id !== id));
      toast.success("Knowledge base deleted");
    } catch {
      toast.error("Failed to delete knowledge base");
    }
  }, []);

  return { kbs, isLoading, fetchKBs, createKB, patchKB, deleteKB };
}

/**
 * Hook for the KB detail page: fetches one KB and its documents, exposes
 * upload/delete mutations. Refetches the document list after each mutation
 * since ingestion progresses asynchronously on the worker.
 */
export function useKBDetail(id: string | null) {
  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [syncSources, setSyncSources] = useState<SyncSourceRead[]>([]);
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const [kbData, docList, sourceList, connectorList] = await Promise.all([
        apiClient.get<KnowledgeBase>(`/kb/${id}`),
        apiClient.get<KBDocumentList>(`/kb/${id}/documents`),
        apiClient.get<SyncSourceList>(`/kb/${id}/sync-sources`).catch(() => ({
          items: [] as SyncSourceRead[],
          total: 0,
        })),
        apiClient.get<ConnectorList>(`/kb/${id}/sync-sources/connectors`).catch(() => ({
          items: [] as ConnectorInfo[],
        })),
      ]);
      setKb(kbData);
      setDocuments(docList.items);
      setSyncSources(sourceList.items);
      setConnectors(connectorList.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load knowledge base");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  const uploadDocument = useCallback(
    async (file: File) => {
      if (!id) return;
      setIsUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        // apiClient.post detects FormData and skips the JSON content-type;
        // the BFF route forwards it raw to FastAPI's UploadFile handler.
        const response = await fetch(`/api/kb/${id}/documents`, {
          method: "POST",
          body: formData,
          credentials: "include",
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new ApiError(response.status, detail.detail || "Upload failed");
        }
        toast.success(`Uploaded ${file.name}`);
        await refresh();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Upload failed";
        toast.error(msg);
        throw e;
      } finally {
        setIsUploading(false);
      }
    },
    [id, refresh],
  );

  const deleteDocument = useCallback(
    async (docId: string) => {
      if (!id) return;
      try {
        await apiClient.delete(`/kb/${id}/documents/${docId}`);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
        toast.success("Document removed");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to delete document");
      }
    },
    [id],
  );

  const createSyncSource = useCallback(
    async (data: SyncSourceCreate) => {
      if (!id) return;
      try {
        const created = await apiClient.post<SyncSourceRead>(`/kb/${id}/sync-sources`, data);
        setSyncSources((prev) => [created, ...prev]);
        toast.success("Sync source connected");
        return created;
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to create sync source");
        throw e;
      }
    },
    [id],
  );

  const triggerSyncSource = useCallback(
    async (sourceId: string) => {
      if (!id) return;
      try {
        await apiClient.post(`/kb/${id}/sync-sources/${sourceId}/trigger`);
        toast.success("Sync started — documents will appear as they ingest");
        // Refresh later to pick up new docs that the worker pulls in.
        setTimeout(() => refresh(), 2000);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to trigger sync");
      }
    },
    [id, refresh],
  );

  const deleteSyncSource = useCallback(
    async (sourceId: string) => {
      if (!id) return;
      try {
        await apiClient.delete(`/kb/${id}/sync-sources/${sourceId}`);
        setSyncSources((prev) => prev.filter((s) => s.id !== sourceId));
        toast.success("Sync source removed");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to remove sync source");
      }
    },
    [id],
  );

  return {
    kb,
    documents,
    syncSources,
    connectors,
    isLoading,
    isUploading,
    error,
    refresh,
    uploadDocument,
    deleteDocument,
    createSyncSource,
    triggerSyncSource,
    deleteSyncSource,
  };
}
