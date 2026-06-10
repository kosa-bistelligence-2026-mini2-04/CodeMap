"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import type { Invitation, InvitationList, InviteMemberInput } from "@/types";

export function useInvitations(orgId: string) {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchInvitations = useCallback(async () => {
    if (!orgId) return;
    setIsLoading(true);
    try {
      const data = await apiClient.get<InvitationList>(`/orgs/${orgId}/invitations`);
      setInvitations(data.items);
    } catch {
      toast.error("Failed to load invitations");
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  const invite = useCallback(
    async (input: InviteMemberInput): Promise<Invitation | null> => {
      try {
        const inv = await apiClient.post<Invitation>(`/orgs/${orgId}/invitations`, input);
        setInvitations((prev) => [inv, ...prev]);
        toast.success(`Invitation sent to ${input.email}`);
        return inv;
      } catch {
        toast.error("Failed to send invitation");
        return null;
      }
    },
    [orgId],
  );

  const revokeInvitation = useCallback(async (token: string) => {
    try {
      await apiClient.delete(`/invitations/${token}`);
      setInvitations((prev) => prev.filter((i) => i.token !== token));
      toast.success("Invitation revoked");
    } catch {
      toast.error("Failed to revoke invitation");
    }
  }, []);

  const acceptInvitation = useCallback(async (token: string) => {
    try {
      await apiClient.post(`/invitations/${token}/accept`);
      toast.success("Joined organization!");
    } catch {
      toast.error("Failed to accept invitation");
    }
  }, []);

  return { invitations, isLoading, fetchInvitations, invite, revokeInvitation, acceptInvitation };
}
