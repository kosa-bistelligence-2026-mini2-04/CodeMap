"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type { OrganizationMember, OrganizationMemberList, OrgRole } from "@/types";

export function useMembers(orgId: string) {
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const fetchMembers = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    try {
      const data = await apiClient.get<OrganizationMemberList>(`/orgs/${orgId}/members`);
      setMembers(data.items);
      setTotal(data.total);
    } catch {
      toast.error("Failed to load members");
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  const changeRole = useCallback(
    async (userId: string, role: OrgRole) => {
      try {
        const updated = await apiClient.patch<OrganizationMember>(
          `/orgs/${orgId}/members/${userId}`,
          { role },
        );
        setMembers((prev) => prev.map((m) => (m.user_id === userId ? updated : m)));
        toast.success("Role updated");
      } catch {
        toast.error("Failed to update role");
      }
    },
    [orgId],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      try {
        await apiClient.delete(`/orgs/${orgId}/members/${userId}`);
        setMembers((prev) => prev.filter((m) => m.user_id !== userId));
        setTotal((t) => t - 1);
        toast.success("Member removed");
      } catch {
        toast.error("Failed to remove member");
      }
    },
    [orgId],
  );

  return { members, total, isLoading, fetchMembers, changeRole, removeMember };
}
