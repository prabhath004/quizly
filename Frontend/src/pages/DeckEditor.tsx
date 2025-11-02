import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Plus, Trash2, Save, ArrowLeft, Edit2 } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";

interface Flashcard {
  id?: string;
  question: string;
  answer: string;
  difficulty: string;
  question_type: string;
  mcq_options?: string[];
  correct_option_index?: number;
}

const DeckEditor = () => {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [isEditMode, setIsEditMode] = useState(!!deckId);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [deckTitle, setDeckTitle] = useState("");
  const [deckDescription, setDeckDescription] = useState("");
  const [flashcards, setFlashcards] = useState<Flashcard[]>([
    { question: "", answer: "", difficulty: "medium", question_type: "free_response" }
  ]);

  useEffect(() => {
    if (deckId) {
      fetchDeck();
    }
  }, [deckId]);

  const fetchDeck = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("auth_token");
      
      // Fetch deck info
      const deckResponse = await fetch(`http://localhost:8000/api/decks/${deckId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!deckResponse.ok) throw new Error("Failed to fetch deck");
      
      const deck = await deckResponse.json();
      setDeckTitle(deck.title);
      setDeckDescription(deck.description || "");
      
      // Fetch flashcards
      const flashcardsResponse = await fetch(`http://localhost:8000/api/flashcards/deck/${deckId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (flashcardsResponse.ok) {
        const data = await flashcardsResponse.json();
        setFlashcards(data.length > 0 ? data : [{ question: "", answer: "", difficulty: "medium", question_type: "free_response" }]);
      }
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to load deck. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const addFlashcard = () => {
    setFlashcards([...flashcards, { question: "", answer: "", difficulty: "medium", question_type: "free_response" }]);
  };

  const removeFlashcard = (index: number) => {
    setFlashcards(flashcards.filter((_, i) => i !== index));
  };

  const updateFlashcard = (index: number, field: string, value: any) => {
    const updated = [...flashcards];
    updated[index] = { ...updated[index], [field]: value };
    
    // Reset MCQ-specific fields if changing question type
    if (field === "question_type") {
      if (value !== "mcq") {
        updated[index].mcq_options = undefined;
        updated[index].correct_option_index = undefined;
      }
    }
    
    setFlashcards(updated);
  };

  const addMcqOption = (index: number) => {
    const updated = [...flashcards];
    if (!updated[index].mcq_options) {
      updated[index].mcq_options = ["", "", "", ""];
    } else {
      updated[index].mcq_options = [...updated[index].mcq_options, ""];
    }
    setFlashcards(updated);
  };

  const updateMcqOption = (flashcardIndex: number, optionIndex: number, value: string) => {
    const updated = [...flashcards];
    if (!updated[flashcardIndex].mcq_options) {
      updated[flashcardIndex].mcq_options = ["", "", "", ""];
    }
    updated[flashcardIndex].mcq_options![optionIndex] = value;
    setFlashcards(updated);
  };

  const removeMcqOption = (flashcardIndex: number, optionIndex: number) => {
    const updated = [...flashcards];
    if (updated[flashcardIndex].mcq_options) {
      updated[flashcardIndex].mcq_options = updated[flashcardIndex].mcq_options.filter((_, i) => i !== optionIndex);
    }
    setFlashcards(updated);
  };

  const handleSave = async () => {
    // Validation
    if (!deckTitle.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a deck title.",
        variant: "destructive",
      });
      return;
    }

    const validFlashcards = flashcards.filter(f => f.question.trim() && f.answer.trim());
    if (validFlashcards.length === 0) {
      toast({
        title: "Validation Error",
        description: "Please add at least one flashcard.",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    try {
      const token = localStorage.getItem("auth_token");
      let currentDeckId = deckId;

      // Create or update deck
      if (isEditMode && deckId) {
        // Update deck
        await fetch(`http://localhost:8000/api/decks/${deckId}`, {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: deckTitle,
            description: deckDescription,
          }),
        });
      } else {
        // Create new deck
        const deckResponse = await fetch("http://localhost:8000/api/decks", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: deckTitle,
            description: deckDescription,
          }),
        });

        if (!deckResponse.ok) throw new Error("Failed to create deck");
        
        const newDeck = await deckResponse.json();
        currentDeckId = newDeck.id;
      }

      // Save/update flashcards
      for (const flashcard of validFlashcards) {
        const flashcardData: any = {
          deck_id: currentDeckId,
          question: flashcard.question,
          answer: flashcard.answer,
          difficulty: flashcard.difficulty,
          question_type: flashcard.question_type,
        };

        if (flashcard.question_type === "mcq" && flashcard.mcq_options) {
          flashcardData.mcq_options = flashcard.mcq_options;
          flashcardData.correct_option_index = flashcard.correct_option_index || 0;
        }

        if (flashcard.id) {
          // Update existing
          await fetch(`http://localhost:8000/api/flashcards/${flashcard.id}`, {
            method: "PUT",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(flashcardData),
          });
        } else {
          // Create new
          await fetch("http://localhost:8000/api/flashcards", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify(flashcardData),
          });
        }
      }

      toast({
        title: "Success! 🎉",
        description: isEditMode ? "Deck updated successfully!" : "Deck created successfully!",
      });

      navigate("/decks");
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to save deck. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header isAuthenticated={true} onLogout={() => navigate("/auth")} />
        <div className="flex justify-center items-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={() => navigate("/auth")} />
      
      <main className="container mx-auto py-12 px-4 sm:px-6 lg:px-8 max-w-4xl">
        <Button
          variant="ghost"
          onClick={() => navigate("/decks")}
          className="mb-6"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Decks
        </Button>

        <Card className="shadow-elegant mb-6">
          <CardHeader>
            <CardTitle>{isEditMode ? "Edit Deck" : "Create New Deck"}</CardTitle>
            <CardDescription>
              {isEditMode ? "Update your deck and flashcards" : "Manually create a flashcard deck"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="deckTitle">Deck Title <span style={{ color: 'red' }}>*</span></Label>
              <Input
                id="deckTitle"
                value={deckTitle}
                onChange={(e) => setDeckTitle(e.target.value)}
                placeholder="e.g., Biology Chapter 5: Cell Structure"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="deckDescription">Description</Label>
              <Textarea
                id="deckDescription"
                value={deckDescription}
                onChange={(e) => setDeckDescription(e.target.value)}
                placeholder="Optional description for this deck"
                rows={2}
              />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Flashcards</h2>
            <Button onClick={addFlashcard}>
              <Plus className="mr-2 h-4 w-4" />
              Add Card
            </Button>
          </div>

          {flashcards.map((flashcard, index) => (
            <Card key={index} className="shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">Card {index + 1}</CardTitle>
                  <div className="flex gap-2">
                    {flashcards.length > 1 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFlashcard(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Difficulty</Label>
                    <Select
                      value={flashcard.difficulty}
                      onValueChange={(value) => updateFlashcard(index, "difficulty", value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Question Type</Label>
                    <Select
                      value={flashcard.question_type}
                      onValueChange={(value) => updateFlashcard(index, "question_type", value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="free_response">Free Response</SelectItem>
                        <SelectItem value="mcq">Multiple Choice</SelectItem>
                        <SelectItem value="true_false">True/False</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Question <span style={{ color: 'red' }}>*</span></Label>
                  <Textarea
                    value={flashcard.question}
                    onChange={(e) => updateFlashcard(index, "question", e.target.value)}
                    placeholder="Enter the question"
                    rows={2}
                  />
                </div>

                {flashcard.question_type === "mcq" && (
                  <div className="space-y-2">
                    <Label>Multiple Choice Options</Label>
                    {(flashcard.mcq_options || [""]).map((option, optIdx) => (
                      <div key={optIdx} className="flex gap-2">
                        <Input
                          value={option}
                          onChange={(e) => updateMcqOption(index, optIdx, e.target.value)}
                          placeholder={`Option ${optIdx + 1}`}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeMcqOption(index, optIdx)}
                          type="button"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    {(!flashcard.mcq_options || flashcard.mcq_options.length < 4) && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => addMcqOption(index)}
                        type="button"
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        Add Option
                      </Button>
                    )}
                    
                    <div className="space-y-2 mt-2">
                      <Label>Correct Answer Index</Label>
                      <Input
                        type="number"
                        min="0"
                        max={(flashcard.mcq_options || []).length - 1}
                        value={flashcard.correct_option_index || 0}
                        onChange={(e) => updateFlashcard(index, "correct_option_index", parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Answer <span style={{ color: 'red' }}>*</span></Label>
                  <Textarea
                    value={flashcard.answer}
                    onChange={(e) => updateFlashcard(index, "answer", e.target.value)}
                    placeholder="Enter the answer"
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex gap-4 justify-end mt-8 sticky bottom-4 bg-background p-4 rounded-lg border">
          <Button variant="outline" onClick={() => navigate("/decks")}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Deck
              </>
            )}
          </Button>
        </div>
      </main>
    </div>
  );
};

export default DeckEditor;

