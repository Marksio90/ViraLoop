/**
 * ViraLoop – Formularz generowania wideo
 *
 * Główny formularz w Studio do zlecania generacji wideo.
 * Integruje się z backendem przez React Query + Axios.
 * Walidacja: Zod + React Hook Form.
 */

"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Loader2, Sparkles, Wand2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import type { ZlecenieGeneracji, OdpowiedzGeneracji } from "@/types/wideo";

// Schemat walidacji Zod
const schematFormularza = z.object({
  opis: z
    .string()
    .min(10, "Opis musi mieć co najmniej 10 znaków")
    .max(2000, "Opis nie może przekraczać 2000 znaków"),
  model: z.string().default("kling-3.0"),
  rozdzielczosc: z.string().default("1080p"),
  czas_trwania: z.number().min(3).max(60).default(8),
  jezyk: z.string().default("pl"),
  styl: z.string().default("kinematograficzny"),
  audio: z.boolean().default(true),
});

type WartosciFormularza = z.infer<typeof schematFormularza>;

interface Props {
  onGenerowanieDodane: (id: string) => void;
}

// Dostępne modele z opisami
const MODELE = [
  {
    id: "kling-3.0",
    nazwa: "Kling 3.0",
    opis: "4K@60fps natywnie",
    tier: "tier1.5",
    cena: "~$0.07/s",
  },
  {
    id: "runway-gen-4.5",
    nazwa: "Runway Gen-4.5",
    opis: "#1 benchmark (Elo 1247)",
    tier: "tier1",
    cena: "$0.25/s",
  },
  {
    id: "veo-3.1",
    nazwa: "Google Veo 3.1",
    opis: "Najlepsza fizyka + audio",
    tier: "tier1",
    cena: "$0.40/s",
  },
  {
    id: "hailuo-02",
    nazwa: "MiniMax Hailuo 02",
    opis: "#2 globalnie, ekonomiczny",
    tier: "tier2",
    cena: "$0.05/s",
  },
  {
    id: "wan2.2",
    nazwa: "Wan2.2 (self-hosted)",
    opis: "Open-source MoE 14B",
    tier: "open",
    cena: "~$0.02/s",
  },
  {
    id: "hunyuan-1.5",
    nazwa: "HunyuanVideo 1.5",
    opis: "14GB VRAM, 96.4% jakości",
    tier: "open",
    cena: "~$0.015/s",
  },
] as const;

const STYLE = [
  "kinematograficzny",
  "animacja",
  "dokumentalny",
  "reklamowy",
  "vlog",
  "edukacyjny",
  "dramatyczny",
];

const JEZYKI = [
  { kod: "pl", nazwa: "Polski" },
  { kod: "en", nazwa: "Angielski" },
  { kod: "de", nazwa: "Niemiecki" },
  { kod: "fr", nazwa: "Francuski" },
  { kod: "es", nazwa: "Hiszpański" },
  { kod: "it", nazwa: "Włoski" },
  { kod: "zh", nazwa: "Chiński" },
  { kod: "ja", nazwa: "Japoński" },
];

