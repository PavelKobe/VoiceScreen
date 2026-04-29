import { useEffect, useRef, useState } from "react";
import { Loader2, Pause, Play } from "lucide-react";
import WaveSurfer from "wavesurfer.js";
import { Button } from "@/components/ui/button";

interface Props {
  src: string;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0:00";
  const mm = Math.floor(seconds / 60);
  const ss = Math.floor(seconds % 60);
  return `${mm}:${String(ss).padStart(2, "0")}`;
}

/**
 * Аудиоплеер с визуализацией звуковой волны через wavesurfer.js.
 * Кликом по волне — переход к моменту разговора.
 */
export function WaveformPlayer({ src }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!containerRef.current) return;

    // Гибридный режим: проигрывание звука через стандартный <audio>
    // (та же аудио-цепочка, что в обычном <audio controls>), визуализация —
    // через wavesurfer. Это убирает «голую» Web Audio передачу и оставляет
    // привычное звучание; нормализация выключена, чтобы тихие участки
    // (фоновый шум) не подкручивались.
    const audio = document.createElement("audio");
    audio.src = src;
    audio.preload = "auto";

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#cbd5e1", // slate-300
      progressColor: "#2563eb", // blue-600
      cursorColor: "#1e40af", // blue-800
      cursorWidth: 2,
      barWidth: 2,
      barRadius: 2,
      barGap: 2,
      height: 64,
      normalize: false,
      media: audio,
    });

    wavesurferRef.current = ws;

    ws.on("ready", () => {
      setIsReady(true);
      setDuration(ws.getDuration());
    });
    ws.on("play", () => setIsPlaying(true));
    ws.on("pause", () => setIsPlaying(false));
    ws.on("finish", () => setIsPlaying(false));
    ws.on("audioprocess", () => setCurrentTime(ws.getCurrentTime()));
    ws.on("seeking", () => setCurrentTime(ws.getCurrentTime()));

    return () => {
      ws.destroy();
      wavesurferRef.current = null;
    };
  }, [src]);

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="rounded-md bg-muted/40 px-3 py-2" />
      <div className="flex items-center justify-between gap-3 text-sm">
        <Button
          variant="outline"
          size="sm"
          onClick={() => wavesurferRef.current?.playPause()}
          disabled={!isReady}
        >
          {!isReady ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {isPlaying ? "Пауза" : "Воспроизвести"}
        </Button>
        <div className="font-mono tabular-nums text-muted-foreground">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>
      </div>
    </div>
  );
}
