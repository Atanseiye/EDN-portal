import { Container, getContainer } from "@cloudflare/containers";

interface Env {
  EDNAI_CONTAINER: DurableObjectNamespace<EDNAiContainer>;
  // JSON stored as a Worker secret; forwarded only into the server container.
  EDNAI_CONFIG: string;
}

export class EDNAiContainer extends Container<Env> {
  defaultPort = 8080;
  sleepAfter = "30m";
  enableInternet = true;

  constructor(ctx: ConstructorParameters<typeof Container<Env>>[0], bindings: Env) {
    super(ctx, bindings);
    let config: unknown;
    try {
      config = JSON.parse(bindings.EDNAI_CONFIG);
    } catch {
      throw new Error("EDNAI_CONFIG must contain valid JSON");
    }
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("EDNAI_CONFIG must be an object of string environment values");
    }
    const values = config as Record<string, unknown>;
    const allowed = /^(EDNAI_[A-Z0-9_]+|HF_TOKEN|APP_ENV|TRUSTED_HOSTS|CORS_ORIGINS)$/;
    for (const [key, value] of Object.entries(values)) {
      if (!allowed.test(key) || typeof value !== "string") {
        throw new Error("EDNAI_CONFIG contains an unsupported name or non-string value");
      }
    }
    if (values.APP_ENV !== "production") {
      throw new Error("Cloud deployment requires APP_ENV=production");
    }
    let database: URL;
    try {
      database = new URL(String(values.EDNAI_DATABASE_URL || ""));
    } catch {
      throw new Error("EDNAI_DATABASE_URL must be a valid PostgreSQL URL");
    }
    if (!["postgres:", "postgresql:"].includes(database.protocol) ||
        !["require", "verify-ca", "verify-full"].includes(database.searchParams.get("sslmode") || "")) {
      throw new Error("Cloud deployment requires PostgreSQL with TLS enabled");
    }
    this.envVars = values as Record<string, string>;
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // One stable instance preserves the application's in-process rate limiter.
    // All durable application state belongs in Neon, never container SQLite.
    const container = getContainer(env.EDNAI_CONTAINER, "ednai-primary");
    const headers = new Headers(request.headers);
    headers.set("x-forwarded-for", request.headers.get("cf-connecting-ip") || "unknown");
    headers.set("x-forwarded-proto", "https");
    return container.fetch(new Request(request, { headers }));
  }
};