export function FormularzGenerowania({ onGenerowanieDodane }: Props) {
  const { toast } = useToast();
  const [szacowanyCzas, setSzacowanyCzas] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<WartosciFormularza>({
    resolver: zodResolver(schematFormularza),
    defaultValues: {
      opis: "",
      model: "kling-3.0",
      rozdzielczosc: "1080p",
      czas_trwania: 8,
      jezyk: "pl",
      styl: "kinematograficzny",
      audio: true,
    },
  });

  const wartosciFormularza = watch();

  // Mutacja React Query do zlecenia generacji
  const mutacjaGenerowania = useMutation<OdpowiedzGeneracji, Error, ZlecenieGeneracji>({
    mutationFn: async (dane) => {
      const odpowiedz = await fetch("/api/v1/wideo/generuj", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dane),
      });

      if (!odpowiedz.ok) {
        const blad = await odpowiedz.json();
        throw new Error(blad.blad || "Błąd generowania wideo");
      }

      return odpowiedz.json();
    },
    onSuccess: (dane) => {
      toast({
        title: "Generowanie zlecone!",
        description: `Wideo będzie gotowe za ok. ${dane.szacowany_czas_sekund}s. ID: ${dane.id_zadania.slice(0, 8)}...`,
      });
      onGenerowanieDodane(dane.id_zadania);
    },
    onError: (blad) => {
      toast({
        title: "Błąd generowania",
        description: blad.message,
        variant: "destructive",
      });
    },
  });

  const onSubmit = (wartosci: WartosciFormularza) => {
    mutacjaGenerowania.mutate(wartosci as ZlecenieGeneracji);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">Utwórz nowe wideo</h2>
        <p className="text-sm text-muted-foreground">
          Opisz scenę, a AI wygeneruje wideo
        </p>
      </div>

      {/* Opis treści */}
      <div className="space-y-2">
        <Label htmlFor="opis">
          Opis treści wideo
          <span className="text-destructive ml-1">*</span>
        </Label>
        <Textarea
          id="opis"
          placeholder="Np. Dynamiczny wschód słońca nad Tatrami, kamera droni, epicka muzyka orkiestralna, 4K..."
          className="min-h-[120px] resize-none"
          {...register("opis")}
        />
        <div className="flex justify-between">
          {errors.opis ? (
            <p className="text-sm text-destructive">{errors.opis.message}</p>
          ) : (
            <span />
          )}
          <span className="text-xs text-muted-foreground">
            {wartosciFormularza.opis.length}/2000
          </span>
        </div>
      </div>

      {/* Wybór modelu */}
      <div className="space-y-2">
        <Label>Model generowania</Label>
        <div className="grid grid-cols-1 gap-2">
          {MODELE.map((model) => (
            <button
              key={model.id}
              type="button"
              onClick={() => setValue("model", model.id)}
              className={`flex items-center justify-between p-3 rounded-lg border text-left transition-colors ${
                wartosciFormularza.model === model.id
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground/50"
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{model.nazwa}</span>
                  <Badge
                    variant={model.tier === "tier1" ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {model.tier === "tier1"
                      ? "Premium"
                      : model.tier === "tier1.5"
                        ? "Przełomowy"
                        : model.tier === "tier2"
                          ? "Ekonomiczny"
                          : "Open-source"}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {model.opis}
                </p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                {model.cena}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Czas trwania */}
      <div className="space-y-3">
        <Label>
          Czas trwania:{" "}
          <span className="font-semibold">{wartosciFormularza.czas_trwania}s</span>
        </Label>
        <Slider
          min={3}
          max={60}
          step={1}
          value={[wartosciFormularza.czas_trwania]}
          onValueChange={([val]) => setValue("czas_trwania", val)}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>3s</span>
          <span>60s</span>
        </div>
      </div>

      {/* Rozdzielczość i styl */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Rozdzielczość</Label>
          <Select
            value={wartosciFormularza.rozdzielczosc}
            onValueChange={(val) => setValue("rozdzielczosc", val)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="480p">480p (Darmowy)</SelectItem>
              <SelectItem value="720p">720p</SelectItem>
              <SelectItem value="1080p">1080p</SelectItem>
              <SelectItem value="4K">4K (Kling 3.0)</SelectItem>
              <SelectItem value="4K@60fps">4K@60fps (Kling 3.0)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Język</Label>
          <Select
            value={wartosciFormularza.jezyk}
            onValueChange={(val) => setValue("jezyk", val)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {JEZYKI.map((j) => (
                <SelectItem key={j.kod} value={j.kod}>
                  {j.nazwa}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Styl wizualny */}
      <div className="space-y-2">
        <Label>Styl wizualny</Label>
        <div className="flex flex-wrap gap-2">
          {STYLE.map((styl) => (
            <button
              key={styl}
              type="button"
              onClick={() => setValue("styl", styl)}
              className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${
                wartosciFormularza.styl === styl
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border hover:border-muted-foreground/50"
              }`}
            >
              {styl}
            </button>
          ))}
        </div>
      </div>

      {/* Szacowany koszt */}
      {wartosciFormularza.model && wartosciFormularza.czas_trwania && (
        <div className="p-3 bg-muted/50 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Szacowany koszt:</span>
            <span className="font-mono font-semibold">
              {(() => {
                const kosztPerSekunde: Record<string, number> = {
                  "kling-3.0": 0.07,
                  "runway-gen-4.5": 0.25,
                  "veo-3.1": 0.40,
                  "hailuo-02": 0.05,
                  "wan2.2": 0.02,
                  "hunyuan-1.5": 0.015,
                };
                const koszt =
                  (kosztPerSekunde[wartosciFormularza.model] || 0.07) *
                  wartosciFormularza.czas_trwania;
                return `~$${koszt.toFixed(3)}`;
              })()}
            </span>
          </div>
        </div>
      )}

      {/* Przycisk generowania */}
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={mutacjaGenerowania.isPending}
      >
        {mutacjaGenerowania.isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Generowanie w toku...
          </>
        ) : (
          <>
            <Sparkles className="mr-2 h-4 w-4" />
            Wygeneruj wideo
          </>
        )}
      </Button>

      {/* Podpowiedź optymalizacja DSPy */}
      <p className="text-xs text-muted-foreground text-center">
        <Wand2 className="inline h-3 w-3 mr-1" />
        Prompty automatycznie optymalizowane przez DSPy MIPROv2
      </p>
    </form>
  );
}
