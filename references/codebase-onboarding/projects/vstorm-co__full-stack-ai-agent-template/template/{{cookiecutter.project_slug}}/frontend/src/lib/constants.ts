/**
 * Application constants.
 */

export const APP_NAME = "{{ cookiecutter.project_name }}";
export const APP_DESCRIPTION = "{{ cookiecutter.project_description }}";

// API Routes (Next.js internal routes)
export const API_ROUTES = {
  // Auth
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  LOGOUT: "/auth/logout",
  REFRESH: "/auth/refresh",
  ME: "/auth/me",

  // Health
  HEALTH: "/health",

  // Users
  USERS: "/users",

  // Chat (AI Agent)
  CHAT: "/chat",
} as const;

// Navigation routes
export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  DASHBOARD: "/dashboard",
  CHAT: "/chat",
  PROFILE: "/profile",
  SETTINGS: "/settings",
  RAG: "/rag",
  ADMIN: "/admin",
  ADMIN_USERS: "/admin/users",
  ADMIN_CONVERSATIONS: "/admin/conversations",
  ADMIN_RATINGS: "/admin/ratings",
  ORGS: "/orgs",
  ORG_MEMBERS: (id: string) => `/orgs/${id}/members`,
  ORG_SETTINGS: (id: string) => `/orgs/${id}/settings`,
  KB: "/kb",
  KB_DETAIL: (id: string) => `/kb/${id}`,
  BILLING: "/billing",
  PRICING: "/pricing",
} as const;

// WebSocket URL (for chat - direct to backend, use wss:// in production)
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:{{ cookiecutter.backend_port }}";

// Backend API URL (public, for direct links like API docs)
export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:{{ cookiecutter.backend_port }}";
