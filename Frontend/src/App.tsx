import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import Decks from "./pages/Decks";
import DeckEditor from "./pages/DeckEditor";
import StudyFreeResponse from "./pages/StudyFreeResponse";
import StudyMCQ from "./pages/StudyMCQ";
import StudyTrueFalse from "./pages/StudyTrueFalse";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<ProtectedRoute><Index /></ProtectedRoute>} />
            <Route path="/auth" element={<Auth />} />
            <Route path="/decks" element={<ProtectedRoute><Decks /></ProtectedRoute>} />
            <Route path="/decks/new" element={<ProtectedRoute><DeckEditor /></ProtectedRoute>} />
            <Route path="/decks/:deckId/edit" element={<ProtectedRoute><DeckEditor /></ProtectedRoute>} />
            <Route path="/study/free-response/:deckId" element={<ProtectedRoute><StudyFreeResponse /></ProtectedRoute>} />
            <Route path="/study/mcq/:deckId" element={<ProtectedRoute><StudyMCQ /></ProtectedRoute>} />
            <Route path="/study/true-false/:deckId" element={<ProtectedRoute><StudyTrueFalse /></ProtectedRoute>} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
