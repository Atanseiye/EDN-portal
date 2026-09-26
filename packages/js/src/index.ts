export const NATLAS_MODEL_ID = "NCAIR1/N-ATLaS" as const;

export type Role = "system" | "user" | "assistant";
export type SpeechLanguage = "english" | "yoruba" | "hausa" | "igbo";

export interface Transcription {
  text: string;
  model: string;
  language: SpeechLanguage;
  provider?: string | null;
  latency_ms?: number | null;
  raw: Record<string, unknown>;
}

export interface Message {
  role: Role;
  content: string;
}

export interface GenerateOptions {
  model?: typeof NATLAS_MODEL_ID;
  messages?: Message[];
  system?: string;
  temperature?: number;
  maxTokens?: number;
  jsonMode?: boolean;
  signal?: AbortSignal;
}

export interface Generation {
  text: string;
  model: string;
  provider?: string | null;
  finish_reason?: string | null;
  latency_ms?: number | null;
  usage: Record<string, unknown>;
  raw: Record<string, unknown>;
}

export interface DeviceTTSOptions {
  rate?: number;
  pitch?: number;
  voiceName?: string;
}

const DEVICE_TTS_LOCALES: Record<SpeechLanguage, string[]> = {
  english: ["en-NG", "en-GB", "en-US", "en"],
  yoruba: ["yo-NG", "yo"],
  hausa: ["ha-NG", "ha"],
  igbo: ["ig-NG", "ig"],
};

export function matchingDeviceVoices(language: SpeechLanguage): SpeechSynthesisVoice[] {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return [];
  const preferences = DEVICE_TTS_LOCALES[language];
  return window.speechSynthesis.getVoices()
    .map((voice) => {
      const lang = voice.lang.toLowerCase();
      let score = Number.POSITIVE_INFINITY;
      preferences.forEach((preference, index) => {
        const wanted = preference.toLowerCase();
        if (lang === wanted) score = Math.min(score, index * 10);
        else if (lang.startsWith(wanted + "-") || wanted.startsWith(lang + "-")) {
          score = Math.min(score, index * 10 + 1);
        }
      });
      return { voice, score };
    })
    .filter((item) => Number.isFinite(item.score))
    .sort((a, b) => a.score - b.score || a.voice.name.localeCompare(b.voice.name))
    .map((item) => item.voice);
}

export function speakWithDeviceVoice(
  text: string,
  language: SpeechLanguage,
  options: DeviceTTSOptions = {},
): Promise<void> {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    return Promise.reject(new Error("Device speech synthesis is not available in this environment."));
  }
  const voices = matchingDeviceVoices(language);
  const voice = options.voiceName
    ? voices.find((item) => item.name === options.voiceName)
    : voices[0];
  if (!voice) {
    return Promise.reject(
      new Error("No matching device voice is available for " + language + "."),
    );
  }

  return new Promise<void>((resolve, reject) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = options.rate ?? 1;
    utterance.pitch = options.pitch ?? 1;
    utterance.onend = () => resolve();
    utterance.onerror = (event) => reject(
      new Error("Device speech synthesis failed: " + event.error),
    );
    window.speechSynthesis.speak(utterance);
  });
}

export interface EDNAiOptions {
  baseUrl: string;
  apiKey?: string;
  fetch?: typeof globalThis.fetch;
}

export class EDNAi {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(options: EDNAiOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  async generate(prompt: string, options: GenerateOptions = {}): Promise<Generation> {
    const messages: Message[] = [];
    if (options.system) {
      messages.push({ role: "system", content: options.system });
    }
    if (options.messages?.length) {
      messages.push(...options.messages);
    } else {
      messages.push({ role: "user", content: prompt });
    }

    const headers: Record<string, string> = {"content-type": "application/json"};
    if (this.apiKey) headers.authorization = "Bearer " + this.apiKey;

    const response = await this.fetchImpl(this.baseUrl + "/v1/generate", {
      method: "POST",
      headers,
      body: JSON.stringify({
        model: options.model ?? NATLAS_MODEL_ID,
        messages,
        temperature: options.temperature ?? 0.2,
        max_tokens: options.maxTokens ?? 512,
        json_mode: options.jsonMode ?? false,
      }),
      signal: options.signal,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error("EDNAi request failed (" + response.status + "): " + detail);
    }
    return response.json() as Promise<Generation>;
  }

  async transcribe(audio: Blob, language: SpeechLanguage, filename = "audio.webm"): Promise<Transcription> {
    const headers: Record<string, string> = {};
    if (this.apiKey) headers.authorization = "Bearer " + this.apiKey;

    const form = new FormData();
    form.append("language", language);
    form.append("file", audio, filename);

    const response = await this.fetchImpl(this.baseUrl + "/v1/audio/transcriptions", {
      method: "POST",
      headers,
      body: form,
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error("EDNAi transcription failed (" + response.status + "): " + detail);
    }
    return response.json() as Promise<Transcription>;
  }

  async speechCapabilities(): Promise<Record<string, unknown>> {
    const response = await this.fetchImpl(this.baseUrl + "/v1/audio/capabilities");
    if (!response.ok) {
      throw new Error("EDNAi speech capability discovery failed (" + response.status + ")");
    }
    return response.json() as Promise<Record<string, unknown>>;
  }

  speak(
    text: string,
    language: SpeechLanguage,
    options: DeviceTTSOptions = {},
  ): Promise<void> {
    return speakWithDeviceVoice(text, language, options);
  }

  async models(): Promise<Array<Record<string, unknown>>> {
    const response = await this.fetchImpl(this.baseUrl + "/v1/models");
    if (!response.ok) {
      throw new Error("EDNAi model discovery failed (" + response.status + ")");
    }
    const body = await response.json() as {data: Array<Record<string, unknown>>};
    return body.data;
  }

  async health(): Promise<Record<string, unknown>> {
    const response = await this.fetchImpl(this.baseUrl + "/health");
    if (!response.ok) {
      throw new Error("EDNAi health check failed (" + response.status + ")");
    }
    return response.json() as Promise<Record<string, unknown>>;
  }
}

export default EDNAi;
