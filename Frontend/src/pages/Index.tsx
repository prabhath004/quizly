import FlashcardGenerator from "@/components/FlashcardGenerator";
import Header from "@/components/Header";

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={() => {}} />
      
      <main className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 bg-gradient-hero opacity-5 pointer-events-none" />
        <div className="relative">
          <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-primary bg-clip-text text-transparent">
              Create Your Deck
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
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
