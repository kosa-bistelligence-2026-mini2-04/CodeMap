{% raw %}"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRightLeft, Building2, Camera, Plus, Settings } from "lucide-react";
import { toast } from "sonner";

import { CreateOrgDialog } from "@/components/teams";
import { PageHero } from "@/components/dashboard/page-hero";
import { EmptyState, LoadingState } from "@/components/states";
import { useOrganizations } from "@/hooks";
import { cn } from "@/lib/utils";

export default function OrgsPage() {
  const { orgs, activeOrgId, fetchOrgs, switchOrg } = useOrganizations();
  const [createOpen, setCreateOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingOrgIdRef = useRef<string | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleAvatarUpload = async (orgId: string, file: File) => {
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Avatar too large. Maximum 2MB.");
      return;
    }
    setUploadingFor(orgId);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`/api/orgs/${orgId}/avatar`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
      }
      toast.success("Organization avatar updated");
      await fetchOrgs();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to upload avatar");
    } finally {
      setUploadingFor(null);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await fetchOrgs();
      if (!cancelled) setIsLoading(false);
    })();
    if (searchParams.get("create") === "1") setCreateOpen(true);
    return () => {
      cancelled = true;
    };
  }, [fetchOrgs, searchParams]);

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <PageHero
        eyebrow="Organizations"
        title={
          <>
            Workspaces and <em>teams.</em>
          </>
        }
        description="Switch between workspaces, manage members, and spin up new organizations to collaborate with your team."
        stats={
          orgs.length > 0
            ? [{ value: orgs.length, label: orgs.length === 1 ? "workspace" : "workspaces" }]
            : undefined
        }
        cta={{ label: "New organization", onClick: () => setCreateOpen(true), icon: Plus }}
      />

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : orgs.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No organizations yet"
          description="Create your first workspace to invite teammates and share access to conversations and knowledge bases."
          cta={{ label: "Create organization", onClick: () => setCreateOpen(true) }}
        />
      ) : (
        <ul className="space-y-3">
          {orgs.map((org) => {
            const isActive = org.id === activeOrgId;
            return (
              <li
                key={org.id}
                className={cn(
                  "relative flex flex-wrap items-center gap-4 rounded-2xl border p-4 transition-all sm:p-5",
                  isActive
                    ? "border-brand/40 bg-brand/[0.06]"
                    : "border-border bg-card hover:border-foreground/25 hover:-translate-y-0.5",
                )}
              >
                {isActive && (
                  <span
                    aria-hidden
                    className="bg-brand absolute top-1/2 left-0 h-8 w-0.5 -translate-y-1/2 rounded-r-full"
                    style={{ boxShadow: "0 0 8px var(--color-brand)" }}
                  />
                )}
                <button
                  type="button"
                  className="group bg-brand/15 text-foreground relative flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full"
                  onClick={() => {
                    pendingOrgIdRef.current = org.id;
                    fileInputRef.current?.click();
                  }}
                  disabled={uploadingFor !== null}
                  title="Change organization avatar"
                >
                  {org.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={`/api/orgs/${org.id}/avatar?v=${org.updated_at ?? ""}`}
                      alt={org.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <Building2 className="h-5 w-5" />
                  )}
                  <span className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
                    <Camera className="h-4 w-4 text-white" />
                  </span>
                </button>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-foreground truncate text-base font-semibold">{org.name}</h2>
                    {org.is_personal && (
                      <span className="border-foreground/15 text-foreground/65 rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                        Personal
                      </span>
                    )}
                    {isActive && (
                      <span className="bg-brand/15 text-foreground rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-foreground/55 mt-0.5 truncate text-xs">
                    <span className="capitalize">{org.subscription_tier}</span>
                    {org.slug && <> · {org.slug}</>}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    disabled={isActive}
                    onClick={() => {
                      switchOrg(org.id);
                      router.push("/dashboard");
                    }}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                      isActive
                        ? "text-foreground/40 cursor-not-allowed"
                        : "border-foreground/15 hover:border-foreground/40 text-foreground border",
                    )}
                  >
                    <ArrowRightLeft className="h-3.5 w-3.5" />
                    {isActive ? "Current" : "Switch"}
                  </button>
                  <button
                    type="button"
                    onClick={() => router.push(`/orgs/${org.id}/members`)}
                    className="border-foreground/15 hover:border-foreground/40 text-foreground inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                  >
                    <Settings className="h-3.5 w-3.5" />
                    Manage
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          const orgId = pendingOrgIdRef.current;
          e.target.value = "";
          if (file && orgId) handleAvatarUpload(orgId, file);
          pendingOrgIdRef.current = null;
        }}
      />
      <CreateOrgDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => fetchOrgs()}
      />
    </div>
  );
}
{% endraw %}
