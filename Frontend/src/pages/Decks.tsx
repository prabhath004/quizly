import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BookOpen, Play, Trash2, Loader2 } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";

interface Deck {
  id: string;
  title: string;
  numFlashcards: number;
  difficulty: string;
  questionType: string;
  createdAt: string;
}

const Decks = () => {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    fetchDecks();
  }, []);

  const fetchDecks = async () => {
    setIsLoading(true);
    try {
      // Replace with your backend API call
      const token = localStorage.getItem("auth_token");
      const response = await fetch("/api/decks", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error("Failed to fetch decks");

      const data = await response.json();
      setDecks(data.decks || []);
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to load your decks. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleStudyDeck = (deck: Deck) => {
    const studyPath = deck.questionType === "mcq" 
      ? `/study/mcq/${deck.id}` 
      : `/study/free-response/${deck.id}`;
    navigate(studyPath);
  };

  const handleDeleteDeck = async (deckId: string) => {
    try {
      const token = localStorage.getItem("auth_token");
      const response = await fetch(`/api/decks/${deckId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error("Failed to delete deck");

      toast({
        title: "Deck deleted",
        description: "Your flashcard deck has been removed.",
      });

      setDecks(decks.filter((d) => d.id !== deckId));
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to delete deck. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case "easy":
        return "bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20";
      case "medium":
        return "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20";
      case "hard":
        return "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={() => navigate("/auth")} />
      
      <main className="container mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="mb-8 animate-fade-in">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-primary bg-clip-text text-transparent">
            My Flashcard Decks
          </h1>
          <p className="text-muted-foreground">
            Review and study your AI-generated flashcard collections
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : decks.length === 0 ? (
          <Card className="relative text-center py-12 animate-fade-in overflow-hidden rounded-2xl shadow-md bg-gradient-to-br from-white via-pink-50 to-purple-100 bg-[length:200%_200%] animate-gradient-loop">
            <CardContent className="space-y-4">
              <BookOpen className="h-16 w-16 mx-auto text-muted-foreground opacity-50" />
              <div>
                <h3 className="text-xl font-semibold mb-2">No decks yet</h3>
                <p className="text-muted-foreground mb-6">
                  Let's get started by creating your first flashcard deck
                </p>
                <Button variant="hero" onClick={() => navigate("/")}>
                  Generate Your First Deck
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {decks.map((deck, index) => (
              <Card
                key={deck.id}
                className="hover:shadow-elegant transition-all duration-200 hover:scale-[1.02] animate-fade-in"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <CardHeader>
                  <CardTitle className="text-xl">{deck.title}</CardTitle>
                  <CardDescription>
                    Created {new Date(deck.createdAt).toLocaleDateString()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {deck.numFlashcards} cards
                    </Badge>
                    <Badge className={getDifficultyColor(deck.difficulty)}>
                      {deck.difficulty}
                    </Badge>
                    <Badge variant="outline">
                      {deck.questionType === "mcq" ? "Multiple Choice" : "Free Response"}
                    </Badge>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      className="flex-1"
                      onClick={() => handleStudyDeck(deck)}
                    >
                      <Play className="mr-2 h-4 w-4" />
                      Study
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handleDeleteDeck(deck.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Decks;
