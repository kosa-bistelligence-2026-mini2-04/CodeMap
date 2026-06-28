"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Users, Mail } from "lucide-react";
import type { TeamWorkspace, TeamInviteItem, TeamMemberResponse } from "@/common/types/contracts";
import {
  acceptInvite,
  createTeam,
  declineInvite,
  fetchMyInvites,
  fetchTeams,
  inviteTeamMember,
  fetchTeamMembers,
  removeTeamMember,
  leaveTeam,
  fetchTeamInvites,
  cancelTeamInvite,
} from "@/features/analysis/api/api";

export type WorkspaceScope = "private" | "team";

interface WorkspaceSelectorProps {
  scope: WorkspaceScope;
  selectedTeamId: string | null;
  isDark: boolean;
  isKo: boolean;
  onSelectionChange: (selection: {
    scope: WorkspaceScope;
    teamId: string | null;
    teamName: string | null;
  }) => void;
}

function getTeamId(team: TeamWorkspace): string {
  return team.teamId || team.id;
}

export function WorkspaceSelector({
  scope,
  selectedTeamId,
  isDark,
  isKo,
  onSelectionChange,
}: WorkspaceSelectorProps) {
  const [teams, setTeams] = useState<TeamWorkspace[]>([]);
  const [invites, setInvites] = useState<TeamInviteItem[]>([]);

  const [members, setMembers] = useState<TeamMemberResponse[]>([]);
  const [sentInvites, setSentInvites] = useState<TeamInviteItem[]>([]);
  const [newTeamName, setNewTeamName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // onSelectionChange는 부모 렌더마다 새 함수일 수 있으므로 ref로 고정해
  // loadTeams가 매 렌더 재생성되어 refetch 루프가 도는 것을 막는다. (자체 PR 리뷰 N3)
  const onSelectionChangeRef = useRef(onSelectionChange);
  useEffect(() => {
    onSelectionChangeRef.current = onSelectionChange;
  }, [onSelectionChange]);

  const selectedTeam = useMemo(
    () => teams.find((team) => getTeamId(team) === selectedTeamId) || null,
    [selectedTeamId, teams],
  );
  const isOwner = selectedTeam?.role === "owner";

  const selectWorkspace = useCallback((
    nextScope: WorkspaceScope,
    team: TeamWorkspace | null = selectedTeam,
  ) => {
    const teamId = team ? getTeamId(team) : selectedTeamId;
    onSelectionChangeRef.current({
      scope: nextScope,
      teamId,
      teamName: nextScope === "team" ? team?.name || null : null,
    });
  }, [selectedTeam, selectedTeamId]);

  const loadTeams = useCallback(async () => {
    try {
      const nextTeams = await fetchTeams();
      setTeams(nextTeams);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "팀 목록을 불러오지 못했습니다.");
    }
  }, []);

  const loadInvites = useCallback(async () => {
    try {
      setInvites(await fetchMyInvites());
    } catch {
      // 초대 목록 실패는 치명적이지 않으므로 조용히 무시한다.
    }
  }, []);


  const loadTeamDetails = useCallback(async (teamId: string, owner: boolean) => {
    try {
      setMembers(await fetchTeamMembers(teamId));
      if (owner) setSentInvites(await fetchTeamInvites(teamId));
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (scope === "team" && selectedTeamId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadTeamDetails(selectedTeamId, isOwner);
    } else {
      queueMicrotask(() => {
        setMembers([]);
        setSentInvites([]);
      });
    }
  }, [scope, selectedTeamId, isOwner, loadTeamDetails]);

  const handleLeaveTeam = async () => {
    if (!selectedTeamId || busy) return;
    if (!window.confirm("정말 탈퇴하시겠습니까?")) return;
    setBusy(true);
    try {
      await leaveTeam(selectedTeamId);
      await loadTeams();
      onSelectionChangeRef.current({ scope: "private", teamId: null, teamName: null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "탈퇴 실패");
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedTeamId || busy) return;
    if (!window.confirm("정말 추방하시겠습니까?")) return;
    setBusy(true);
    try {
      await removeTeamMember(selectedTeamId, userId);
      await loadTeamDetails(selectedTeamId, isOwner);
    } catch (err) {
      setError(err instanceof Error ? err.message : "추방 실패");
    } finally {
      setBusy(false);
    }
  };

  const handleCancelInvite = async (inviteId: string) => {
    if (!selectedTeamId || busy) return;
    if (!window.confirm("초대를 취소하시겠습니까?")) return;
    setBusy(true);
    try {
      await cancelTeamInvite(selectedTeamId, inviteId);
      await loadTeamDetails(selectedTeamId, isOwner);
    } catch (err) {
      setError(err instanceof Error ? err.message : "초대 취소 실패");
    } finally {
      setBusy(false);
    }
  };

  // 최초 마운트 시 1회만 로드한다.
  useEffect(() => {
    queueMicrotask(() => {
      void loadTeams();
      void loadInvites();
    });
  }, [loadTeams, loadInvites]);

  // 선택된 팀이 없고 팀이 존재하면 첫 팀을 기본 선택한다. (fetch와 분리)
  useEffect(() => {
    if (!selectedTeamId && teams.length > 0) {
      onSelectionChangeRef.current({
        scope,
        teamId: getTeamId(teams[0]),
        teamName: teams[0].name,
      });
    }
  }, [teams, selectedTeamId, scope]);

  const handleCreateTeam = async () => {
    const name = newTeamName.trim();
    if (!name || busy) return;
    setBusy(true);
    setError(null);
    try {
      const team = await createTeam(name);
      const teamId = getTeamId(team);
      setTeams((current) => [team, ...current.filter((item) => getTeamId(item) !== teamId)]);
      onSelectionChangeRef.current({ scope: "team", teamId, teamName: team.name });
      setNewTeamName("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "팀을 생성하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const handleInviteMember = async () => {
    const email = inviteEmail.trim();
    if (!selectedTeamId || !email || busy) return;
    setBusy(true);
    setError(null);
    try {
      await inviteTeamMember(selectedTeamId, email);
      setInviteEmail("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "팀원을 초대하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const handleAccept = async (invite: TeamInviteItem) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await acceptInvite(invite.inviteId);
      setInvites((current) => current.filter((item) => item.inviteId !== invite.inviteId));
      await loadTeams();
      onSelectionChangeRef.current({ scope: "team", teamId: invite.teamId, teamName: invite.teamName });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "초대를 수락하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const handleDecline = async (invite: TeamInviteItem) => {
    if (busy) return;
    if (!window.confirm(isKo ? "초대를 거절하시겠습니까?" : "Decline this invitation?")) return;
    setBusy(true);
    setError(null);
    try {
      await declineInvite(invite.inviteId);
      setInvites((current) => current.filter((item) => item.inviteId !== invite.inviteId));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "초대를 거절하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`mb-3 rounded-2xl border p-3 ${isDark ? "border-zinc-800 bg-zinc-900/60" : "border-zinc-200 bg-white"}`}>
      <div className="mb-2 flex items-center gap-2">
        <Users className="size-3.5 text-blue-400" />
        <span className={`text-xs font-bold ${isDark ? "text-zinc-200" : "text-zinc-800"}`}>{isKo ? "워크스페이스" : "Workspace"}</span>
      </div>
      <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Workspace Scope">
        <button
          type="button"
          role="radio"
          aria-checked={scope === "private"}
          onClick={() => selectWorkspace("private", null)}
          className={`rounded-lg border px-2.5 py-2 text-left text-[11px] font-semibold transition ${scope === "private" ? "border-blue-500 bg-blue-500/10 text-blue-400" : isDark ? "border-zinc-800 text-zinc-500 hover:bg-zinc-900" : "border-zinc-200 text-zinc-600 hover:bg-zinc-50"}`}
        >
          Private
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={scope === "team"}
          onClick={() => selectWorkspace("team")}
          disabled={!selectedTeamId}
          className={`rounded-lg border px-2.5 py-2 text-left text-[11px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${scope === "team" ? "border-emerald-500 bg-emerald-500/10 text-emerald-400" : isDark ? "border-zinc-800 text-zinc-500 hover:bg-zinc-900" : "border-zinc-200 text-zinc-600 hover:bg-zinc-50"}`}
        >
          Team
        </button>
      </div>
      {teams.length > 0 && (
        <select
          value={selectedTeamId || ""}
          onChange={(event) => {
            const team = teams.find((item) => getTeamId(item) === event.target.value) || null;
            onSelectionChangeRef.current({
              scope: event.target.value ? "team" : "private",
              teamId: team ? getTeamId(team) : null,
              teamName: team?.name || null,
            });
          }}
          className={`mt-2 w-full rounded-lg border px-2.5 py-2 text-[11px] outline-none ${isDark ? "border-zinc-800 bg-zinc-950 text-zinc-200" : "border-zinc-200 bg-white text-zinc-800"}`}
        >
          {teams.map((team) => (
            <option key={getTeamId(team)} value={getTeamId(team)}>
              {team.name} · {team.role}
            </option>
          ))}
        </select>
      )}
      <div className="mt-2 grid gap-2">
        <div className="flex gap-1.5">
          <input
            value={newTeamName}
            onChange={(event) => setNewTeamName(event.target.value)}
            placeholder={isKo ? "새 팀 이름" : "New team name"}
            className={`min-w-0 flex-1 rounded-lg border px-2.5 py-2 text-[11px] outline-none ${isDark ? "border-zinc-800 bg-zinc-950 text-zinc-200 placeholder:text-zinc-600" : "border-zinc-200 bg-white text-zinc-800 placeholder:text-zinc-400"}`}
          />
          <button type="button" onClick={handleCreateTeam} disabled={busy || !newTeamName.trim()} className={`rounded-lg px-2.5 text-[10px] font-bold disabled:opacity-40 ${isDark ? "bg-white text-black" : "bg-zinc-900 text-white"}`}>
            {isKo ? "생성" : "Create"}
          </button>
        </div>
        {/* 초대는 owner만 가능하므로 owner에게만 노출한다. (자체 PR 리뷰 N4) */}
        {selectedTeamId && isOwner && (
          <div className="flex gap-1.5">
            <input
              value={inviteEmail}
              onChange={(event) => setInviteEmail(event.target.value)}
              placeholder={isKo ? "초대할 이메일" : "Invite email"}
              className={`min-w-0 flex-1 rounded-lg border px-2.5 py-2 text-[11px] outline-none ${isDark ? "border-zinc-800 bg-zinc-950 text-zinc-200 placeholder:text-zinc-600" : "border-zinc-200 bg-white text-zinc-800 placeholder:text-zinc-400"}`}
            />
            <button type="button" onClick={handleInviteMember} disabled={busy || !inviteEmail.trim()} className="rounded-lg bg-blue-600 px-2.5 text-[10px] font-bold text-white disabled:opacity-40">
              {isKo ? "초대" : "Invite"}
            </button>
          </div>
        )}
      </div>

      {scope === "team" && selectedTeamId && (
        <div className={`mt-3 border-t pt-2.5 ${isDark ? "border-zinc-800" : "border-zinc-200/60"}`}>
          <div className="flex justify-between items-center mb-1.5">
            <span className={`text-[10px] font-bold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>팀 멤버 관리</span>
            <button type="button" onClick={handleLeaveTeam} disabled={busy} className="text-[10px] text-red-500 hover:underline">탈퇴하기</button>
          </div>
          <div className="grid gap-1.5 max-h-32 overflow-y-auto">
            {members.map(m => (
              <div key={m.userId} className={`flex items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-zinc-50"}`}>
                <span className={`min-w-0 flex-1 truncate text-[11px] ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>{m.email} ({m.role})</span>
                {isOwner && m.role !== "owner" && (
                  <button type="button" onClick={() => handleRemoveMember(m.userId)} disabled={busy} className="text-[10px] text-red-500 hover:underline">추방</button>
                )}
              </div>
            ))}
          </div>
          {isOwner && sentInvites.length > 0 && (
            <div className="mt-2">
              <span className={`text-[10px] font-bold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>보낸 초대</span>
              <div className="grid gap-1.5 mt-1.5 max-h-32 overflow-y-auto">
                {sentInvites.map(i => (
                  <div key={i.inviteId} className={`flex items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-zinc-50"}`}>
                    <span className={`min-w-0 flex-1 truncate text-[11px] ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>{i.email}</span>
                    <button type="button" onClick={() => handleCancelInvite(i.inviteId)} disabled={busy} className="text-[10px] text-red-500 hover:underline">취소</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {/* 나에게 온 pending 초대: 수락/거절 (PROJECT-TEAM-F-103) */}
      {invites.length > 0 && (
        <div className={`mt-3 border-t pt-2.5 ${isDark ? "border-zinc-800" : "border-zinc-200/60"}`}>
          <div className="mb-1.5 flex items-center gap-1.5">
            <Mail className="size-3 text-amber-500" />
            <span className={`text-[10px] font-bold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>{isKo ? "받은 초대" : "Invitations"}</span>
          </div>
          <div className="grid gap-1.5">
            {invites.map((invite) => (
              <div key={invite.inviteId} className={`flex items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 ${isDark ? "border-zinc-800 bg-zinc-950" : "border-zinc-200 bg-zinc-50"}`}>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className={`truncate text-[11px] font-semibold ${isDark ? "text-zinc-300" : "text-zinc-700"}`}>{invite.teamName}</span>
                  {(invite.invitedByEmail || invite.expiresAt) && (
                    <span className={`truncate text-[9px] ${isDark ? "text-zinc-500" : "text-zinc-400"}`}>
                      {invite.invitedByEmail ? `${isKo ? "보낸 사람" : "From"}: ${invite.invitedByEmail}` : ""}
                      {invite.invitedByEmail && invite.expiresAt ? " · " : ""}
                      {invite.expiresAt ? `${isKo ? "만료" : "Expires"}: ${new Date(invite.expiresAt).toLocaleDateString()}` : ""}
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <button type="button" onClick={() => handleAccept(invite)} disabled={busy} className="rounded-md bg-emerald-600 px-2 py-1 text-[10px] font-bold text-white disabled:opacity-40">
                    {isKo ? "수락" : "Accept"}
                  </button>
                  <button type="button" onClick={() => handleDecline(invite)} disabled={busy} className={`rounded-md px-2 py-1 text-[10px] font-semibold disabled:opacity-40 ${isDark ? "text-zinc-400 hover:bg-zinc-800" : "text-zinc-600 hover:bg-zinc-200"}`}>
                    {isKo ? "거절" : "Decline"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      <p className={`mt-2 text-[10px] leading-4 ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>
        {scope === "team" && selectedTeam
          ? `${selectedTeam.name} 팀 멤버에게만 분석 이력과 대화가 공유됩니다.`
          : "개인 기록은 본인 계정에서만 보입니다."}
      </p>
      {error && <p className="mt-2 text-[10px] font-medium text-red-400">{error}</p>}
    </div>
  );
}
