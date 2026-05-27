import { Layout } from "@/components/layout";
import { useListSources, useGetScraperStatus, useTriggerScraper } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Play, RefreshCw, AlertTriangle, ShieldCheck } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function SourcesList() {
  const { data: sources, isLoading } = useListSources();
  const { data: status } = useGetScraperStatus({ query: { refetchInterval: 3000 } });
  const triggerScraper = useTriggerScraper();
  const { toast } = useToast();

  const handleTrigger = () => {
    triggerScraper.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: "Scraper Triggered",
          description: "Data collection sequence initiated.",
        });
      },
      onError: () => {
        toast({
          variant: "destructive",
          title: "Error",
          description: "Failed to trigger scraper sequence.",
        });
      }
    });
  };

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold font-mono tracking-tight">INTELLIGENCE SOURCES</h2>
          
          <div className="flex items-center gap-4">
            {status?.is_running && (
              <div className="flex items-center gap-2 text-primary font-mono text-sm">
                <RefreshCw className="w-4 h-4 animate-spin" />
                COLLECTION IN PROGRESS...
              </div>
            )}
            <Button 
              onClick={handleTrigger} 
              disabled={status?.is_running || triggerScraper.isPending}
              variant={status?.is_running ? "outline" : "default"}
              className="font-mono"
            >
              {status?.is_running ? <Activity className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {status?.is_running ? "RUNNING" : "TRIGGER SCRAPER"}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-y-auto pb-6">
          {isLoading ? (
            Array(6).fill(0).map((_, i) => (
              <Card key={i} className="bg-card border-border animate-pulse h-[140px]" />
            ))
          ) : sources?.map((source) => (
            <Card key={source.id} className="bg-card border-border hover:border-primary/50 transition-colors">
              <CardContent className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-bold text-lg leading-none mb-1">{source.name}</h3>
                    <div className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">{source.url}</div>
                  </div>
                  <Badge variant={source.is_active ? "default" : "secondary"} className="font-mono text-[10px]">
                    {source.is_active ? "ACTIVE" : "INACTIVE"}
                  </Badge>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mt-6 border-t border-border pt-4">
                  <div>
                    <div className="text-[10px] uppercase text-muted-foreground font-mono mb-1">TYPE</div>
                    <div className="text-sm font-medium">{source.type}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-muted-foreground font-mono mb-1">EVENTS</div>
                    <div className="text-sm font-medium">{source.events_count}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </Layout>
  );
}
