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

export interface VoiceTurnOptions {
  filename?: string;
  system?: string;
  temperature?: number;
  maxTokens?: number;
  jsonMode?: boolean;
}

export interface VoiceTurnResult {
  transcription: Transcription;
  generation: Generation;
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

  async voiceTurn(
    audio: Blob,
    language: SpeechLanguage,
    options: VoiceTurnOptions = {},
  ): Promise<VoiceTurnResult> {
    const transcription = await this.transcribe(
      audio,
      language,
      options.filename ?? "audio.webm",
    );
    const generation = await this.generate(transcription.text, {
      system: options.system,
      temperature: options.temperature,
      maxTokens: options.maxTokens,
      jsonMode: options.jsonMode,
    });
    return { transcription, generation };
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
