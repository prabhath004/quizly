import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { apiGet, apiPost } from "@/lib/api";

interface Flashcard {
  id: string;
  question: string;
  answer: string;
  correct_option_index: number;
}

const StudyTrueFalse = () => {
  const { deckId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [deck, setDeck] = useState<any>(null);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [score, setScore] = useState(0);

  useEffect(() => {
    fetchDeckData();
  }, [deckId]);

  const fetchDeckData = async () => {
    setIsLoading(true);
    try {
      const data = await apiGet<{ flashcards: any[]; deck: any }>(`/flashcards/deck/${deckId}`);
      setDeck(data.deck || { title: "True/False Quiz" });
      setFlashcards(data.flashcards || []);
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to load flashcards. Please try again.",
        variant: "destructive",
      });
      navigate("/");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptionSelect = async (optionIndex: number) => {
    if (showResult) return;
    setSelectedOption(optionIndex);
    setShowResult(true);
    
    // Evaluate answer with backend
    try {
      const result = await apiPost<{ is_correct: boolean; similarity_score: number; feedback: string }>(
        "/ai/evaluate-answer",
        {
          user_answer: optionIndex.toString(),
          correct_answer: currentCard.answer,
          question_type: "true_false",
          correct_option_index: currentCard.correct_option_index,
        }
      );
      
      if (result.is_correct) {
        setScore(score + 1);
        toast({
          title: "Correct!",
          description: result.feedback,
        });
      } else {
        toast({
          title: "Incorrect",
          description: result.feedback,
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error evaluating answer:", error);
    }
  };

  const handleNext = () => {
    if (currentIndex < flashcards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setSelectedOption(null);
      setShowResult(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setSelectedOption(null);
      setShowResult(false);
    }
  };

  const progress = ((currentIndex + 1) / flashcards.length) * 100;
  const currentCard = flashcards[currentIndex];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={() => navigate("/auth")} />
      
      <main className="container mx-auto py-8 px-4 sm:px-6 lg:px-8 max-w-4xl">
        <div className="mb-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-primary bg-clip-text text-transparent">
                {deck?.title}
              </h1>
              <p className="text-muted-foreground">True/False Practice</p>
            </div>
            <div className="flex gap-4">
              <Badge variant="secondary" className="text-lg">
                Score: {score}/{flashcards.length}
              </Badge>
              <Badge variant="outline" className="text-lg">
                {currentIndex + 1} / {flashcards.length}
              </Badge>
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {currentCard && (
          <Card className="mb-6 shadow-elegant animate-scale-in">
            <CardHeader>
              <CardTitle className="text-2xl">{currentCard.question}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {["True", "False"].map((option, index) => {
                  const isSelected = selectedOption === index;
                  const isCorrect = index === currentCard.correct_option_index;
                  const showCorrect = showResult && isCorrect;
                  const showIncorrect = showResult && isSelected && !isCorrect;

                  return (
                    <button
                      key={index}
                      onClick={() => handleOptionSelect(index)}
                      disabled={showResult}
                      className={cn(
                        "p-8 text-2xl font-bold rounded-lg border-2 transition-all duration-200",
                        "hover:border-primary hover:shadow-lg hover:scale-105",
                        isSelected && !showResult && "border-primary bg-primary/10 scale-105",
                        showCorrect && "border-green-500 bg-green-500/10",
                        showIncorrect && "border-red-500 bg-red-500/10",
                        !isSelected && !showCorrect && "border-border"
                      )}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <span>{option}</span>
                        {showCorrect && (
                          <CheckCircle2 className="h-6 w-6 text-green-600" />
                        )}
                        {showIncorrect && (
                          <XCircle className="h-6 w-6 text-red-600" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>

              {showResult && (
                <div className={cn(
                  "p-4 rounded-lg border-2 animate-fade-in",
                  selectedOption === currentCard.correct_option_index
                    ? "bg-green-500/10 border-green-500/20"
                    : "bg-red-500/10 border-red-500/20"
                )}>
                  <p className="font-semibold mb-2">
                    {selectedOption === currentCard.correct_option_index
                      ? "Correct!"
                      : "Incorrect"}
                  </p>
                  <p className="text-sm"><strong>Explanation:</strong> {currentCard.answer}</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="flex gap-4 justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentIndex === 0}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Previous
          </Button>

          {currentIndex === flashcards.length - 1 ? (
            <Button variant="success" onClick={() => navigate("/")}>
              Complete ({score}/{flashcards.length})
            </Button>
          ) : (
            <Button onClick={handleNext} disabled={!showResult}>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </main>
    </div>
  );
};

export default StudyTrueFalse;

