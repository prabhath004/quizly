import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Plus, Trash2, Save, ArrowLeft, Edit2, Headphones, Mic, StopCircle, Play, X } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPut, apiPost, apiUpload } from "@/lib/api";
import { Progress } from "@/components/ui/progress";

interface Flashcard {
  id?: string;
  question: string;
  answer: string;
  difficulty: string;
  question_type: string;
  mcq_options?: string[];
  correct_option_index?: number;
  audio_url?: string | null;
}

const DeckEditor = () => {
  const { deckId } = useParams<{ deckId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [isEditMode, setIsEditMode] = useState(!!deckId);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generatingPodcast, setGeneratingPodcast] = useState(false);
  const [podcastProgress, setPodcastProgress] = useState(0);
  const [podcastAudioUrl, setPodcastAudioUrl] = useState<string | null>(null);
  
  const [deckTitle, setDeckTitle] = useState("");
  const [deckDescription, setDeckDescription] = useState("");
  const [flashcards, setFlashcards] = useState<Flashcard[]>([
    { question: "", answer: "", difficulty: "medium", question_type: "free_response" }
  ]);
  
  // Recording state per flashcard
  const [recordingStates, setRecordingStates] = useState<Record<number, {
    isRecording: boolean;
    mediaRecorder: MediaRecorder | null;
    audioChunks: Blob[];
    audioUrl: string | null;
    isPlaying: boolean;
    audioElement: HTMLAudioElement | null;
  }>>({});

  useEffect(() => {
    if (deckId) {
      fetchDeck();
    }
  }, [deckId]);

  const fetchDeck = async () => {
    setLoading(true);
    try {
      // Fetch deck info
      const deck = await apiGet<any>(`/decks/${deckId}`);
      setDeckTitle(deck.title);
      setDeckDescription(deck.description || "");
      setPodcastAudioUrl(deck.podcast_audio_url || null);

      // Fetch flashcards - the endpoint returns { flashcards: [...], deck: {...} }
      const data = await apiGet<any>(`/flashcards/deck/${deckId}`);
      const flashcardsData = data.flashcards || [];
      
      // Transform flashcards to match the expected format
      const formattedFlashcards = flashcardsData.map((card: any) => ({
        id: card.id,
        question: card.question || "",
        answer: card.answer || "",
        difficulty: card.difficulty || "medium",
        question_type: card.question_type || "free_response",
        mcq_options: card.mcq_options || card.options,
        correct_option_index: card.correct_option_index !== undefined ? card.correct_option_index : card.correctAnswer,
        audio_url: card.audio_url || null,
      }));
      
      setFlashcards(formattedFlashcards.length > 0 ? formattedFlashcards : [{ question: "", answer: "", difficulty: "medium", question_type: "free_response" }]);
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
    // Stop any ongoing recording for this flashcard
    const state = recordingStates[index];
    if (state?.isRecording && state.mediaRecorder) {
      state.mediaRecorder.stop();
    }
    if (state?.audioElement) {
      state.audioElement.pause();
      state.audioElement = null;
    }
    // Clean up recording state
    const newStates = { ...recordingStates };
    delete newStates[index];
    setRecordingStates(newStates);
    
    setFlashcards(flashcards.filter((_, i) => i !== index));
  };
  
  // Recording functions
  const startRecording = async (index: number) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 
                       MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : 
                       'audio/webm';
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      const audioChunks: Blob[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        setRecordingStates(prev => ({
          ...prev,
          [index]: {
            isRecording: false,
            mediaRecorder: null,
            audioChunks: [],
            audioUrl,
            isPlaying: false,
            audioElement: null,
          }
        }));
      };
      
      mediaRecorder.start(100); // Collect data every 100ms
      
      setRecordingStates(prev => ({
        ...prev,
        [index]: {
          isRecording: true,
          mediaRecorder,
          audioChunks: [],
          audioUrl: null,
          isPlaying: false,
          audioElement: null,
        }
      }));
    } catch (error) {
      console.error("Error starting recording:", error);
      toast({
        title: "Error",
        description: "Failed to start recording. Please check microphone permissions.",
        variant: "destructive",
      });
    }
  };
  
  const stopRecording = (index: number) => {
    const state = recordingStates[index];
    if (state?.mediaRecorder && state.isRecording) {
      state.mediaRecorder.stop();
    }
  };
  
  const uploadRecording = async (index: number, flashcardId: string) => {
    const state = recordingStates[index];
    if (!state?.audioUrl || !flashcardId) {
      toast({
        title: "Error",
        description: "No recording to upload. Please record audio first.",
        variant: "destructive",
      });
      return;
    }
    
    try {
      // Convert blob URL to blob
      const response = await fetch(state.audioUrl);
      const blob = await response.blob();
      
      // Create form data
      const formData = new FormData();
      const fileName = `recording-${flashcardId}.webm`;
      formData.append('audio_file', blob, fileName);
      
      // Upload using apiUpload (which handles FormData)
      const result = await apiUpload<any>(`/flashcards/${flashcardId}/upload-audio`, formData);
      
      // Update flashcard with audio URL
      const updated = [...flashcards];
      updated[index] = { ...updated[index], audio_url: result.audio_url };
      setFlashcards(updated);
      
      // Clean up recording state
      URL.revokeObjectURL(state.audioUrl);
      setRecordingStates(prev => {
        const newState = { ...prev };
        delete newState[index];
        return newState;
      });
      
      toast({
        title: "Success",
        description: "Voice memo uploaded successfully!",
      });
    } catch (error: any) {
      console.error("Error uploading recording:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to upload recording. Please try again.",
        variant: "destructive",
      });
    }
  };
  
  const deleteRecording = async (index: number, flashcardId: string) => {
    if (!flashcardId) return;
    
    try {
      await apiPut(`/flashcards/${flashcardId}`, { audio_url: "" });
      
      const updated = [...flashcards];
      updated[index] = { ...updated[index], audio_url: null };
      setFlashcards(updated);
      
      toast({
        title: "Success",
        description: "Voice memo deleted successfully!",
      });
    } catch (error: any) {
      console.error("Error deleting recording:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to delete recording. Please try again.",
        variant: "destructive",
      });
    }
  };
  
  const playRecording = (audioUrl: string, index: number) => {
    const state = recordingStates[index];
    if (state?.audioElement) {
      state.audioElement.pause();
      state.audioElement = null;
    }
    
    const audio = new Audio(audioUrl);
    audio.play();
    
    audio.onended = () => {
      setRecordingStates(prev => ({
        ...prev,
        [index]: {
          ...prev[index],
          isPlaying: false,
          audioElement: null,
        }
      }));
    };
    
    setRecordingStates(prev => ({
      ...prev,
      [index]: {
        ...prev[index],
        isPlaying: true,
        audioElement: audio,
      }
    }));
  };
  
  const stopPlayback = (index: number) => {
    const state = recordingStates[index];
    if (state?.audioElement) {
      state.audioElement.pause();
      state.audioElement.currentTime = 0;
      setRecordingStates(prev => ({
        ...prev,
        [index]: {
          ...prev[index],
          isPlaying: false,
          audioElement: null,
        }
      }));
    }
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
      let currentDeckId = deckId;

      // Create or update deck
      if (isEditMode && deckId) {
        // Update deck
        await apiPut(`/decks/${deckId}`, {
          title: deckTitle,
          description: deckDescription,
        });
      } else {
        // Create new deck
        const newDeck = await apiPost<any>("/decks", {
          title: deckTitle,
          description: deckDescription,
        });
        currentDeckId = newDeck.id;
      }

      // Save/update flashcards
      for (let i = 0; i < validFlashcards.length; i++) {
        const flashcard = validFlashcards[i];
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

        let savedFlashcard;
        if (flashcard.id) {
          // Update existing
          savedFlashcard = await apiPut(`/flashcards/${flashcard.id}`, flashcardData);
        } else {
          // Create new
          savedFlashcard = await apiPost("/flashcards", flashcardData);
        }
        
        // If there's a recording that hasn't been uploaded yet, upload it now
        // Find the recording state by matching the flashcard
        const flashcardIndex = flashcards.findIndex(f => 
          flashcard.id ? f.id === flashcard.id : 
          flashcard === f
        );
        const recordingState = recordingStates[flashcardIndex];
        if (recordingState?.audioUrl && savedFlashcard.id) {
          try {
            const response = await fetch(recordingState.audioUrl);
            const blob = await response.blob();
            const formData = new FormData();
            const fileName = `recording-${savedFlashcard.id}.webm`;
            formData.append('audio_file', blob, fileName);
            const uploadResult = await apiUpload<any>(`/flashcards/${savedFlashcard.id}/upload-audio`, formData);
            
            // Update the flashcard in state with the audio URL
            const updated = [...flashcards];
            if (flashcardIndex >= 0) {
              updated[flashcardIndex] = { ...updated[flashcardIndex], audio_url: uploadResult.audio_url };
            }
            setFlashcards(updated);
            
            // Clean up recording state
            URL.revokeObjectURL(recordingState.audioUrl);
            const newStates = { ...recordingStates };
            delete newStates[flashcardIndex];
            setRecordingStates(newStates);
          } catch (error) {
            console.error("Error uploading recording during save:", error);
            // Don't fail the entire save if recording upload fails
          }
        }
      }

      toast({
        title: "Success!",
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

  const handleGeneratePodcast = async () => {
    if (!deckId) {
      toast({
        title: "Error",
        description: "Please save the deck first before generating a podcast.",
        variant: "destructive",
      });
      return;
    }

    const validFlashcards = flashcards.filter(f => f.question.trim() && f.answer.trim());
    if (validFlashcards.length === 0) {
      toast({
        title: "Error",
        description: "Please add at least one flashcard before generating a podcast.",
        variant: "destructive",
      });
      return;
    }

    setGeneratingPodcast(true);
    setPodcastProgress(0);
    
    // Simulate progress updates (since we can't get real-time progress from the API)
    const progressInterval = setInterval(() => {
      setPodcastProgress((prev) => {
        if (prev >= 90) {
          return 90; // Don't go to 100% until request completes
        }
        return prev + 5;
      });
    }, 500);

    try {
      const result = await apiPost<any>(`/decks/${deckId}/generate-podcast`, {});
      clearInterval(progressInterval);
      setPodcastProgress(100);
      setPodcastAudioUrl(result.podcast_audio_url);
      
      setTimeout(() => {
        setPodcastProgress(0);
      }, 1000);
      
      toast({
        title: "Success!",
        description: "Podcast generated successfully! You can now play it from the decks page.",
      });
    } catch (err: any) {
      clearInterval(progressInterval);
      setPodcastProgress(0);
      toast({
        title: "Error",
        description: err.message || "Failed to generate podcast. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGeneratingPodcast(false);
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
      
      <main className="container mx-auto py-6 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-4xl">
        <Button
          variant="ghost"
          onClick={() => navigate("/decks")}
          className="mb-6"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Decks
        </Button>

        <Card className="shadow-elegant mb-4 sm:mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl sm:text-2xl">{isEditMode ? "Edit Deck" : "Create New Deck"}</CardTitle>
                <CardDescription className="text-sm sm:text-base">
                  {isEditMode ? "Update your deck and flashcards" : "Manually create a flashcard deck"}
                </CardDescription>
              </div>
              {isEditMode && deckId && (
                <div className="flex flex-col gap-2">
                  <div className="flex gap-2">
                    {podcastAudioUrl && (
                      <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-300">
                        <Headphones className="mr-1 h-3 w-3" />
                        Podcast Ready
                      </Badge>
                    )}
                    <Button
                      variant="outline"
                      onClick={handleGeneratePodcast}
                      disabled={generatingPodcast || flashcards.filter(f => f.question.trim() && f.answer.trim()).length === 0}
                    >
                      {generatingPodcast ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Headphones className="mr-2 h-4 w-4" />
                          {podcastAudioUrl ? "Regenerate Podcast" : "Generate Podcast"}
                        </>
                      )}
                    </Button>
                  </div>
                  {generatingPodcast && (
                    <div className="space-y-2">
                      <Progress value={podcastProgress} className="h-2" />
                      <p className="text-xs text-muted-foreground text-center">
                        Generating podcast... {podcastProgress}%
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
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

        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h2 className="text-xl sm:text-2xl font-bold">Flashcards</h2>
            <Button onClick={addFlashcard} className="w-full sm:w-auto">
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
                    <Label>
                      Multiple Choice Options (select the correct answer)
                      <span style={{ color: 'red' }}> *</span>
                    </Label>
                    {(flashcard.mcq_options || [""]).map((option, optIdx) => (
                      <div key={optIdx} className="flex gap-2">
                        <input
                          type="radio"
                          name={`correct-option-${index}`}
                          checked={flashcard.correct_option_index === optIdx}
                          onChange={() => updateFlashcard(index, "correct_option_index", optIdx)}
                          className="w-4 h-4 text-primary cursor-pointer"
                          title="Mark as correct answer"
                        />
                        <Input
                          value={option}
                          onChange={(e) => updateMcqOption(index, optIdx, e.target.value)}
                          placeholder={`Option ${optIdx + 1}`}
                          className="flex-1"
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
                  </div>
                )}

                <div className="space-y-2">
                  <Label>
                    {flashcard.question_type === "mcq" ? "Explanation" : "Answer"} 
                    <span style={{ color: 'red' }}>*</span>
                  </Label>
                  <Textarea
                    value={flashcard.answer}
                    onChange={(e) => updateFlashcard(index, "answer", e.target.value)}
                    placeholder={
                      flashcard.question_type === "mcq"
                        ? "Provide an explanation or additional context for the correct answer"
                        : "Enter the answer"
                    }
                    rows={3}
                  />
                </div>

                {/* Voice Mnemonic Recording Section */}
                <div className="space-y-2 border-t pt-4">
                  <Label>Voice Mnemonic (Optional)</Label>
                  <p className="text-xs text-muted-foreground mb-2">
                    Record yourself explaining this flashcard to help with retention
                  </p>
                  
                  <div className="flex flex-wrap gap-2">
                    {!flashcard.audio_url && !recordingStates[index]?.audioUrl && (
                      <>
                        {!recordingStates[index]?.isRecording ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => startRecording(index)}
                          >
                            <Mic className="mr-2 h-4 w-4" />
                            Record Voice Memo
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            onClick={() => stopRecording(index)}
                          >
                            <StopCircle className="mr-2 h-4 w-4" />
                            Stop Recording
                          </Button>
                        )}
                      </>
                    )}
                    
                    {recordingStates[index]?.audioUrl && !flashcard.audio_url && (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const state = recordingStates[index];
                            if (state?.audioUrl) {
                              playRecording(state.audioUrl, index);
                            }
                          }}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Play
                        </Button>
                        {recordingStates[index]?.isPlaying && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => stopPlayback(index)}
                          >
                            Stop
                          </Button>
                        )}
                        {flashcard.id && (
                          <Button
                            type="button"
                            variant="default"
                            size="sm"
                            onClick={() => uploadRecording(index, flashcard.id!)}
                          >
                            Save Recording
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const state = recordingStates[index];
                            if (state?.audioUrl) {
                              URL.revokeObjectURL(state.audioUrl);
                            }
                            setRecordingStates(prev => {
                              const newState = { ...prev };
                              delete newState[index];
                              return newState;
                            });
                          }}
                        >
                          <X className="mr-2 h-4 w-4" />
                          Discard
                        </Button>
                      </>
                    )}
                    
                    {flashcard.audio_url && (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => playRecording(flashcard.audio_url!, index)}
                        >
                          <Play className="mr-2 h-4 w-4" />
                          Play Recording
                        </Button>
                        {recordingStates[index]?.isPlaying && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => stopPlayback(index)}
                          >
                            Stop
                          </Button>
                        )}
                        {flashcard.id && (
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            onClick={() => deleteRecording(index, flashcard.id!)}
                          >
                            <X className="mr-2 h-4 w-4" />
                            Delete Recording
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                  
                  {recordingStates[index]?.isRecording && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="h-2 w-2 bg-red-500 rounded-full animate-pulse"></div>
                      Recording...
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-end mt-6 sm:mt-8 sticky bottom-4 bg-background p-3 sm:p-4 rounded-lg border">
          <Button variant="outline" onClick={() => navigate("/decks")} className="w-full sm:w-auto">
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving} className="w-full sm:w-auto">
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
