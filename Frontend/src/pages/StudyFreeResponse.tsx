import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, Mic, MicOff, Loader2, CheckCircle2 } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";

interface Flashcard {
  id: string;
  question: string;
  answer: string;
}

const StudyFreeResponse = () => {
  const { deckId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [deck, setDeck] = useState<any>(null);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [userAnswer, setUserAnswer] = useState("");
  const [showAnswer, setShowAnswer] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [recognition, setRecognition] = useState<any>(null);

  useEffect(() => {
    fetchDeckData();
    initializeSpeechRecognition();
  }, [deckId]);

  const fetchDeckData = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("auth_token");
      const response = await fetch(`http://localhost:8000/api/sessions/deck/${deckId}/flashcards`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to fetch deck");

      const data = await response.json();
      setDeck({ title: "Free Response Quiz" });
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

  const initializeSpeechRecognition = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setUserAnswer(transcript);
        toast({
          title: "Speech recognized",
          description: "Your answer has been transcribed.",
        });
      };

      recognitionInstance.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        toast({
          title: "Error",
          description: "Failed to recognize speech. Please try again.",
          variant: "destructive",
        });
        setIsRecording(false);
      };

      recognitionInstance.onend = () => {
        setIsRecording(false);
      };

      setRecognition(recognitionInstance);
    }
  };

  const toggleRecording = () => {
    if (!recognition) {
      toast({
        title: "Not supported",
        description: "Speech recognition is not supported in your browser.",
        variant: "destructive",
      });
      return;
    }

    if (isRecording) {
      recognition.stop();
      setIsRecording(false);
    } else {
      recognition.start();
      setIsRecording(true);
      toast({
        title: "Listening...",
        description: "Speak your answer clearly.",
      });
    }
  };

  const handleNext = () => {
    if (currentIndex < flashcards.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setUserAnswer("");
      setShowAnswer(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setUserAnswer("");
      setShowAnswer(false);
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
              <p className="text-muted-foreground">Free Response Practice</p>
            </div>
            <Badge variant="secondary" className="text-lg">
              {currentIndex + 1} / {flashcards.length}
            </Badge>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {currentCard && (
          <Card className="mb-6 shadow-elegant animate-scale-in">
            <CardHeader>
              <CardTitle className="text-2xl">{currentCard.question}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Your Answer:</label>
                  <Button
                    variant={isRecording ? "destructive" : "outline"}
                    size="sm"
                    onClick={toggleRecording}
                  >
                    {isRecording ? (
                      <>
                        <MicOff className="mr-2 h-4 w-4" />
                        Stop Recording
                      </>
                    ) : (
                      <>
                        <Mic className="mr-2 h-4 w-4" />
                        Use Microphone
                      </>
                    )}
                  </Button>
                </div>

                <Textarea
                  placeholder="Type or speak your answer..."
                  value={userAnswer}
                  onChange={(e) => setUserAnswer(e.target.value)}
                  className="min-h-[120px]"
                />
              </div>

              {!showAnswer ? (
                <Button
                  className="w-full"
                  onClick={async () => {
                    setShowAnswer(true);
                    // Evaluate with backend
                    try {
                      const token = localStorage.getItem("auth_token");
                      const response = await fetch("http://localhost:8000/api/ai/evaluate-answer", {
                        method: "POST",
                        headers: {
                          "Authorization": `Bearer ${token}`,
                          "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                          user_answer: userAnswer,
                          correct_answer: currentCard.answer,
                          question_type: "free_response",
                        }),
                      });

                      const result = await response.json();
                      
                      toast({
                        title: result.is_correct ? "Great Answer! 🎉" : "Keep Practicing!",
                        description: `Similarity: ${(result.similarity_score * 100).toFixed(0)}% - ${result.feedback}`,
                        variant: result.is_correct ? "default" : "destructive",
                      });
                    } catch (error) {
                      console.error("Error evaluating answer:", error);
                    }
                  }}
                  disabled={!userAnswer.trim()}
                >
                  Evaluate Answer
                </Button>
              ) : (
                <div className="space-y-4 p-4 bg-accent/50 rounded-lg border-2 border-primary/20 animate-fade-in">
                  <div className="flex items-center gap-2 text-primary">
                    <CheckCircle2 className="h-5 w-5" />
                    <span className="font-semibold">Model Answer:</span>
                  </div>
                  <p className="text-lg">{currentCard.answer}</p>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setShowAnswer(false);
                      setUserAnswer("");
                    }}
                  >
                    Try Again
                  </Button>
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
            <Button variant="success" onClick={() => navigate("/decks")}>
              Complete Study Session
            </Button>
          ) : (
            <Button onClick={handleNext}>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </main>
    </div>
  );
};

export default StudyFreeResponse;
