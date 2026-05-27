import { Layout } from "@/components/layout";
import { useListEvents } from "@workspace/api-client-react";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { CATEGORY_COLORS } from "@/lib/constants";
import { Loader2, Search } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";

export default function EventsList() {
  const [search, setSearch] = useState("");
  const { data: eventsData, isLoading } = useListEvents({ search, limit: 50 });

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold font-mono tracking-tight">EVENT LOG</h2>
          <div className="relative w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter events..."
              className="pl-8 bg-card border-border font-mono text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="flex-1 bg-card rounded-md border border-border overflow-hidden flex flex-col">
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-auto flex-1">
              <Table>
                <TableHeader className="bg-muted/50 sticky top-0 z-10 backdrop-blur-sm">
                  <TableRow>
                    <TableHead className="w-[100px] font-mono">TIME</TableHead>
                    <TableHead className="font-mono">CATEGORY</TableHead>
                    <TableHead className="font-mono max-w-[400px]">TITLE (HE)</TableHead>
                    <TableHead className="font-mono">LOCATION</TableHead>
                    <TableHead className="font-mono">SOURCE</TableHead>
                    <TableHead className="font-mono w-[150px]">CONFIDENCE</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {eventsData?.items.map((event) => (
                    <TableRow key={event.id} className="hover:bg-muted/50 cursor-pointer transition-colors border-border">
                      <TableCell className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(event.created_at).toLocaleString(undefined, {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={`font-mono text-[10px] uppercase border-none text-white ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`}>
                          {event.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium" dir="rtl">
                        <div className="line-clamp-1">{event.title_he || event.title}</div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground whitespace-nowrap truncate max-w-[150px]">
                        {event.location_name || "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                        {event.source_name || "-"}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={event.confidence * 100} className="h-2 w-16" />
                          <span className="text-xs font-mono text-muted-foreground">{(event.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {eventsData?.items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        No events found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
