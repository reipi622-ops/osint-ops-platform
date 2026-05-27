import { Layout } from "@/components/layout";
import { useListEvents, useGetEvent, getGetEventQueryKey } from "@workspace/api-client-react";
import { useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { CATEGORY_HEX_COLORS, CATEGORY_COLORS } from "@/lib/constants";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Loader2 } from "lucide-react";

export default function MapView() {
  const [search, setSearch] = useState("");
  const { data: eventsData, isLoading } = useListEvents({ search, limit: 100 });
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const { data: selectedEvent } = useGetEvent(selectedEventId!, {
    query: { queryKey: getGetEventQueryKey(selectedEventId!), enabled: !!selectedEventId }
  });

  return (
    <Layout>
      <div className="flex h-full w-full">
        <div className="w-80 border-r border-border bg-card flex flex-col z-10 shadow-2xl">
          <div className="p-4 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search events..."
                className="pl-8 bg-background border-border font-mono text-sm"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <ScrollArea className="flex-1 p-2">
            {isLoading ? (
              <div className="flex justify-center p-4">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : (
              <div className="space-y-2">
                {eventsData?.items.map((event) => (
                  <div 
                    key={event.id}
                    className="p-3 rounded border border-border bg-background hover:border-primary/50 cursor-pointer transition-colors"
                    onClick={() => setSelectedEventId(event.id)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-2 h-2 rounded-full ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`} />
                      <span className="text-xs font-mono text-muted-foreground uppercase">{event.category}</span>
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(event.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <h3 className="text-sm font-medium leading-tight line-clamp-2" dir="rtl">{event.title_he || event.title}</h3>
                    {event.location_name && (
                      <p className="text-xs text-muted-foreground mt-2 truncate">📍 {event.location_name}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
        <div className="flex-1 relative bg-black">
          <MapContainer 
            center={[31.5, 35.0]} 
            zoom={7} 
            className="w-full h-full"
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            {eventsData?.items.map((event) => {
              if (!event.lat || !event.lng) return null;
              return (
                <CircleMarker
                  key={event.id}
                  center={[event.lat, event.lng]}
                  radius={6}
                  pathOptions={{
                    fillColor: CATEGORY_HEX_COLORS[event.category] || CATEGORY_HEX_COLORS.other,
                    fillOpacity: 0.7,
                    color: CATEGORY_HEX_COLORS[event.category] || CATEGORY_HEX_COLORS.other,
                    weight: 2
                  }}
                  eventHandlers={{
                    click: () => setSelectedEventId(event.id)
                  }}
                >
                  <Popup className="custom-popup">
                    <div className="p-1 min-w-[200px]" dir="rtl">
                      <Badge variant="outline" className={`mb-2 font-mono ${CATEGORY_COLORS[event.category]}`}>
                        {event.category}
                      </Badge>
                      <h4 className="font-bold text-sm mb-1">{event.title_he || event.title}</h4>
                      <div className="text-xs text-muted-foreground mt-2" dir="ltr">
                        <div>Source: {event.source_name}</div>
                        <div>Conf: {(event.confidence * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
      </div>
    </Layout>
  );
}
