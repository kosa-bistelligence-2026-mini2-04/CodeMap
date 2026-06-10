"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Organization } from "@/types";

interface OrgState {
  activeOrgId: string | null;
  orgs: Organization[];
  setActiveOrgId: (id: string | null) => void;
  setOrgs: (orgs: Organization[]) => void;
  addOrg: (org: Organization) => void;
  updateOrg: (id: string, patch: Partial<Organization>) => void;
  removeOrg: (id: string) => void;
  activeOrg: () => Organization | null;
}

export const useOrgStore = create<OrgState>()(
  persist(
    (set, get) => ({
      activeOrgId: null,
      orgs: [],

      setActiveOrgId: (id) => set({ activeOrgId: id }),

      setOrgs: (orgs) => set({ orgs }),

      addOrg: (org) => set((s) => ({ orgs: [...s.orgs, org] })),

      updateOrg: (id, patch) =>
        set((s) => ({
          orgs: s.orgs.map((o) => (o.id === id ? { ...o, ...patch } : o)),
        })),

      removeOrg: (id) =>
        set((s) => ({
          orgs: s.orgs.filter((o) => o.id !== id),
          activeOrgId: s.activeOrgId === id ? null : s.activeOrgId,
        })),

      activeOrg: () => {
        const { activeOrgId, orgs } = get();
        return orgs.find((o) => o.id === activeOrgId) ?? null;
      },
    }),
    {
      name: "org-storage",
      partialize: (state) => ({
        activeOrgId: state.activeOrgId,
      }),
    },
  ),
);
