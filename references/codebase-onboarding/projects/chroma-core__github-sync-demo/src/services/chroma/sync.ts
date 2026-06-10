import { env } from "@/lib/env";
import { trace } from "@opentelemetry/api";
import {
  type CreateSourceResponse,
  type CreateInvocationResponse,
  type InvocationStatus,
  type InvocationStatusResponse,
  type NormalizedInvocationStatus,
} from "@/types/chroma";

const tracer = trace.getTracer("chroma");

const SYNC_API_BASE = "https://sync.trychroma.com/api/v1";

const EMBEDDING_CONFIG = {
  dense: {
    model: "Qwen/Qwen3-Embedding-0.6B",
    task: null,
  },
  sparse: null,
} as const;

function normalizeStatus(
  status: InvocationStatusResponse["status"],
): InvocationStatus {
  if (typeof status === "string") {
    return status as InvocationStatus;
  }
  if ("complete" in status) {
    return "completed";
  }
  if ("failed" in status) {
    return "failed";
  }
  return "pending";
}

export async function createSource(
  owner: string,
  repo: string,
): Promise<CreateSourceResponse> {
  const span = tracer.startSpan("chroma.createSource");

  try {
    const response = await fetch(`${SYNC_API_BASE}/sources`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "Content-Type": "application/json",
        "x-chroma-token": env.CHROMA_API_KEY,
      },
      body: JSON.stringify({
        github: {
          include_globs: ["**/*"],
          repository: `${owner}/${repo}`,
        },
        database_name: env.CHROMA_DATABASE,
        embedding: EMBEDDING_CONFIG,
        embedding_model: null,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      span.recordException(
        new Error(`Failed to create Chroma source: ${errorText}`),
      );
      throw new Error(`Failed to create Chroma source: ${errorText}`);
    }

    const data: CreateSourceResponse = await response.json();
    return data;
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}

export async function createInvocation(
  sourceId: string,
  commitSha: string,
  collectionName: string,
): Promise<CreateInvocationResponse> {
  const span = tracer.startSpan("chroma.createInvocation");

  try {
    const response = await fetch(
      `${SYNC_API_BASE}/sources/${sourceId}/invocations`,
      {
        method: "POST",
        headers: {
          accept: "application/json",
          "Content-Type": "application/json",
          "x-chroma-token": env.CHROMA_API_KEY,
        },
        body: JSON.stringify({
          ref_identifier: {
            sha: commitSha,
          },
          target_collection_name: collectionName,
        }),
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      span.recordException(
        new Error(`Failed to create Chroma invocation: ${errorText}`),
      );
      throw new Error(`Failed to create Chroma invocation: ${errorText}`);
    }

    const data: CreateInvocationResponse = await response.json();
    span.setAttribute("invocation.id", data.invocation_id);
    return data;
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}

export async function getInvocationStatus(
  invocationId: string,
): Promise<NormalizedInvocationStatus> {
  const span = tracer.startSpan("chroma.getInvocationStatus");

  try {
    const response = await fetch(
      `${SYNC_API_BASE}/invocations/${invocationId}`,
      {
        method: "GET",
        headers: {
          accept: "application/json",
          "Content-Type": "application/json",
          "x-chroma-token": env.CHROMA_API_KEY,
        },
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      span.recordException(
        new Error(`Failed to fetch invocation status: ${errorText}`),
      );
      throw new Error(`Failed to fetch invocation status: ${errorText}`);
    }

    const data: InvocationStatusResponse = await response.json();
    const normalizedStatus = normalizeStatus(data.status);

    span.setAttribute("invocation.status", normalizedStatus);

    return {
      id: data.id,
      status: normalizedStatus,
      created_at: data.created_at,
      metadata: data.metadata,
    };
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}
