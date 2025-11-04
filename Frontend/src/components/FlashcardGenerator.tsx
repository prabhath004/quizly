import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Lightbulb, Loader2, RotateCcw, CheckCircle2, Upload, FileText, Sparkles } from "lucide-react";
import { apiUpload } from "@/lib/api";

type DeckData = {
  deckId: string;
  deckTitle: string;
  numFlashcards: number;
  difficulty: string;
  questionType: string;
  savedCount?: number;
};

const FlashcardGenerator = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    deckTitle: "",
    numFlashcards: 10 as number | '',
    difficulty: "",
    questionType: "",
    textContent: "",
  });
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [deck, setDeck] = useState<DeckData | null>(null);
  const [error, setError] = useState(false);

  const isFormValid = 
    formData.deckTitle.trim().length >= 3 &&
    typeof formData.numFlashcards === 'number' &&
    formData.numFlashcards >= 1 &&
    formData.numFlashcards <= 50 &&
    formData.difficulty &&
    formData.questionType &&
    (formData.textContent.trim().length > 0 || file);

  const handleSubmit = async () => {
    if (!isFormValid) {
      toast({
        title: "Validation Error",
        description: "Please fill all required fields correctly.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    setError(false);
    setProgress(0);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 300);

    try {
      const formDataToSend = new FormData();
      const numCards = typeof formData.numFlashcards === 'number' ? formData.numFlashcards : 10;
      
      formDataToSend.append("deck_title", formData.deckTitle);
      formDataToSend.append("num_flashcards", numCards.toString());
      formDataToSend.append("difficulty_level", formData.difficulty);
      formDataToSend.append("question_type", formData.questionType);
      
      console.log("Sending to backend:", {
        deck_title: formData.deckTitle,
        num_flashcards: numCards,
        difficulty_level: formData.difficulty,
        question_type: formData.questionType,
      });
      
      if (formData.textContent.trim()) {
        formDataToSend.append("text_content", formData.textContent);
      }
      if (file) {
        formDataToSend.append("file", file);
      }

      const data = await apiUpload<any>("/ai/generate-flashcards", formDataToSend);

      clearInterval(progressInterval);
      setProgress(100);
      console.log("Backend response:", data);

      // Store deck data with correct structure
      const deckData: DeckData = {
        deckId: data.deck_id || "temp-id",
        deckTitle: formData.deckTitle,
        numFlashcards: data.saved_count || data.flashcards?.length || 0,
        difficulty: formData.difficulty,
        questionType: formData.questionType,
        savedCount: data.saved_count || data.flashcards?.length || 0,
      };

      console.log("Deck data:", deckData);
      setDeck(deckData);

      toast({
        title: "Success!",
        description: `Generated ${deckData.savedCount} flashcards${data.deck_id ? ' and saved to database' : ''}!`,
      });
    } catch (err: any) {
      clearInterval(progressInterval);
      setError(true);
      const errorMessage = err?.message || err?.detail || "Unable to generate flashcards. Please try again.";
      console.error("Flashcard generation error:", err);
      toast({
        title: "Generation Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      deckTitle: "",
      numFlashcards: 10,
      difficulty: "",
      questionType: "",
      textContent: "",
    });
    setFile(null);
    setDeck(null);
    setError(false);
    setProgress(0);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      toast({
        title: "File uploaded",
        description: selectedFile.name,
      });
    }
  };

  if (deck) {
    return (
      <div className="w-full max-w-2xl mx-auto px-4">
        <Card className="shadow-glow border-success/20">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="w-12 h-12 sm:w-16 sm:h-16 text-success" />
            </div>
            <CardTitle className="text-2xl sm:text-3xl">Deck Generated Successfully!</CardTitle>
            <CardDescription className="text-sm sm:text-base">Your AI-powered flashcards are ready</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 p-4 sm:p-6 bg-gradient-accent rounded-lg text-primary-foreground">
              <div>
                <p className="text-xs sm:text-sm opacity-90">Deck Title</p>
                <p className="font-semibold text-base sm:text-lg break-words">{deck.deckTitle}</p>
              </div>
              <div>
                <p className="text-xs sm:text-sm opacity-90">Flashcards</p>
                <p className="font-semibold text-base sm:text-lg">{deck.numFlashcards} cards</p>
              </div>
              <div>
                <p className="text-xs sm:text-sm opacity-90">Difficulty</p>
                <p className="font-semibold text-base sm:text-lg capitalize">{deck.difficulty}</p>
              </div>
              <div>
                <p className="text-xs sm:text-sm opacity-90">Question Type</p>
                <p className="font-semibold text-base sm:text-lg capitalize">{deck.questionType}</p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col sm:flex-row gap-3">
            <Button
              variant="hero"
              className="flex-1 w-full"
              size="lg"
              onClick={() => {
                let studyPath = `/study/free-response/${deck.deckId}`;
                if (deck.questionType === "mcq") {
                  studyPath = `/study/mcq/${deck.deckId}`;
                } else if (deck.questionType === "true_false") {
                  studyPath = `/study/true-false/${deck.deckId}`;
                }
                navigate(studyPath);
              }}
            >
              <Sparkles className="mr-2" />
              Start Studying
            </Button>
            <Button variant="outline" onClick={handleReset} size="lg" className="w-full sm:w-auto">
              Generate Another
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <Card className="shadow-lg border-border/50 backdrop-blur">
        <CardHeader className="space-y-1 pb-6 border-b">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-500 to-blue-600">
              <Lightbulb className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
            </div>
            <div>
              <CardTitle className="text-xl sm:text-2xl font-semibold">AI Flashcard Generator</CardTitle>
              <CardDescription className="text-xs sm:text-sm text-muted-foreground mt-1">Generate intelligent flashcards from your study materials</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5 sm:space-y-6 pt-6">
          {error && (
            <Alert variant="destructive" className="border-red-200 bg-red-50/50">
              <AlertDescription className="flex items-center justify-between">
                <span className="text-sm">Failed to generate deck. Please try again.</span>
                <Button variant="ghost" size="sm" onClick={() => setError(false)}>
                  <RotateCcw className="w-4 h-4" />
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="deckTitle" className="text-sm font-medium text-foreground">
                Deck Title <span className="text-red-500">*</span>
              </Label>
              <Input
                id="deckTitle"
                placeholder="e.g., Biology Chapter 5: Cell Structure"
                value={formData.deckTitle}
                onChange={(e) => setFormData({ ...formData, deckTitle: e.target.value })}
                disabled={loading}
                className="h-11 border-border/60 focus-visible:ring-purple-500 focus-visible:border-purple-500"
              />
              {formData.deckTitle.length > 0 && formData.deckTitle.length < 3 && (
                <p className="text-xs text-red-500 mt-1.5">Title must be at least 3 characters</p>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5">
              <div className="space-y-2">
                <Label htmlFor="numFlashcards" className="text-sm font-medium text-foreground">
                  Number of Cards <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="numFlashcards"
                  type="number"
                  min="1"
                  max="50"
                  value={formData.numFlashcards}
                  onChange={(e) => {
                    const value = e.target.value;
                    setFormData({ ...formData, numFlashcards: value === '' ? '' as any : parseInt(value) });
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '') {
                      setFormData({ ...formData, numFlashcards: 10 });
                    }
                  }}
                  disabled={loading}
                  className="h-11 border-border/60 focus-visible:ring-purple-500 focus-visible:border-purple-500"
                />
                {typeof formData.numFlashcards === 'number' && (formData.numFlashcards < 1 || formData.numFlashcards > 50) && (
                  <p className="text-xs text-red-500 mt-1.5">Must be between 1-50</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="difficulty" className="text-sm font-medium text-foreground">
                  Difficulty Level <span className="text-red-500">*</span>
                </Label>
                <Select
                  value={formData.difficulty}
                  onValueChange={(value) => setFormData({ ...formData, difficulty: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="difficulty" className="h-11 border-border/60 focus-visible:ring-purple-500">
                    <SelectValue placeholder="Select level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="easy">Easy</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="hard">Hard</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="questionType" className="text-sm font-medium text-foreground">
                Question Type <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.questionType}
                onValueChange={(value) => setFormData({ ...formData, questionType: value })}
                disabled={loading}
              >
                <SelectTrigger id="questionType" className="h-11 border-border/60 focus-visible:ring-purple-500">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mcq">Multiple Choice</SelectItem>
                  <SelectItem value="true_false">True/False</SelectItem>
                  <SelectItem value="free_response">Free Response</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="textContent" className="text-sm font-medium text-foreground">Text Content</Label>
              <Textarea
                id="textContent"
                placeholder="Paste your notes, text, or study material here..."
                value={formData.textContent}
                onChange={(e) => setFormData({ ...formData, textContent: e.target.value })}
                disabled={loading}
                rows={6}
                className="resize-none border-border/60 focus-visible:ring-purple-500 focus-visible:border-purple-500"
              />
              <p className="text-xs text-muted-foreground">
                {formData.textContent.length} characters
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="file" className="text-sm font-medium text-foreground">
                Optional: <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent font-semibold">Upload a File</span>
              </Label>
              <div className="flex items-center gap-3">
                <Input
                  id="file"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={handleFileChange}
                  disabled={loading}
                  className="hidden"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => document.getElementById("file")?.click()}
                  disabled={loading}
                  className="flex-1 h-11 border-border/60 hover:border-purple-500/50 hover:bg-purple-50/50"
                >
                  <Upload className="mr-2 w-4 h-4" />
                  <span className="truncate">{file ? file.name : "Choose File"}</span>
                </Button>
                {file && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => setFile(null)}
                    disabled={loading}
                    className="h-11 w-11 shrink-0"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5" />
                Supports PDF, DOC, DOCX, TXT
              </p>
            </div>

            <Alert className="border-blue-200 bg-blue-50/50">
              <AlertDescription className="text-xs sm:text-sm text-blue-900">
                <strong className="font-semibold">Note:</strong> Fill all required fields before generating your deck.
              </AlertDescription>
            </Alert>
          </div>

          {loading && (
            <div className="space-y-2.5 p-4 bg-purple-50/50 border border-purple-200 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="text-purple-900 font-medium">Generating flashcards...</span>
                <span className="font-semibold text-purple-700">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2 bg-purple-100" />
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col sm:flex-row gap-3 pt-6 border-t">
          <Button
            variant="hero"
            onClick={handleSubmit}
            disabled={!isFormValid || loading}
            className="flex-1 w-full h-11 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 shadow-md"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-4 w-4" />
                Generate Deck
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleReset}
            disabled={loading}
            size="lg"
            className="w-full sm:w-auto h-11 border-border/60"
          >
            Clear Form
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default FlashcardGenerator;
