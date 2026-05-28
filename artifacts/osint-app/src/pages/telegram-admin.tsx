import { Layout } from "@/components/layout";
import { useState, useRef, useEffect, memo } from "react";
import type { EventResponse } from "@workspace/api-client-react";
import {
  useGetTelegramAuthStatus,
  useTelegramRequestCode,
  useTelegramVerifyCode,
  useTelegramLogout,
  useListTelegramChannels,
  useAddTelegramChannel,
  useUpdateTelegramChannel,
  useDeleteTelegramChannel,
  useApproveTelegramChannel,
  useTestFetchTelegramChannel,
  getListTelegramChannelsQueryKey,
  getGetTelegramAuthStatusQueryKey,
  getListEventsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Activity, ShieldAlert, Phone, KeyRound, LogOut, Plus, Trash2, Radio,
  CheckCircle2, MessageSquare, Clock, ShieldCheck, ShieldX, Lock, Eye,
  Download, Wifi, WifiOff, AlertTriangle,
} from "lucide-react";
import { useLiveEvents } from "@/hooks/use-live-events";
import { useToast } from "@/hooks/use-toast";
import {
  CATEGORY_COLORS,
  SIDE_COLORS,
  SIDE_LABELS,
  SIDE_BORDER_COLORS,
  CONFIDENCE_LEVEL_COLORS,
} from "@/lib/constants";

// ── helpers ────────────────────────────────────────────────────────────────────

