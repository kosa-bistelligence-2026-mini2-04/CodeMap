"use client";

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Camera, Loader2, MailPlus, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";

import { InviteMemberDialog, MembersTable } from "@/components/teams";
import { EmptyState, LoadingState } from "@/components/states";
import { useAuth, useInvitations, useMembers, useOrganizations } from "@/hooks";
import { cn } from "@/lib/utils";
import type { OrgRole } from "@/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

const ROLE_TONE: Record<string, string> = {
  owner: "bg-brand/15 text-foreground",
  admin: "border-foreground/15 text-foreground/70 border",
  member: "border-foreground/10 text-foreground/55 border",
  viewer: "border-foreground/10 text-foreground/55 border",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function OrgMembersPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const { members, total, isLoading, fetchMembers, changeRole, removeMember } = useMembers(id);
  const { invitations, fetchInvitations, revokeInvitation } = useInvitations(id);
  const { orgs, fetchOrgs, patchOrg } = useOrganizations();
  const [inviteOpen, setInviteOpen] = useState(false);

  useEffect(() => {
    fetchMembers();
    fetchInvitations();
    fetchOrgs();
  }, [fetchMembers, fetchInvitations, fetchOrgs]);

  const org = orgs.find((o) => o.id === id);
  const currentMember = members.find((m) => m.user_id === user?.id);
  const canManage = currentMember?.role === "owner" || currentMember?.role === "admin";
  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  // Workspace profile state — name edits stay local until "Save" lands the
  // PATCH; avatar uploads are immediate (a separate POST endpoint).
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const avatarInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (org) setName(org.name);
  }, [org?.id, org?.name]);

  const handleSaveName = async () => {
    if (!org) return;
    const trimmed = name.trim();
    if (!trimmed || trimmed === org.name) return;
    setSavingName(true);
    try {
      await patchOrg(org.id, { name: trimmed });
    } finally {
      setSavingName(false);
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Avatar too large. Maximum 2MB.");
      return;
    }
    setAvatarUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`/api/orgs/${id}/avatar`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      toast.success("Workspace avatar updated");
      await fetchOrgs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to upload avatar");
    } finally {
      setAvatarUploading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <div className="space-y-1">
        <button
          type="button"
          onClick={() => router.push("/orgs")}
          className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 text-xs font-medium transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to organizations
        </button>
      </div>

      {/* Workspace profile — avatar + name editing for admins/owners */}
      {org && (
        <section className="border-foreground/10 bg-card flex flex-wrap items-start gap-5 rounded-2xl border p-5 sm:p-6">
          <button
            type="button"
            onClick={() => avatarInputRef.current?.click()}
            disabled={!canManage || avatarUploading}
            className="bg-foreground/8 group relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full disabled:cursor-default"
            title={canManage ? "Change workspace avatar" : "Only owners and admins can edit"}
          >
            {org.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`/api/orgs/${org.id}/avatar?v=${org.updated_at ?? ""}`}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <span className="text-foreground font-mono text-lg font-semibold">
                {org.name.slice(0, 2).toUpperCase()}
              </span>
            )}
            {canManage && (
              <span className="absolute inset-0 flex items-center justify-center bg-black/45 opacity-0 transition-opacity group-hover:opacity-100">
                {avatarUploading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-white" />
                ) : (
                  <Camera className="h-5 w-5 text-white" />
                )}
              </span>
            )}
          </button>
          <input
            ref={avatarInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleAvatarUpload}
          />

          <div className="min-w-0 flex-1 space-y-3">
            <div>
              <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Workspace profile
              </p>
              <p className="text-foreground/55 mt-0.5 text-xs">
                Name and avatar shown across the app to everyone in this workspace.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={!canManage || savingName}
                className="border-foreground/15 focus:border-foreground/40 bg-background text-foreground min-w-0 flex-1 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors outline-none disabled:opacity-60"
                placeholder="Workspace name"
                maxLength={255}
              />
              {canManage && name.trim() !== org.name && name.trim() !== "" && (
                <button
                  type="button"
                  onClick={handleSaveName}
                  disabled={savingName}
                  className="bg-foreground text-background hover:bg-foreground/90 inline-flex shrink-0 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-60"
                >
                  {savingName ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Save"}
                </button>
              )}
            </div>
            {!canManage && (
              <p className="text-foreground/45 text-[11px]">
                Only owners and admins can edit workspace profile.
              </p>
            )}
          </div>
        </section>
      )}

      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Members
          </p>
          <h1 className="font-display text-foreground text-2xl font-bold tracking-tight sm:text-3xl">
            People in this workspace
          </h1>
          <p className="text-foreground/65 max-w-xl text-sm">
            {total} {total === 1 ? "person has" : "people have"} access. Owners and admins can
            invite teammates and adjust roles.
          </p>
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setInviteOpen(true)}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            Invite teammate
          </button>
        )}
      </header>

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : members.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No members yet"
          description="Invite teammates by email to give them access to this workspace."
          cta={
            canManage ? { label: "Invite teammate", onClick: () => setInviteOpen(true) } : undefined
          }
        />
      ) : (
        <div className="border-border bg-card overflow-hidden rounded-2xl border">
          <MembersTable
            members={members}
            currentUserId={user?.id ?? ""}
            canManage={canManage}
            onRoleChange={(userId, role: OrgRole) => changeRole(userId, role)}
            onRemove={removeMember}
          />
        </div>
      )}

      {pendingInvitations.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-end justify-between gap-2">
            <div>
              <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Pending invitations
              </p>
              <h2 className="font-display text-foreground text-xl font-semibold tracking-tight">
                {pendingInvitations.length} waiting on a response
              </h2>
            </div>
          </div>
          <ul className="space-y-2">
            {pendingInvitations.map((inv) => (
              <li
                key={inv.id}
                className="border-border bg-card flex flex-wrap items-center gap-3 rounded-2xl border p-4 sm:p-5"
              >
                <div className="bg-brand/15 text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
                  <MailPlus className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-semibold">{inv.email}</p>
                  <p className="text-foreground/55 mt-0.5 text-xs">
                    Invited {formatDate(inv.created_at)}
                    {inv.expires_at && <> · expires {formatDate(inv.expires_at)}</>}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase",
                    ROLE_TONE[inv.role] ?? ROLE_TONE.member,
                  )}
                >
                  {inv.role}
                </span>
                {canManage && (
                  <button
                    type="button"
                    onClick={() => revokeInvitation(inv.token)}
                    className="text-foreground/55 hover:text-destructive text-xs font-medium transition-colors"
                  >
                    Revoke
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} orgId={id} />
    </div>
  );
}
