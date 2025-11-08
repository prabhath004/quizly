import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Play, Pause, Headphones, Volume2 } from "lucide-react";

interface PodcastPlayerProps {
  isOpen: boolean;
  onClose: () => void;
  podcastUrl: string | null;
  deckTitle: string;
  onStop: () => void;
}

const PodcastPlayer = ({ isOpen, onClose, podcastUrl, deckTitle, onStop }: PodcastPlayerProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!podcastUrl) return;

    // Clean up previous audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
    }

    // Create main audio element (background music is already mixed in by backend)
    const audio = new Audio(podcastUrl);
    audioRef.current = audio;

    const updateTime = () => {
      setCurrentTime(audio.currentTime);
      if (audio.duration) {
        setDuration(audio.duration);
      }
    };

    const updateDuration = () => {
      setDuration(audio.duration);
    };

    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('loadedmetadata', updateDuration);
    audio.addEventListener('durationchange', updateDuration);
    audio.addEventListener('ended', () => {
      setIsPlaying(false);
      setCurrentTime(0);
      onStop();
    });

    // Auto-play when player opens
    if (isOpen) {
      audio.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.error("Auto-play failed:", err);
        // Auto-play might be blocked by browser, that's okay
      });
    }

    return () => {
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('loadedmetadata', updateDuration);
      audio.removeEventListener('durationchange', updateDuration);
      audio.pause();
      audio.src = '';
    };
  }, [podcastUrl, isOpen, onStop]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSeek = (value: number[]) => {
    if (audioRef.current && duration) {
      const newTime = (value[0] / 100) * duration;
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (value: number[]) => {
    setVolume(value[0] / 100);
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!podcastUrl) return null;

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="bottom" className="h-auto p-4 sm:p-6 border-t-2" style={{ maxWidth: '100%' }}>
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Headphones className="h-6 w-6 text-primary" />
              <div>
                <h3 className="font-semibold text-xl">{deckTitle}</h3>
                <p className="text-sm text-muted-foreground">Podcast Player</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="h-8 w-8"
            >
              ×
            </Button>
          </div>

          {/* Main Controls - Wider Layout */}
          <div className="flex items-center gap-6">
            <Button
              variant="outline"
              size="icon"
              onClick={handlePlayPause}
              className="h-14 w-14 shrink-0"
            >
              {isPlaying ? (
                <Pause className="h-7 w-7" />
              ) : (
                <Play className="h-7 w-7" />
              )}
            </Button>

            <div className="flex-1 space-y-3 min-w-0">
              <Slider
                value={duration ? [(currentTime / duration) * 100] : [0]}
                onValueChange={handleSeek}
                max={100}
                step={0.1}
                className="w-full h-3"
              />
              <div className="flex justify-between text-sm font-medium">
                <span className="text-foreground">{formatTime(currentTime)}</span>
                <span className="text-muted-foreground">{formatTime(duration)}</span>
              </div>
            </div>

            {/* Volume Control */}
            <div className="flex items-center gap-3 w-40 shrink-0">
              <Volume2 className="h-5 w-5 text-muted-foreground" />
              <Slider
                value={[volume * 100]}
                onValueChange={handleVolumeChange}
                max={100}
                step={1}
                className="flex-1"
              />
              <span className="text-xs text-muted-foreground w-8 text-right">
                {Math.round(volume * 100)}%
              </span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default PodcastPlayer;

