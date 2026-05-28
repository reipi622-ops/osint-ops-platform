import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import MapView from "@/pages/map-view";
import Dashboard from "@/pages/dashboard";
import EventsList from "@/pages/events";
import SourcesList from "@/pages/sources";
import TelegramAdmin from "@/pages/telegram-admin";
import AlertsPage from "@/pages/alerts";
import TimelinePage from "@/pages/timeline";

const queryClient = new QueryClient();

function Router() {
  return (
    <Switch>
      <Route path="/" component={MapView} />
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/events" component={EventsList} />
      <Route path="/alerts" component={AlertsPage} />
      <Route path="/timeline" component={TimelinePage} />
      <Route path="/sources" component={SourcesList} />
      <Route path="/telegram" component={TelegramAdmin} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