function formatIsraelTime(utcStr: string): string {
  try {
    return new Intl.DateTimeFormat("he-IL", {
      timeZone: "Asia/Jerusalem",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(utcStr));
  } catch {
    return new Date(utcStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
}

function formatIsraelDate(utcStr: string): string {
  try {
    return new Intl.DateTimeFormat("he-IL", {
      timeZone: "Asia/Jerusalem",
      day: "2-digit",
      month: "2-digit",
    }).format(new Date(utcStr));
  } catch {
    return "";
  }
}

// ── InterceptRow (memoised — only re-renders when event object identity changes) ─

const InterceptRow = memo(function InterceptRow({ ev }: { ev: EventResponse }) {
  const side = ev.side ?? "neutral";
  const conf = ev.confidence_level ?? "low";
  const cat  = ev.category ?? "other";
  const srcLabel = ev.source_name
    ? ev.source_name.replace(/^Telegram:\s*/i, "@")
    : null;

  return (
    <div
      className={[
        "flex gap-2 p-2 rounded-md border-l-[3px] bg-background/60",
        "border border-border/40 text-sm",
        "animate-in fade-in slide-in-from-top-2 duration-300 ease-out",
        SIDE_BORDER_COLORS[side] ?? "border-l-slate-500/40",
      ].join(" ")}
    >
      {/* Timestamp column */}
      <div className="flex-none flex flex-col items-center justify-start pt-0.5 min-w-[42px]">
        <span className="text-[10px] font-mono font-bold text-foreground/70 tabular-nums leading-tight">
          {formatIsraelTime(ev.created_at)}
        </span>
        <span className="text-[9px] font-mono text-muted-foreground/50 tabular-nums">
          {formatIsraelDate(ev.created_at)}
        </span>
      </div>

      {/* Content column */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* Badge row */}
        <div className="flex flex-wrap items-center gap-1">
          <Badge
            className={`text-[9px] font-mono uppercase px-1 py-0 h-4 border-none text-white shrink-0 ${SIDE_COLORS[side] ?? "bg-slate-500"}`}
          >
            {SIDE_LABELS[side] ?? side}
          </Badge>
          <Badge
            className={`text-[9px] font-mono uppercase px-1 py-0 h-4 border-none text-white shrink-0 ${CATEGORY_COLORS[cat] ?? "bg-slate-500"}`}
          >
            {cat}
          </Badge>
          <Badge
            className={`text-[9px] font-mono uppercase px-1 py-0 h-4 border-none text-white shrink-0 ${CONFIDENCE_LEVEL_COLORS[conf] ?? "bg-slate-500"}`}
          >
            {conf}
          </Badge>
          {srcLabel && (
            <Badge
              variant="outline"
              className="text-[9px] font-mono px-1 py-0 h-4 border-border/50 text-muted-foreground max-w-[90px] shrink-0"
            >
              <span className="truncate block">{srcLabel}</span>
            </Badge>
          )}
          {ev.location_name && (
            <span className="text-[9px] font-mono text-muted-foreground/70 truncate max-w-[80px]">
              📍 {ev.location_name}
            </span>
          )}
        </div>

        {/* Hebrew title — RTL, wraps rather than truncates */}
        <p
          dir="rtl"
          lang="he"
          className="text-xs font-medium text-foreground/90 line-clamp-2 break-words leading-snug"
        >
          {ev.title_he || ev.title || "—"}
        </p>
      </div>
    </div>
  );
});

export default function TelegramAdmin() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: authStatus, isLoading: authLoading } = useGetTelegramAuthStatus({
    query: { queryKey: getGetTelegramAuthStatusQueryKey(), refetchInterval: 5000 },
  });

  const { data: channels, isLoading: channelsLoading } = useListTelegramChannels({
    query: { queryKey: getListTelegramChannelsQueryKey(), refetchInterval: 10000 },
  });

  const requestCode  = useTelegramRequestCode();
  const verifyCode   = useTelegramVerifyCode();
  const logout       = useTelegramLogout();
  const addChannel   = useAddTelegramChannel();
  const patchChannel = useUpdateTelegramChannel();
  const deleteChannel = useDeleteTelegramChannel();
  const approveChannel = useApproveTelegramChannel();
  const testFetch    = useTestFetchTelegramChannel();

  const [phone, setPhone]       = useState("");
  const [code, setCode]         = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep]         = useState<1 | 2 | 3>(1);
  const [newUsername, setNewUsername] = useState("");
  const [newTitle, setNewTitle]       = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [fetchingId, setFetchingId]   = useState<number | null>(null);

  const { events, status: liveStatus, messageCount, lastEventAt } = useLiveEvents(50);

  // Auto-scroll to top of intercept list whenever a new event arrives
  const interceptScrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (events.length > 0 && interceptScrollRef.current) {
      interceptScrollRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [events.length]);

  const invalidateChannels = () =>
    queryClient.invalidateQueries({ queryKey: getListTelegramChannelsQueryKey() });

  // ── auth handlers ──────────────────────────────────────────────────────────
  const handleRequestCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.startsWith("+")) {
      toast({ variant: "destructive", title: "Invalid Phone", description: "Must start with +" });
      return;
    }
    requestCode.mutate(
      { data: { phone } },
      {
        onSuccess: () => { setStep(3); toast({ title: "Code Sent", description: "Check your Telegram app." }); },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Error", description: err.message || "Failed to request code" }),
      },
    );
  };

  const handleVerifyCode = (e: React.FormEvent) => {
    e.preventDefault();
    verifyCode.mutate(
      { data: { phone, code, password: password || undefined } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetTelegramAuthStatusQueryKey() });
          toast({ title: "Authorized", description: "Successfully connected to Telegram." });
        },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Verification Failed", description: err.message || "Invalid code" }),
      },
    );
  };

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetTelegramAuthStatusQueryKey() });
        setStep(1);
        toast({ title: "Logged Out" });
      },
    });
  };

  // ── channel handlers ───────────────────────────────────────────────────────
  const handleAddChannel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim()) return;
    addChannel.mutate(
      { data: { username: newUsername, title: newTitle || undefined, is_active: true } },
      {
        onSuccess: () => {
          invalidateChannels();
          setNewUsername(""); setNewTitle(""); setShowAddForm(false);
          toast({
            title: "Channel Added — Pending Approval",
            description: `@${newUsername} verified as public channel. Click APPROVE to activate.`,
          });
        },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Rejected", description: err.message || "Could not add" }),
      },
    );
  };

  const handleApprove = (id: number, username: string) => {
    approveChannel.mutate(
      { channelId: id },
      {
        onSuccess: () => {
          invalidateChannels();
          toast({
            title: "Channel Approved & Joined",
            description: `@${username} is now in the whitelist. Live monitoring + backfill started.`,
          });
        },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Approval Failed", description: err.message }),
      },
    );
  };

  const handleToggleActive = (id: number, current: boolean) => {
    patchChannel.mutate(
      { channelId: id, data: { is_active: !current } },
      { onSuccess: invalidateChannels },
    );
  };

  const handleDelete = (id: number, username: string) => {
    deleteChannel.mutate(
      { channelId: id },
      {
        onSuccess: () => { invalidateChannels(); toast({ title: "Removed", description: `@${username} removed from whitelist.` }); },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Error", description: err.message }),
      },
    );
  };

  const handleTestFetch = (id: number, username: string) => {
    setFetchingId(id);
    testFetch.mutate(
      { channelId: id },
      {
        onSuccess: (data: any) => {
          invalidateChannels();
          queryClient.invalidateQueries({ queryKey: getGetTelegramAuthStatusQueryKey() });
          queryClient.invalidateQueries({ queryKey: getListEventsQueryKey() });
          toast({
            title: `Test Fetch: @${username}`,
            description: data.fetched > 0
              ? `✓ Fetched ${data.fetched} new message(s) — check the Live Intercepts panel.`
              : "No new messages since last poll. Channel is up to date.",
          });
        },
        onError: (err: any) =>
          toast({ variant: "destructive", title: "Fetch Failed", description: err.message }),
        onSettled: () => setFetchingId(null),
      },
    );
  };

  if (authLoading) {
    return <Layout><div className="p-6 h-full flex items-center justify-center"><Activity className="w-8 h-8 animate-spin text-primary" /></div></Layout>;
  }

  const isConfigured = authStatus?.configured;
  const isAuthorized = authStatus?.authorized;
  const pending  = (channels ?? []).filter(c => !c.is_approved);
  const approved = (channels ?? []).filter(c => c.is_approved);

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col gap-5 overflow-y-auto">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex flex-wrap justify-between items-center gap-3">
          <h2 className="text-2xl font-bold font-mono tracking-tight uppercase flex items-center gap-2">
            <MessageSquare className="w-6 h-6" />
            Telegram Operations
          </h2>
          {isAuthorized && (
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="font-mono bg-green-500/10 text-green-500 border-green-500/20">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                {authStatus.phone}
              </Badge>
              {/* Live counter strip */}
              <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground border border-border rounded px-2 py-1 bg-card">
                <span title="Raw MTProto updates received (any type)">
                  <span className="text-foreground font-bold">{authStatus.raw_updates_received ?? 0}</span> raw updates
                </span>
                <span className="text-border">|</span>
                <span title="Messages that passed all security gates and were stored">
                  <span className="text-green-400 font-bold">{authStatus.messages_processed ?? 0}</span> stored
                </span>
                <span className="text-border">|</span>
                <span title="Messages dropped by security gates">
                  <span className="text-amber-400 font-bold">{authStatus.messages_rejected ?? 0}</span> rejected
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}
                className="font-mono text-xs text-muted-foreground hover:text-destructive">
                <LogOut className="w-3 h-3 mr-1" /> DISCONNECT
              </Button>
            </div>
          )}
        </div>

        {/* ── Security Policy Banner ──────────────────────────────────── */}
        <div className="flex items-start gap-3 bg-blue-500/8 border border-blue-500/20 rounded-md px-4 py-3 text-xs font-mono text-blue-400">
          <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0" />
          <div className="space-y-0.5">
            <p className="font-bold uppercase tracking-widest text-blue-300">Security Policy Active</p>
            <p className="text-blue-400/80">
              Whitelist-only · Public broadcast channels only · No private chats, groups, or contacts · Manual approval required · All actions are audit-logged
            </p>
          </div>
        </div>

        {/* ── Auth Wizard ─────────────────────────────────────────────── */}
        {!isAuthorized && (
          <Card className="border-border bg-card">
            <CardHeader className="border-b border-border pb-4">
              <CardTitle className="font-mono text-lg flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-500" />
                Authentication Required
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                Connect a Telegram account to enable real-time intelligence gathering.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              {!isConfigured ? (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-md p-4 flex items-start gap-3">
                  <Activity className="w-5 h-5 text-amber-500 mt-0.5" />
                  <div>
                    <h4 className="font-mono text-sm font-bold text-amber-500 mb-1">NOT CONFIGURED</h4>
                    <p className="text-sm text-amber-500/80">TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are missing.</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-6 max-w-md">
                  <div className="flex items-center gap-2 text-xs font-mono mb-2">
                    {[["1. CONFIGURED", 1], ["2. PHONE", 2], ["3. VERIFY", 3]].map(([label, s]) => (
                      <span key={s} className={`px-2 py-1 rounded-sm ${
                        (s === 1 && isConfigured) || step === s
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}>{label}</span>
                    ))}
                  </div>
                  {step !== 3 ? (
                    <form onSubmit={handleRequestCode} className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">Phone Number</label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                          <Input value={phone} onChange={e => setPhone(e.target.value)}
                            placeholder="+1234567890" className="pl-9 font-mono bg-background border-border" required />
                        </div>
                      </div>
                      <Button type="submit" disabled={requestCode.isPending} className="w-full font-mono">
                        {requestCode.isPending && <Activity className="w-4 h-4 mr-2 animate-spin" />}
                        REQUEST CODE
                      </Button>
                    </form>
                  ) : (
                    <form onSubmit={handleVerifyCode} className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">Verification Code</label>
                        <Input value={code} onChange={e => setCode(e.target.value)}
                          placeholder="12345" className="font-mono bg-background border-border tracking-widest text-lg" required />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">2FA Password (Optional)</label>
                        <div className="relative">
                          <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                          <Input type="password" value={password} onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••" className="pl-9 font-mono bg-background border-border" />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button type="button" variant="outline" onClick={() => setStep(2)} className="flex-1 font-mono">BACK</Button>
                        <Button type="submit" disabled={verifyCode.isPending} className="flex-1 font-mono">
                          {verifyCode.isPending && <Activity className="w-4 h-4 mr-2 animate-spin" />}
                          VERIFY
                        </Button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Add Channel Form ─────────────────────────────────────────── */}
        {isAuthorized && (
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold font-mono tracking-tight uppercase">Monitored Sources</h3>
              {authStatus?.monitoring && (
                <p className="text-xs font-mono text-green-500 mt-1 flex items-center gap-1">
                  <Activity className="w-3 h-3 animate-pulse" />
                  ACTIVE — {authStatus.channels_active} channels · live listener + 30s polling fallback
                </p>
              )}
            </div>
            {!showAddForm && (
              <Button onClick={() => setShowAddForm(true)} size="sm" className="font-mono text-xs">
                <Plus className="w-4 h-4 mr-1" /> ADD CHANNEL
              </Button>
            )}
          </div>
        )}

        {showAddForm && (
          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start gap-2 text-xs font-mono text-amber-400/80">
                <Lock className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                <span>Only public broadcast channels are accepted. Verified via Telegram before saving. New channels require manual approval.</span>
              </div>
              <form onSubmit={handleAddChannel} className="flex flex-col md:flex-row gap-3 items-end">
                <div className="space-y-1.5 flex-1">
                  <label className="text-[10px] font-mono text-muted-foreground uppercase">Public Channel Username</label>
                  <Input value={newUsername} onChange={e => setNewUsername(e.target.value)}
                    placeholder="@channelname or https://t.me/channelname"
                    className="font-mono bg-background border-border text-sm h-9" required />
                </div>
                <div className="space-y-1.5 flex-1">
                  <label className="text-[10px] font-mono text-muted-foreground uppercase">Display Title (Optional)</label>
                  <Input value={newTitle} onChange={e => setNewTitle(e.target.value)}
                    placeholder="Custom Title"
                    className="font-mono bg-background border-border text-sm h-9" />
                </div>
                <div className="flex gap-2 w-full md:w-auto">
                  <Button type="button" variant="outline" onClick={() => setShowAddForm(false)}
                    className="font-mono text-xs h-9 flex-1 md:flex-none">CANCEL</Button>
                  <Button type="submit" disabled={addChannel.isPending}
                    className="font-mono text-xs h-9 flex-1 md:flex-none">
                    {addChannel.isPending
                      ? <Activity className="w-3 h-3 mr-1 animate-spin" />
                      : <Eye className="w-3 h-3 mr-1" />}
                    VERIFY & ADD
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* ── Pending Approval ─────────────────────────────────────────── */}
        {pending.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-bold font-mono tracking-widest text-amber-400 uppercase flex items-center gap-2">
              <ShieldX className="w-4 h-4" /> Pending Approval ({pending.length})
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {pending.map(ch => (
                <Card key={ch.id} className="border-amber-500/30 bg-amber-500/5 border-l-4 border-l-amber-500">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <div className="truncate pr-2">
                        <h4 className="font-bold text-sm truncate">{ch.title || ch.username}</h4>
                        <p className="text-xs font-mono text-muted-foreground">@{ch.username}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 bg-amber-500/10 text-amber-400 border-amber-500/30">
                          PENDING
                        </Badge>
                        {ch.is_public_verified && (
                          <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 bg-green-500/10 text-green-400 border-green-500/20">
                            <ShieldCheck className="w-2.5 h-2.5 mr-0.5" /> PUBLIC ✓
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="text-[10px] font-mono text-muted-foreground mb-3">
                      Added {new Date(ch.created_at).toLocaleString()} · awaiting approval
                    </p>
                    <div className="flex gap-2">
                      <Button size="sm" className="flex-1 h-7 text-xs font-mono bg-green-600 hover:bg-green-700"
                        onClick={() => handleApprove(ch.id, ch.username)}
                        disabled={approveChannel.isPending}>
                        {approveChannel.isPending
                          ? <Activity className="w-3 h-3 mr-1 animate-spin" />
                          : <ShieldCheck className="w-3 h-3 mr-1" />}
                        APPROVE
                      </Button>
                      <Button variant="outline" size="icon" className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive border-transparent"
                        onClick={() => handleDelete(ch.id, ch.username)}
                        disabled={deleteChannel.isPending}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* ── Approved & Active ─────────────────────────────────────────── */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold font-mono tracking-widest text-green-400 uppercase flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" /> Approved Whitelist ({approved.length})
          </h4>

          {channelsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => <Card key={i} className="h-44 animate-pulse bg-card/50 border-border" />)}
            </div>
          ) : approved.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-8 flex flex-col items-center justify-center text-center bg-card/20">
              <Radio className="w-8 h-8 text-muted-foreground mb-3 opacity-50" />
              <p className="text-sm font-medium text-foreground/80 mb-1">No approved channels</p>
              <p className="text-xs text-muted-foreground max-w-md">
                Add a public channel username (e.g., @AJArabic) then approve it to start monitoring.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {approved.map(ch => {
                const ls = ch.listener_status;
                const isJoined   = ls?.joined === true;
                const joinError  = ls?.error;
                const isFetching = fetchingId === ch.id;

                return (
                  <Card key={ch.id} className={`bg-card border-border transition-colors ${
                    ch.is_active ? "border-l-4 border-l-green-500" : "border-l-4 border-l-muted opacity-60"
                  }`}>
                    <CardContent className="p-4">
                      {/* Title row */}
                      <div className="flex justify-between items-start mb-2">
                        <div className="truncate pr-2">
                          <h4 className="font-bold text-sm truncate">{ch.title || ch.username}</h4>
                          <p className="text-xs font-mono text-muted-foreground">@{ch.username}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <Badge variant={ch.is_active ? "default" : "secondary"}
                            className="text-[9px] font-mono px-1.5 py-0">
                            {ch.is_active ? "ACTIVE" : "PAUSED"}
                          </Badge>
                          {ch.is_public_verified && (
                            <Badge variant="outline"
                              className="text-[9px] font-mono px-1.5 py-0 bg-green-500/10 text-green-400 border-green-500/20">
                              <ShieldCheck className="w-2.5 h-2.5 mr-0.5" /> PUBLIC ✓
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Listener status badge */}
                      <div className="mb-3">
                        {ls === null || ls === undefined ? (
                          <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground">
                            <WifiOff className="w-3 h-3" /> Not initialized
                          </div>
                        ) : isJoined ? (
                          <div className="flex items-center gap-1.5 text-[10px] font-mono text-green-400">
                            <Wifi className="w-3 h-3 animate-pulse" />
                            <span className="font-bold">JOINED</span>
                            <span className="text-muted-foreground">— receiving live updates</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5 text-[10px] font-mono text-amber-400">
                            <AlertTriangle className="w-3 h-3" />
                            <span className="font-bold">NOT JOINED</span>
                            {joinError && (
                              <span className="text-muted-foreground truncate max-w-[120px]" title={joinError}>
                                {joinError}
                              </span>
                            )}
                          </div>
                        )}
                        {ls?.polled_at && (
                          <div className="text-[9px] font-mono text-muted-foreground mt-0.5">
                            Last poll: {new Date(ls.polled_at).toLocaleTimeString()}
                          </div>
                        )}
                      </div>

                      {/* Stats */}
                      <div className="space-y-0.5 mb-3">
                        {ch.approved_at && (
                          <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                            Approved {new Date(ch.approved_at).toLocaleDateString()}
                          </div>
                        )}
                        <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                          <MessageSquare className="w-3 h-3" />
                          {ch.messages_processed || 0} messages stored
                        </div>
                        {ch.last_activity_at && (
                          <div className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            Last: {new Date(ch.last_activity_at).toLocaleTimeString()}
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex gap-1">
                        {/* Test Fetch */}
                        <Button
                          size="sm"
                          variant="outline"
                          className="flex-1 h-7 text-[10px] font-mono font-bold"
                          onClick={() => handleTestFetch(ch.id, ch.username)}
                          disabled={isFetching || !isAuthorized}
                          title="Fetch latest 10 messages from this channel right now"
                        >
                          {isFetching
                            ? <Activity className="w-3 h-3 mr-1 animate-spin" />
                            : <Download className="w-3 h-3 mr-1" />}
                          TEST FETCH
                        </Button>
                        {/* Toggle active */}
                        <Button variant="outline" size="icon" className="h-7 w-7"
                          onClick={() => handleToggleActive(ch.id, ch.is_active ?? false)}
                          disabled={patchChannel.isPending}
                          title={ch.is_active ? "Pause monitoring" : "Resume monitoring"}>
                          <Activity className={`w-3 h-3 ${ch.is_active ? "text-primary" : "text-muted-foreground"}`} />
                        </Button>
                        {/* Delete */}
                        <Button variant="outline" size="icon"
                          className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive border-transparent"
                          onClick={() => handleDelete(ch.id, ch.username)}
                          disabled={deleteChannel.isPending}>
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Live Intercepts feed ─────────────────────────────────────── */}
        {isAuthorized && (
          <div className="border border-border rounded-lg bg-card flex flex-col h-[420px] sm:h-[480px]">
            {/* Header */}
            <div className="px-3 py-2 border-b border-border bg-muted/20 flex flex-wrap justify-between items-center gap-2 shrink-0">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                <Radio className="w-3.5 h-3.5" />
                Live Intercepts
                {events.length > 0 && (
                  <span className="font-normal text-muted-foreground">
                    ({events.length})
                  </span>
                )}
              </h3>

              <div className="flex items-center gap-2 text-[10px] font-mono flex-wrap">
                {/* SSE connection state */}
                {liveStatus === "connected" ? (
                  <span className="flex items-center gap-1 text-green-500 font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    LIVE
                  </span>
                ) : liveStatus === "connecting" ? (
                  <span className="flex items-center gap-1 text-yellow-500">
                    <Activity className="w-3 h-3 animate-spin" />
                    CONNECTING
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-destructive">
                    <WifiOff className="w-3 h-3" />
                    RECONNECTING
                  </span>
                )}

                <span className="text-border/60">|</span>

                {/* Event counter */}
                <span className="text-muted-foreground">
                  <span className="text-foreground font-bold">{messageCount}</span> recv
                </span>

                {/* Timestamp of last event */}
                {lastEventAt && (
                  <>
                    <span className="text-border/60">|</span>
                    <span className="text-muted-foreground">
                      last{" "}
                      <span className="text-foreground">
                        {lastEventAt.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </span>
                  </>
                )}

                {/* Timezone label */}
                <span className="text-muted-foreground/50 hidden sm:inline">IL time</span>
              </div>
            </div>

            {/* Scroll body */}
            <div
              ref={interceptScrollRef}
              className="flex-1 overflow-y-auto overscroll-contain p-2 space-y-1.5 scroll-smooth"
            >
              {events.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-xs font-mono select-none">
                  <Radio className="w-7 h-7 mb-2 opacity-20" />
                  <p className="italic opacity-40">Waiting for intercepts…</p>
                  <p className="text-[10px] opacity-25 mt-1">
                    Use &ldquo;TEST FETCH&rdquo; on any approved channel to trigger immediately
                  </p>
                </div>
              ) : (
                events.map((ev) => (
                  <InterceptRow key={ev.id} ev={ev} />
                ))
              )}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
