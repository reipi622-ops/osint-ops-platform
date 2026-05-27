import { Layout } from "@/components/layout";
import { useState } from "react";
import { 
  useGetTelegramAuthStatus, 
  useTelegramRequestCode, 
  useTelegramVerifyCode, 
  useTelegramLogout,
  useListTelegramChannels,
  useAddTelegramChannel,
  useUpdateTelegramChannel,
  useDeleteTelegramChannel,
  getListTelegramChannelsQueryKey,
  getGetTelegramAuthStatusQueryKey
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Activity, ShieldAlert, Phone, KeyRound, LogOut, Plus, Trash2, Radio, CheckCircle2, MessageSquare, Clock } from "lucide-react";
import { useLiveEvents } from "@/hooks/use-live-events";
import { useToast } from "@/hooks/use-toast";
import { CATEGORY_COLORS } from "@/lib/constants";

export default function TelegramAdmin() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  
  const { data: authStatus, isLoading: authLoading } = useGetTelegramAuthStatus({ 
    query: { queryKey: getGetTelegramAuthStatusQueryKey(), refetchInterval: 10000 } 
  });
  
  const { data: channels, isLoading: channelsLoading } = useListTelegramChannels();
  
  const requestCode = useTelegramRequestCode();
  const verifyCode = useTelegramVerifyCode();
  const logout = useTelegramLogout();
  
  const addChannel = useAddTelegramChannel();
  const patchChannel = useUpdateTelegramChannel();
  const deleteChannel = useDeleteTelegramChannel();

  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<1 | 2 | 3>(1);

  const [newChannelUsername, setNewChannelUsername] = useState("");
  const [newChannelTitle, setNewChannelTitle] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  const { events, status: liveStatus } = useLiveEvents(20);

  const handleRequestCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.startsWith("+")) {
      toast({ variant: "destructive", title: "Invalid Phone", description: "Must start with +" });
      return;
    }
    requestCode.mutate(
      { data: { phone } },
      {
        onSuccess: () => {
          setStep(3);
          toast({ title: "Code Sent", description: "Check your Telegram app." });
        },
        onError: (err: any) => {
          toast({ variant: "destructive", title: "Error", description: err.message || "Failed to request code" });
        }
      }
    );
  };

  const handleVerifyCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length !== 6 && code.length !== 5) { // Telegram codes are usually 5 or 6 digits
      toast({ variant: "destructive", title: "Invalid Code", description: "Please enter the code correctly." });
      return;
    }
    verifyCode.mutate(
      { data: { phone, code, password: password || undefined } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetTelegramAuthStatusQueryKey() });
          toast({ title: "Authorized", description: "Successfully connected to Telegram." });
        },
        onError: (err: any) => {
          toast({ variant: "destructive", title: "Verification Failed", description: err.message || "Invalid code or password" });
        }
      }
    );
  };

  const handleLogout = () => {
    logout.mutate(
      undefined,
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getGetTelegramAuthStatusQueryKey() });
          setStep(1);
          toast({ title: "Logged Out", description: "Disconnected from Telegram." });
        }
      }
    );
  };

  const handleAddChannel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChannelUsername.startsWith("@") && !newChannelUsername.startsWith("https://")) {
      toast({ variant: "destructive", title: "Invalid Username", description: "Must start with @ or be a valid link." });
      return;
    }
    addChannel.mutate(
      { data: { username: newChannelUsername, title: newChannelTitle || undefined, is_active: true } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListTelegramChannelsQueryKey() });
          setNewChannelUsername("");
          setNewChannelTitle("");
          setShowAddForm(false);
          toast({ title: "Channel Added", description: "Now monitoring " + newChannelUsername });
        },
        onError: (err: any) => {
          toast({ variant: "destructive", title: "Failed to Add", description: err.message || "Could not add channel" });
        }
      }
    );
  };

  const handleToggleActive = (id: number, currentActive: boolean) => {
    patchChannel.mutate(
      { channelId: id, data: { is_active: !currentActive } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListTelegramChannelsQueryKey() });
        }
      }
    );
  };

  const handleDelete = (id: number) => {
    deleteChannel.mutate(
      { channelId: id },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListTelegramChannelsQueryKey() });
          toast({ title: "Channel Deleted" });
        }
      }
    );
  };

  if (authLoading) {
    return <Layout><div className="p-6 h-full flex items-center justify-center"><Activity className="w-8 h-8 animate-spin text-primary" /></div></Layout>;
  }

  const isConfigured = authStatus?.configured;
  const isAuthorized = authStatus?.authorized;

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col gap-6 overflow-y-auto">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold font-mono tracking-tight uppercase flex items-center gap-2">
            <MessageSquare className="w-6 h-6" />
            Telegram Operations
          </h2>
          {isAuthorized && (
            <div className="flex items-center gap-4">
              <Badge variant="outline" className="font-mono bg-green-500/10 text-green-500 border-green-500/20">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                AUTHORIZED: {authStatus.phone}
              </Badge>
              <Button variant="ghost" size="sm" onClick={handleLogout} className="font-mono text-xs text-muted-foreground hover:text-destructive">
                <LogOut className="w-3 h-3 mr-1" /> DISCONNECT
              </Button>
            </div>
          )}
        </div>

        {/* Section A: Auth Wizard */}
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
                    <p className="text-sm text-amber-500/80 mb-2">TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables are missing.</p>
                    <p className="text-xs font-mono text-amber-500/60">Please refer to /TELEGRAM_SETUP.md for instructions on obtaining API credentials.</p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-6 max-w-md">
                  <div className="flex items-center gap-2 text-xs font-mono mb-2">
                    <span className={`px-2 py-1 rounded-sm ${step === 1 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>1. CONFIGURED</span>
                    <span className="text-muted-foreground">-&gt;</span>
                    <span className={`px-2 py-1 rounded-sm ${step === 2 || (step === 1 && isConfigured) ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>2. PHONE</span>
                    <span className="text-muted-foreground">-&gt;</span>
                    <span className={`px-2 py-1 rounded-sm ${step === 3 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>3. VERIFY</span>
                  </div>

                  {step !== 3 ? (
                    <form onSubmit={handleRequestCode} className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">Phone Number</label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                          <Input 
                            value={phone} 
                            onChange={(e) => setPhone(e.target.value)} 
                            placeholder="+1234567890" 
                            className="pl-9 font-mono bg-background border-border"
                            required
                          />
                        </div>
                      </div>
                      <Button type="submit" disabled={requestCode.isPending} className="w-full font-mono">
                        {requestCode.isPending ? <Activity className="w-4 h-4 mr-2 animate-spin" /> : null}
                        REQUEST CODE
                      </Button>
                    </form>
                  ) : (
                    <form onSubmit={handleVerifyCode} className="space-y-4">
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">Verification Code</label>
                        <Input 
                          value={code} 
                          onChange={(e) => setCode(e.target.value)} 
                          placeholder="12345" 
                          className="font-mono bg-background border-border tracking-widest text-lg"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-mono text-muted-foreground uppercase">2FA Password (Optional)</label>
                        <div className="relative">
                          <KeyRound className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                          <Input 
                            type="password"
                            value={password} 
                            onChange={(e) => setPassword(e.target.value)} 
                            placeholder="••••••••" 
                            className="pl-9 font-mono bg-background border-border"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button type="button" variant="outline" onClick={() => setStep(2)} className="flex-1 font-mono">
                          BACK
                        </Button>
                        <Button type="submit" disabled={verifyCode.isPending} className="flex-1 font-mono">
                          {verifyCode.isPending ? <Activity className="w-4 h-4 mr-2 animate-spin" /> : null}
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

        {/* Section B: Monitored Channels */}
        <div className="flex flex-col gap-4 flex-1">
          <div className="flex justify-between items-end">
            <div>
              <h3 className="text-lg font-bold font-mono tracking-tight text-foreground/90 uppercase">Monitored Sources</h3>
              {authStatus?.monitoring && (
                <p className="text-xs font-mono text-green-500 mt-1 flex items-center gap-1">
                  <Activity className="w-3 h-3" />
                  ACTIVE MONITORING: {authStatus.messages_processed || 0} MESSAGES PROCESSED
                </p>
              )}
            </div>
            {!showAddForm && isAuthorized ? (
              <Button onClick={() => setShowAddForm(true)} size="sm" className="font-mono text-xs">
                <Plus className="w-4 h-4 mr-1" /> ADD CHANNEL
              </Button>
            ) : null}
          </div>

          {showAddForm && (
            <Card className="border-border bg-card/50">
              <CardContent className="p-4">
                <form onSubmit={handleAddChannel} className="flex flex-col md:flex-row gap-3 items-end">
                  <div className="space-y-1.5 flex-1">
                    <label className="text-[10px] font-mono text-muted-foreground uppercase">Username or Link</label>
                    <Input 
                      value={newChannelUsername} 
                      onChange={(e) => setNewChannelUsername(e.target.value)} 
                      placeholder="@channelname" 
                      className="font-mono bg-background border-border text-sm h-9"
                      required
                    />
                  </div>
                  <div className="space-y-1.5 flex-1">
                    <label className="text-[10px] font-mono text-muted-foreground uppercase">Display Title (Optional)</label>
                    <Input 
                      value={newChannelTitle} 
                      onChange={(e) => setNewChannelTitle(e.target.value)} 
                      placeholder="Custom Title" 
                      className="font-mono bg-background border-border text-sm h-9"
                    />
                  </div>
                  <div className="flex gap-2 w-full md:w-auto">
                    <Button type="button" variant="outline" onClick={() => setShowAddForm(false)} className="font-mono text-xs h-9 flex-1 md:flex-none">
                      CANCEL
                    </Button>
                    <Button type="submit" disabled={addChannel.isPending} className="font-mono text-xs h-9 flex-1 md:flex-none">
                      {addChannel.isPending ? <Activity className="w-3 h-3 mr-1 animate-spin" /> : <Plus className="w-3 h-3 mr-1" />}
                      ADD
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {channelsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => <Card key={i} className="h-32 animate-pulse bg-card/50 border-border" />)}
            </div>
          ) : !channels?.length ? (
            <div className="border border-dashed border-border rounded-lg p-8 flex flex-col items-center justify-center text-center bg-card/20">
              <Radio className="w-8 h-8 text-muted-foreground mb-3 opacity-50" />
              <p className="text-sm font-medium text-foreground/80 mb-1">No channels configured</p>
              <p className="text-xs text-muted-foreground max-w-md">Add a Telegram channel username (e.g., @BreakingNews) to start receiving live intelligence updates.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {channels.map((channel) => (
                <Card key={channel.id} className={`bg-card border-border transition-colors ${channel.is_active ? 'border-l-4 border-l-primary' : 'border-l-4 border-l-muted opacity-60'}`}>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="truncate pr-2">
                        <h4 className="font-bold text-sm truncate">{channel.title || channel.username}</h4>
                        <p className="text-xs font-mono text-muted-foreground truncate">{channel.username}</p>
                      </div>
                      <Badge variant={channel.is_active ? "default" : "secondary"} className="text-[9px] font-mono px-1.5 py-0">
                        {channel.is_active ? "ACTIVE" : "INACTIVE"}
                      </Badge>
                    </div>
                    
                    <div className="flex justify-between items-end mt-4">
                      <div className="space-y-1">
                        <div className="text-[10px] font-mono text-muted-foreground uppercase flex items-center">
                          <MessageSquare className="w-3 h-3 mr-1" />
                          {channel.messages_processed || 0} msgs
                        </div>
                        {channel.last_activity_at && (
                          <div className="text-[10px] font-mono text-muted-foreground uppercase flex items-center">
                            <Clock className="w-3 h-3 mr-1" />
                            {new Date(channel.last_activity_at).toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex gap-1">
                        <Button 
                          variant="outline" 
                          size="icon" 
                          className="h-7 w-7"
                          onClick={() => handleToggleActive(channel.id, channel.is_active ?? false)}
                          disabled={patchChannel.isPending}
                        >
                          <Activity className={`w-3 h-3 ${channel.is_active ? 'text-primary' : 'text-muted-foreground'}`} />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="icon" 
                          className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive border-transparent"
                          onClick={() => handleDelete(channel.id)}
                          disabled={deleteChannel.isPending}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Section C: Live Feed */}
        {isAuthorized && (
          <div className="mt-auto border border-border rounded-lg bg-card flex flex-col h-[300px]">
            <div className="p-3 border-b border-border bg-muted/20 flex justify-between items-center">
              <h3 className="font-mono text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                <Radio className="w-4 h-4" />
                Live Stream
              </h3>
              <div className="flex items-center gap-2 text-[10px] font-mono">
                {liveStatus === 'connected' ? (
                  <span className="flex items-center text-green-500 font-bold">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse mr-1.5" />
                    LIVE
                  </span>
                ) : liveStatus === 'connecting' ? (
                  <span className="flex items-center text-yellow-500">
                    <Activity className="w-3 h-3 mr-1 animate-spin" />
                    CONNECTING
                  </span>
                ) : (
                  <span className="text-destructive">RECONNECTING...</span>
                )}
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {events.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground text-xs font-mono italic opacity-50">
                  Waiting for incoming intercepts...
                </div>
              ) : (
                events.map((event, i) => (
                  <div key={event.id || i} className="flex flex-col md:flex-row gap-2 md:gap-4 p-3 rounded bg-background border border-border/50 text-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="flex-none flex items-center gap-2 md:w-32 text-[10px] font-mono text-muted-foreground">
                      <span>{new Date(event.created_at || Date.now()).toLocaleTimeString()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-2 mb-1.5">
                        <Badge variant="outline" className={`text-[9px] font-mono uppercase px-1.5 py-0 ${CATEGORY_COLORS[event.category || "other"]} text-white border-transparent`}>
                          {event.category || "other"}
                        </Badge>
                        {event.location_name && (
                          <Badge variant="outline" className="text-[9px] font-mono px-1.5 py-0 text-muted-foreground">
                            {event.location_name}
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium text-foreground/90 truncate pr-4" dir="rtl">{event.title_he || event.title}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
