import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import FlashcardGenerator from "@/components/FlashcardGenerator";
import Header from "@/components/Header";
import authService from "@/lib/auth";

const Index = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is authenticated on mount
    if (!authService.isAuthenticated()) {
      navigate("/auth");
    }
  }, [navigate]);

  const handleLogout = () => {
    authService.logout();
    navigate("/auth");
  };

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={handleLogout} />
      
      <main className="py-6 sm:py-12 px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 bg-gradient-hero opacity-5 pointer-events-none" />
        <div className="relative">
          <div className="text-center mb-8 sm:mb-12">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 bg-gradient-primary bg-clip-text text-transparent">
              Create Your Deck
            </h1>
            <p className="text-base sm:text-lg lg:text-xl text-muted-foreground max-w-2xl mx-auto px-4">
              Transform your study materials into powerful flashcards with AI
            </p>
          </div>
          <FlashcardGenerator />
        </div>
      </main>
    </div>
  );
};

export default Index;
