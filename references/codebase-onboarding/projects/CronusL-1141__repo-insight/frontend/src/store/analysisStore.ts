import { create } from 'zustand';
import type {
  AgentName,
  AgentRuntimeStatus,
  ReportJsonResponse,
  WsConflictDetectedEvent,
  WsDegradedEvent,
} from '@/types/contracts';

type JobStatus = 'idle' | 'queued' | 'running' | 'completed' | 'failed';

const AGENT_ORDER: AgentName[] = [
  'static_analyzer',
  'behavior_inferer',
  'community_assessor',
  'reporter',
];

function makeInitialAgents(): Record<AgentName, AgentRuntimeStatus> {
  return AGENT_ORDER.reduce(
    (acc, name) => {
      acc[name] = { name, status: 'pending', progress: 0 };
      return acc;
    },
    {} as Record<AgentName, AgentRuntimeStatus>,
  );
}

interface AnalysisState {
  jobId: string | null;
  status: JobStatus;
  agents: Record<AgentName, AgentRuntimeStatus>;
  report: ReportJsonResponse | null;
  htmlReport: string | null;
  conflictModules: string[];
  conflictEvents: WsConflictDetectedEvent[];
  degraded: WsDegradedEvent[];
  error: string | null;

  startJob: (jobId: string) => void;
  upsertAgent: (status: AgentRuntimeStatus) => void;
  recordConflict: (event: WsConflictDetectedEvent) => void;
  recordDegraded: (event: WsDegradedEvent) => void;
  setReport: (report: ReportJsonResponse) => void;
  setHtmlReport: (html: string) => void;
  markCompleted: () => void;
  markFailed: (error: string) => void;
  reset: () => void;
}

export const AGENT_NAMES = AGENT_ORDER;

export const useAnalysisStore = create<AnalysisState>((set) => ({
  jobId: null,
  status: 'idle',
  agents: makeInitialAgents(),
  report: null,
  htmlReport: null,
  conflictModules: [],
  conflictEvents: [],
  degraded: [],
  error: null,

  startJob: (jobId) =>
    set({
      jobId,
      status: 'queued',
      agents: makeInitialAgents(),
      report: null,
      htmlReport: null,
      conflictModules: [],
      conflictEvents: [],
      degraded: [],
      error: null,
    }),

  upsertAgent: (status) =>
    set((state) => ({
      status: state.status === 'queued' ? 'running' : state.status,
      agents: {
        ...state.agents,
        [status.name]: { ...state.agents[status.name], ...status },
      },
    })),

  recordConflict: (event) =>
    set((state) => ({
      conflictEvents: [...state.conflictEvents, event],
      conflictModules: Array.from(
        new Set([...state.conflictModules, ...event.modules]),
      ),
    })),

  recordDegraded: (event) =>
    set((state) => ({
      degraded: [...state.degraded, event],
      agents: {
        ...state.agents,
        [event.agent]: {
          ...state.agents[event.agent],
          status: 'degraded',
          message: event.reason,
        },
      },
    })),

  setReport: (report) => set({ report }),
  setHtmlReport: (html) => set({ htmlReport: html }),
  markCompleted: () => set({ status: 'completed' }),
  markFailed: (error) => set({ status: 'failed', error }),

  reset: () =>
    set({
      jobId: null,
      status: 'idle',
      agents: makeInitialAgents(),
      report: null,
      htmlReport: null,
      conflictModules: [],
      conflictEvents: [],
      degraded: [],
      error: null,
    }),
}));
