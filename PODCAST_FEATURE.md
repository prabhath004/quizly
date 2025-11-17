# Podcast Feature Documentation

## Overview

The Quizly podcast feature converts your flashcard decks into engaging, conversational podcast-style audio files. It uses OpenAI's text-to-speech API to create natural dialogue between two speakers (Questioner and Answerer) discussing your flashcards.

## How It Works

### Backend Flow (`app/decks.py`)

1. **Generate Podcast Endpoint**: `POST /decks/{deck_id}/generate-podcast`
   - Validates deck ownership and flashcard count
   - Creates a conversational script using OpenAI GPT
   - Converts script to audio using OpenAI TTS (two voices: Questioner and Answerer)
   - Adds background music/ambient tones
   - Uploads to Supabase Storage
   - Updates deck with `podcast_audio_url`

2. **Next Podcast Endpoint**: `GET /decks/{deck_id}/next-podcast`
   - Finds the next deck in the same folder with a podcast
   - Uses `order_index` to determine sequence
   - Enables autoplay of podcasts in folders

### Frontend Implementation

#### 1. **DeckEditor.tsx** - Generate Podcast
```typescript
// Location: Frontend/src/pages/DeckEditor.tsx

// Button to generate podcast (only visible when editing existing deck)
<Button onClick={handleGeneratePodcast}>
  Generate Podcast
</Button>

// Shows progress bar during generation
{generatingPodcast && (
  <Progress value={podcastProgress} />
)}
```

**Features:**
- Only available for saved decks with flashcards
- Shows progress indicator during generation
- Displays "Podcast Ready" badge when complete
- Allows regeneration of podcast

#### 2. **Decks.tsx** - Play Podcast
```typescript
// Location: Frontend/src/pages/Decks.tsx

// Podcast badge on deck card
{deck.podcast_audio_url && (
  <Badge>Podcast</Badge>
)}

// Play button
<Button onClick={() => handlePlayPodcast(deck)}>
  <Headphones />
</Button>
```

**Features:**
- Shows "Podcast" badge on decks with podcasts
- Play button opens podcast player
- Highlights currently playing podcast

#### 3. **PodcastPlayer.tsx** - Audio Player Component
```typescript
// Location: Frontend/src/components/PodcastPlayer.tsx
```

**Features:**
- Full audio controls (play/pause, seek, volume)
- Auto-plays when opened
- Auto-plays next podcast in folder when current ends
- Bottom sheet UI (slides up from bottom)
- Shows deck title and progress

## How to Use the Podcast Feature

### Step 1: Create/Edit a Deck
1. Go to **Deck Editor** (`/decks/{id}/edit`)
2. Add flashcards with questions and answers
3. Save the deck

### Step 2: Generate Podcast
1. In the Deck Editor, click **"Generate Podcast"** button
2. Wait for generation (shows progress bar)
3. You'll see a "Podcast Ready" badge when complete

### Step 3: Play Podcast
1. Go to **Decks page** (`/decks`)
2. Find your deck (it will have a purple "Podcast" badge)
3. Click the **headphones icon** button
4. Podcast player opens at bottom of screen
5. Audio auto-plays

### Step 4: Podcast Player Controls
- **Play/Pause**: Large button in center
- **Seek**: Drag the progress slider
- **Volume**: Adjust with volume slider
- **Auto-play Next**: If deck is in a folder, next podcast plays automatically
- **Close**: Click X or swipe down

## Features

### ✅ Current Features

1. **AI-Generated Scripts**
   - Conversational dialogue format
   - Natural back-and-forth between speakers
   - Includes all flashcards in deck

2. **Dual Voice System**
   - Questioner voice (asks questions)
   - Answerer voice (provides answers)
   - Natural conversation flow

3. **Background Music**
   - Ambient background music mixed in
   - Calm, study-friendly tones
   - Automatically loops to match podcast length

4. **Folder Autoplay**
   - If deck is in a folder, automatically plays next podcast
   - Uses `order_index` to determine sequence
   - Seamless listening experience

5. **Full Audio Controls**
   - Play/pause
   - Seek/scrub through timeline
   - Volume control
   - Time display (current/total)

6. **Visual Indicators**
   - "Podcast" badge on deck cards
   - "Podcast Ready" badge in editor
   - Highlighted play button when playing

### 🔧 Technical Details

**Backend:**
- Uses OpenAI GPT-4 to generate script
- Uses OpenAI TTS (text-to-speech) API
- Mixes audio with pydub library
- Stores in Supabase Storage bucket: `quizly-files`
- File path: `podcasts/{user_id}/{deck_id}.mp3`

**Frontend:**
- React component with HTML5 Audio API
- Bottom sheet UI (shadcn/ui Sheet component)
- Auto-play detection and handling
- Progress tracking and seeking

## API Endpoints

### Generate Podcast
```http
POST /decks/{deck_id}/generate-podcast
Authorization: Bearer {token}

Response:
{
  "message": "Podcast generated successfully",
  "podcast_audio_url": "https://...",
  "deck_id": "..."
}
```

### Get Next Podcast
```http
GET /decks/{deck_id}/next-podcast
Authorization: Bearer {token}

Response:
{
  "next_deck": {
    "id": "...",
    "title": "...",
    "podcast_audio_url": "https://...",
    "folder_id": "...",
    "order_index": 1,
    "flashcard_count": 10
  }
}
// or
{
  "next_deck": null
}
```

## Requirements

- Deck must be saved (have a deck_id)
- Deck must have at least one flashcard
- User must own the deck
- OpenAI API key must be configured
- Supabase Storage bucket `quizly-files` must exist

## UI Components Used

- `PodcastPlayer` - Main audio player component
- `Sheet` - Bottom sheet container (from shadcn/ui)
- `Button` - Play/pause and action buttons
- `Slider` - Progress and volume controls
- `Badge` - Podcast indicators
- `Progress` - Generation progress bar

## Future Enhancements (Potential)

- Download podcast as MP3
- Share podcast link
- Playback speed control
- Skip forward/backward buttons
- Playlist view for folder podcasts
- Podcast analytics (listening time, completion rate)


