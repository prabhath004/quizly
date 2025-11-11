import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { BookOpen, Play, Trash2, Loader2, Plus, Edit2, FolderPlus, Folder, FolderOpen, X, Move, MoreVertical, Headphones, ChevronUp, ChevronDown } from "lucide-react";
import Header from "@/components/Header";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import authService from "@/lib/auth";
import { Progress } from "@/components/ui/progress";
import PodcastPlayer from "@/components/PodcastPlayer";
// Temporarily disabled drag-and-drop due to React hook error
// import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, closestCenter } from "@dnd-kit/core";
// import { SortableContext, verticalListSortingStrategy, useSortable } from "@dnd-kit/sortable";
// import { CSS } from "@dnd-kit/utilities";

interface Deck {
  id: string;
  title: string;
  numFlashcards: number;
  difficulty: string;
  questionType: string;
  createdAt: string;
  folder_id?: string | null;
  order_index?: number | null;
  podcast_audio_url?: string | null;
}

interface Folder {
  id: string;
  name: string;
  deck_count: number;
  created_at: string;
}

const Decks = () => {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  // Drag-and-drop temporarily disabled
  // const [isDragging, setIsDragging] = useState(false);
  // const [activeId, setActiveId] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [creatingFolder, setCreatingFolder] = useState(false);
  
  // Global podcast player state
  const [currentPodcast, setCurrentPodcast] = useState<{ url: string; title: string; deckId: string; folderId: string | null } | null>(null);
  const [isPodcastPlayerOpen, setIsPodcastPlayerOpen] = useState(false);
  
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    // Check if user is authenticated
    if (!authService.isAuthenticated()) {
      navigate("/auth");
      return;
    }
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clean up expanded folders when decks or folders change
  useEffect(() => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      let changed = false;
      
      // Remove folders that don't exist or are empty
      newSet.forEach(folderId => {
        const folder = folders.find(f => f.id === folderId);
        if (!folder) {
          // Folder doesn't exist anymore
          newSet.delete(folderId);
          changed = true;
        } else {
          // Check if folder has any decks
          const folderDecks = decks.filter(d => d.folder_id === folderId);
          if (folderDecks.length === 0) {
            newSet.delete(folderId);
            changed = true;
          }
        }
      });
      
      return changed ? newSet : prev;
    });
  }, [decks, folders]);

  const fetchData = async () => {
    // Fetch decks and folders independently - if one fails, the other should still work
    fetchDecks().catch(err => {
      console.error("Error fetching decks:", err);
      setIsLoading(false);
    });
    
    fetchFolders().catch(err => {
      console.error("Error fetching folders:", err);
      // Folders are optional, so we just continue
    });
  };

  const fetchDecks = async () => {
    setIsLoading(true);
    try {
      const data = await apiGet<any[]>("/decks/my-decks");
      
      // Transform backend data to frontend format
      const transformedDecks = data.map((deck: any) => ({
        id: deck.id,
        title: deck.title,
        numFlashcards: deck.flashcard_count || 0,
        difficulty: deck.description?.includes("easy") ? "easy" : 
                   deck.description?.includes("hard") ? "hard" : "medium",
        questionType: deck.description?.includes("MCQ") ? "mcq" :
                     deck.description?.includes("TRUE_FALSE") ? "true_false" : "free_response",
        createdAt: deck.created_at,
        folder_id: deck.folder_id,
        order_index: deck.order_index,
        podcast_audio_url: deck.podcast_audio_url || null,
      }));
      
      setDecks(transformedDecks);
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

  const fetchFolders = async () => {
    try {
      const data = await apiGet<any[]>("/folders/my-folders");
      setFolders(data || []);
    } catch (err) {
      // Silently fail - folders feature is optional
      console.warn("Failed to fetch folders (this is OK if folders table doesn't exist yet):", err);
      setFolders([]);
    }
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      toast({
        title: "Invalid name",
        description: "Please enter a folder name.",
        variant: "destructive",
      });
      return;
    }

    setCreatingFolder(true);
    try {
      await apiPost("/folders", { name: newFolderName });

      await fetchFolders();
      setNewFolderName("");
      setIsCreatingFolder(false);
      
      toast({
        title: "Folder created",
        description: `Folder "${newFolderName}" has been created.`,
      });
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to create folder. Please try again.",
        variant: "destructive",
      });
    } finally {
      setCreatingFolder(false);
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    try {
      await apiDelete(`/folders/${folderId}`);

      toast({
        title: "Folder deleted",
        description: "The folder has been removed and its decks moved to root.",
      });

      await fetchData();
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to delete folder. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleStudyDeck = (deck: Deck) => {
    console.log("Navigating to study deck:", deck);
    let studyPath = `/study/free-response/${deck.id}`;
    if (deck.questionType === "mcq") {
      studyPath = `/study/mcq/${deck.id}`;
    } else if (deck.questionType === "true_false") {
      studyPath = `/study/true-false/${deck.id}`;
    }
    console.log("Study path:", studyPath);
    navigate(studyPath);
  };

  const handleDeleteDeck = async (deckId: string) => {
    try {
      await apiDelete(`/decks/${deckId}`);

      toast({
        title: "Deck deleted",
        description: "Your flashcard deck has been removed.",
      });

      await fetchDecks();
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to delete deck. Please try again.",
        variant: "destructive",
      });
    }
  };

  // Simplified move function without drag-and-drop
  const moveDeckToFolder = async (deckId: string, folderId: string | null) => {
    try {
      // Get the current deck to check its current folder
      const currentDeck = decks.find(d => d.id === deckId);
      const wasInFolder = currentDeck?.folder_id;
      
      await apiPut(`/decks/${deckId}`, { folder_id: folderId });

      const targetFolder = folderId ? folders.find(f => f.id === folderId) : null;
      toast({
        title: "Deck moved",
        description: targetFolder ? `Deck moved to "${targetFolder.name}"` : "Deck moved to root",
      });

      // Refresh both decks and folders to ensure UI is up to date
      // Fetch folders first, then decks (so decks can use updated folders)
      await fetchFolders();
      await fetchDecks();
    } catch (err: any) {
      console.error("Error moving deck:", err);
      toast({
        title: "Error",
        description: err?.message || "Failed to move deck. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReorderDecks = async (folderId: string, deckOrder: string[]) => {
    try {
      await apiPost(`/decks/folder/${folderId}/reorder`, { deck_order: deckOrder });
      await fetchDecks();
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to reorder decks. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleMoveDeckUp = async (deck: Deck) => {
    if (!deck.folder_id || deck.order_index === null || deck.order_index === undefined) return;
    
    const folderDecks = decks
      .filter(d => d.folder_id === deck.folder_id)
      .sort((a, b) => (a.order_index || 0) - (b.order_index || 0));
    
    const currentIndex = folderDecks.findIndex(d => d.id === deck.id);
    if (currentIndex <= 0) return; // Already at top
    
    // Swap with previous deck
    const newOrder = folderDecks.map(d => d.id);
    [newOrder[currentIndex], newOrder[currentIndex - 1]] = [newOrder[currentIndex - 1], newOrder[currentIndex]];
    
    await handleReorderDecks(deck.folder_id, newOrder);
  };

  const handleMoveDeckDown = async (deck: Deck) => {
    if (!deck.folder_id || deck.order_index === null || deck.order_index === undefined) return;
    
    const folderDecks = decks
      .filter(d => d.folder_id === deck.folder_id)
      .sort((a, b) => (a.order_index || 0) - (b.order_index || 0));
    
    const currentIndex = folderDecks.findIndex(d => d.id === deck.id);
    if (currentIndex < 0 || currentIndex >= folderDecks.length - 1) return; // Already at bottom
    
    // Swap with next deck
    const newOrder = folderDecks.map(d => d.id);
    [newOrder[currentIndex], newOrder[currentIndex + 1]] = [newOrder[currentIndex + 1], newOrder[currentIndex]];
    
    await handleReorderDecks(deck.folder_id, newOrder);
  };

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
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

  const rootDecks = decks.filter(deck => !deck.folder_id);

  // Global podcast player handlers
  const handlePlayPodcast = (deck: Deck) => {
    if (!deck.podcast_audio_url) return;
    
    // Stop any currently playing podcast
    setCurrentPodcast({
      url: deck.podcast_audio_url,
      title: deck.title,
      deckId: deck.id,
      folderId: deck.folder_id || null,
    });
    setIsPodcastPlayerOpen(true);
  };

  const handleStopPodcast = () => {
    setCurrentPodcast(null);
    setIsPodcastPlayerOpen(false);
  };

  const DeckCard = ({ deck, folders }: { deck: Deck; folders: Folder[] }) => {

    return (
      <div>
        <Card className="hover:shadow-elegant transition-shadow duration-200">
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
              {deck.podcast_audio_url && (
                <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/20 dark:text-purple-300">
                  <Headphones className="mr-1 h-3 w-3" />
                  Podcast
                </Badge>
              )}
            </div>

            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={() => handleStudyDeck(deck)}
              >
                <Play className="mr-2 h-4 w-4" />
                Study
              </Button>
              {deck.podcast_audio_url && (
                <Button
                  variant={currentPodcast?.url === deck.podcast_audio_url ? "default" : "outline"}
                  size="icon"
                  onClick={() => handlePlayPodcast(deck)}
                  title="Play Podcast"
                >
                  <Headphones className="h-4 w-4" />
                </Button>
              )}
              <Button
                variant="outline"
                size="icon"
                onClick={() => navigate(`/decks/${deck.id}/edit`)}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => moveDeckToFolder(deck.id, null)}>
                    <Folder className="mr-2 h-4 w-4" />
                    Move to Root
                  </DropdownMenuItem>
                  {folders.length > 0 && (
                    <>
                      {folders.map((folder) => (
                        <DropdownMenuItem 
                          key={folder.id}
                          onClick={() => moveDeckToFolder(deck.id, folder.id)}
                        >
                          <FolderOpen className="mr-2 h-4 w-4" />
                          Move to {folder.name}
                        </DropdownMenuItem>
                      ))}
                    </>
                  )}
                  <DropdownMenuItem 
                    onClick={() => handleDeleteDeck(deck.id)}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const FolderItem = ({ folder }: { folder: Folder }) => {
    const isExpanded = expandedFolders.has(folder.id);
    const folderDecks = decks
      .filter(deck => deck.folder_id === folder.id)
      .sort((a, b) => (a.order_index || 0) - (b.order_index || 0));

    return (
      <div>
        <Card className="mb-4">
          <CardHeader className="cursor-pointer" onClick={() => toggleFolder(folder.id)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isExpanded ? (
                  <FolderOpen className="h-5 w-5 text-blue-500" />
                ) : (
                  <Folder className="h-5 w-5 text-blue-500" />
                )}
                <div>
                  <CardTitle className="text-lg">{folder.name}</CardTitle>
                  <CardDescription>{folderDecks.length} decks</CardDescription>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteFolder(folder.id);
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          {isExpanded && folderDecks.length > 0 && (
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {folderDecks.map((deck, index) => (
                  <div key={deck.id} className="relative">
                    <DeckCard deck={deck} folders={folders} />
                    {/* Reorder buttons for decks in folders */}
                    <div className="absolute top-2 right-2 flex flex-col gap-1 bg-background/80 backdrop-blur-sm rounded-md p-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMoveDeckUp(deck);
                        }}
                        disabled={index === 0}
                        title="Move up"
                      >
                        <ChevronUp className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMoveDeckDown(deck);
                        }}
                        disabled={index === folderDecks.length - 1}
                        title="Move down"
                      >
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <Header isAuthenticated={true} onLogout={() => navigate("/auth")} />
      
      <main className="container mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2 bg-gradient-primary bg-clip-text text-transparent">
                My Flashcard Decks
              </h1>
              <p className="text-muted-foreground">
                Review and study your AI-generated flashcard collections
              </p>
            </div>
            <div className="flex gap-2">
              <Dialog open={isCreatingFolder} onOpenChange={setIsCreatingFolder}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="gap-2">
                    <FolderPlus className="h-4 w-4" />
                    New Folder
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Folder</DialogTitle>
                    <DialogDescription>
                      Organize your decks into folders for better management.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <Input
                      placeholder="Folder name"
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleCreateFolder();
                        }
                      }}
                    />
                    <Button onClick={handleCreateFolder} disabled={creatingFolder} className="w-full">
                      {creatingFolder ? "Creating..." : "Create Folder"}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
              <Button onClick={() => navigate("/decks/new")}>
                <Plus className="mr-2 h-4 w-4" />
                Create Deck
              </Button>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <div>
            {folders.length > 0 && (
              <div>
                {folders.map((folder) => (
                  <FolderItem key={folder.id} folder={folder} />
                ))}
              </div>
            )}

            {rootDecks.length > 0 && (
              <div className="mb-4">
                <h2 className="text-2xl font-semibold mb-4">Unorganized Decks</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {rootDecks.map((deck) => (
                    <DeckCard key={deck.id} deck={deck} folders={folders} />
                  ))}
                </div>
              </div>
            )}

            {folders.length === 0 && rootDecks.length === 0 && (
              <Card className="relative text-center py-12 overflow-hidden rounded-2xl shadow-md bg-gradient-to-br from-white via-pink-50 to-purple-100">
                <CardContent className="space-y-4">
                  <BookOpen className="h-16 w-16 mx-auto text-muted-foreground opacity-50" />
                  <div>
                    <h3 className="text-xl font-semibold mb-2">No decks yet</h3>
                    <p className="text-muted-foreground mb-6">
                      Let's get started by creating your first flashcard deck
                    </p>
                    <div className="flex gap-3 justify-center">
                      <Button variant="hero" onClick={() => navigate("/decks/new")}>
                        Create Manual Deck
                      </Button>
                      <Button variant="outline" onClick={() => navigate("/")}>
                        Generate with AI
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </main>
      
      {/* Global Podcast Player */}
      <PodcastPlayer
        isOpen={isPodcastPlayerOpen}
        onClose={() => setIsPodcastPlayerOpen(false)}
        podcastUrl={currentPodcast?.url || null}
        deckTitle={currentPodcast?.title || ""}
        deckId={currentPodcast?.deckId || null}
        folderId={currentPodcast?.folderId || null}
        onStop={handleStopPodcast}
        onNextPodcast={(nextPodcast) => {
          setCurrentPodcast(nextPodcast);
          setIsPodcastPlayerOpen(true);
        }}
      />
    </div>
  );
};

export default Decks;

