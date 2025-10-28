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

type DeckData = {
  deckTitle: string;
  numFlashcards: number;
  difficulty: string;
  questionType: string;
};

const FlashcardGenerator = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    deckTitle: "",
    numFlashcards: 10,
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
      formDataToSend.append("deckTitle", formData.deckTitle);
      formDataToSend.append("numFlashcards", formData.numFlashcards.toString());
      formDataToSend.append("difficulty", formData.difficulty);
      formDataToSend.append("questionType", formData.questionType);
      formDataToSend.append("textContent", formData.textContent);
      if (file) {
        formDataToSend.append("file", file);
      }

      const res = await fetch("/api/ai/generate-flashcards", {
        method: "POST",
        body: formDataToSend,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!res.ok) throw new Error("Failed to generate deck");

      const data = await res.json();
      setDeck(data);

      toast({
        title: "Success! 🎉",
        description: `Generated ${data.numFlashcards} flashcards for "${data.deckTitle}"`,
      });
    } catch (err) {
      clearInterval(progressInterval);
      setError(true);
      toast({
        title: "Generation Failed",
        description: "Unable to generate flashcards. Please try again.",
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
      <div className="w-full max-w-2xl mx-auto animate-fade-in">
        <Card className="shadow-glow border-success/20">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="w-16 h-16 text-success animate-scale-in" />
            </div>
            <CardTitle className="text-3xl">Deck Generated Successfully!</CardTitle>
            <CardDescription>Your AI-powered flashcards are ready</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-6 bg-gradient-accent rounded-lg text-primary-foreground">
              <div>
                <p className="text-sm opacity-90">Deck Title</p>
                <p className="font-semibold text-lg">{deck.deckTitle}</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Flashcards</p>
                <p className="font-semibold text-lg">{deck.numFlashcards} cards</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Difficulty</p>
                <p className="font-semibold text-lg capitalize">{deck.difficulty}</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Question Type</p>
                <p className="font-semibold text-lg capitalize">{deck.questionType}</p>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex gap-3">
            <Button 
              variant="hero" 
              className="flex-1" 
              size="lg"
              onClick={() => {
                const studyPath = deck.questionType === "mcq" 
                  ? `/study/mcq/${Date.now()}` 
                  : `/study/free-response/${Date.now()}`;
                navigate(studyPath);
              }}
            >
              <Sparkles className="mr-2" />
              View Deck
            </Button>
            <Button variant="outline" onClick={handleReset} size="lg">
              Generate Another
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <Card className="shadow-elegant">
        <CardHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-gradient-hero">
              <Lightbulb className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <CardTitle className="text-2xl">AI Flashcard Generator</CardTitle>
              <CardDescription>Generate intelligent flashcards from your notes or PDFs instantly</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {error && (
            <Alert variant="destructive" className="animate-fade-in">
              <AlertDescription className="flex items-center justify-between">
                <span>Failed to generate deck. Please try again.</span>
                <Button variant="ghost" size="sm" onClick={() => setError(false)}>
                  <RotateCcw className="w-4 h-4" />
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="deckTitle">Deck Title *</Label>
              <Input
                id="deckTitle"
                placeholder="e.g., Biology Chapter 5: Cell Structure"
                value={formData.deckTitle}
                onChange={(e) => setFormData({ ...formData, deckTitle: e.target.value })}
                disabled={loading}
                className="transition-all duration-200 focus:shadow-sm"
              />
              {formData.deckTitle.length > 0 && formData.deckTitle.length < 3 && (
                <p className="text-sm text-destructive">Title must be at least 3 characters</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="numFlashcards">Number of Cards *</Label>
                <Input
                  id="numFlashcards"
                  type="number"
                  min="1"
                  max="50"
                  value={formData.numFlashcards}
                  onChange={(e) => setFormData({ ...formData, numFlashcards: parseInt(e.target.value) || 1 })}
                  disabled={loading}
                  className="transition-all duration-200 focus:shadow-sm"
                />
                {(formData.numFlashcards < 1 || formData.numFlashcards > 50) && (
                  <p className="text-sm text-destructive">Must be between 1-50</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="difficulty">Difficulty Level *</Label>
                <Select
                  value={formData.difficulty}
                  onValueChange={(value) => setFormData({ ...formData, difficulty: value })}
                  disabled={loading}
                >
                  <SelectTrigger id="difficulty" className="transition-all duration-200 focus:shadow-sm">
                    <SelectValue placeholder="Select level" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beginner">Beginner</SelectItem>
                    <SelectItem value="intermediate">Intermediate</SelectItem>
                    <SelectItem value="advanced">Advanced</SelectItem>
                    <SelectItem value="expert">Expert</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="questionType">Question Type *</Label>
              <Select
                value={formData.questionType}
                onValueChange={(value) => setFormData({ ...formData, questionType: value })}
                disabled={loading}
              >
                <SelectTrigger id="questionType" className="transition-all duration-200 focus:shadow-sm">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="multiple-choice">Multiple Choice</SelectItem>
                  <SelectItem value="true-false">True/False</SelectItem>
                  <SelectItem value="fill-in-blank">Fill in the Blank</SelectItem>
                  <SelectItem value="short-answer">Short Answer</SelectItem>
                  <SelectItem value="mixed">Mixed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="textContent">Text Content *</Label>
              <Textarea
                id="textContent"
                placeholder="Paste your notes, text, or study material here..."
                value={formData.textContent}
                onChange={(e) => setFormData({ ...formData, textContent: e.target.value })}
                disabled={loading}
                rows={6}
                className="transition-all duration-200 focus:shadow-sm resize-none"
              />
              <p className="text-sm text-muted-foreground">
                {formData.textContent.length} characters
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="file">Or Upload a File (Optional)</Label>
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
                  variant="outline"
                  onClick={() => document.getElementById("file")?.click()}
                  disabled={loading}
                  className="flex-1"
                >
                  <Upload className="mr-2" />
                  {file ? file.name : "Choose File"}
                </Button>
                {file && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setFile(null)}
                    disabled={loading}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                )}
              </div>
              <p className="text-sm text-muted-foreground flex items-center gap-1">
                <FileText className="w-4 h-4" />
                Supports PDF, DOC, DOCX, TXT
              </p>
            </div>

            <Alert>
              <AlertDescription className="text-sm">
                💡 <strong>Tip:</strong> You must fill all fields before generating your deck.
              </AlertDescription>
            </Alert>
          </div>

          {loading && (
            <div className="space-y-2 animate-fade-in">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Generating flashcards...</span>
                <span className="font-medium">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
          )}
        </CardContent>

        <CardFooter className="flex gap-3">
          <Button
            variant="hero"
            onClick={handleSubmit}
            disabled={!isFormValid || loading}
            className="flex-1"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="mr-2" />
                Generate Deck
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={loading}
            size="lg"
          >
            Clear Form
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default FlashcardGenerator;
