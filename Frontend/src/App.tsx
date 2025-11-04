import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import Decks from "./pages/Decks";
import DeckEditor from "./pages/DeckEditor";
import StudyFreeResponse from "./pages/StudyFreeResponse";
import StudyMCQ from "./pages/StudyMCQ";
import StudyTrueFalse from "./pages/StudyTrueFalse";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/decks" element={<Decks />} />
          <Route path="/decks/new" element={<DeckEditor />} />
          <Route path="/decks/:deckId/edit" element={<DeckEditor />} />
          <Route path="/study/free-response/:deckId" element={<StudyFreeResponse />} />
          <Route path="/study/mcq/:deckId" element={<StudyMCQ />} />
          <Route path="/study/true-false/:deckId" element={<StudyTrueFalse />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
