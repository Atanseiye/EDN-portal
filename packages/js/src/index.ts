export const NATLAS_MODEL_ID = "NCAIR1/N-ATLaS" as const;
export type Role = "system" | "user" | "assistant";
export interface Message { role: Role; content: string; }
export interface GenerateOptions {
  model?: typeof NATLAS_MODEL_ID; messages?: Message[]; system?: string;
  temperature?: number; maxTokens?: number; jsonMode?: boolean; signal?: AbortSignal;
}
export interface Generation {
  text:string; model:string; provider?:string|null; finish_reason?:string|null;
  latency_ms?:number|null; usage:Record<string,unknown>; raw:Record<string,unknown>;
}
export interface EDNAiOptions { baseUrl:string; apiKey?:string; fetch?:typeof globalThis.fetch; }

export class EDNAi {
  private readonly baseUrl:string;
  private readonly apiKey?:string;
  private readonly fetchImpl:typeof globalThis.fetch;

  constructor(options:EDNAiOptions) {
    this.baseUrl=options.baseUrl.replace(/\/$/,"");
    this.apiKey=options.apiKey;
    this.fetchImpl=options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  async generate(prompt:string, options:GenerateOptions={}):Promise<Generation> {
    const messages:Message[]=[];
    if(options.system) messages.push({role:"system",content:options.system});
    if(options.messages?.length) messages.push(...options.messages);
    else messages.push({role:"user",content:prompt});
    const response=await this.fetchImpl(\`\${this.baseUrl}/v1/generate\`,{
      method:"POST",
      headers:{"content-type":"application/json",...(this.apiKey?{authorization:\`Bearer \${this.apiKey}\`}:{})},
      body:JSON.stringify({
        model:options.model??NATLAS_MODEL_ID,messages,
        temperature:options.temperature??0.2,max_tokens:options.maxTokens??512,
        json_mode:options.jsonMode??false
      }),
      signal:options.signal
    });
    if(!response.ok) {
      const detail=await response.text();
      throw new Error(\`EDNAi request failed (\${response.status}): \${detail}\`);
    }
    return response.json() as Promise<Generation>;
  }

  async models():Promise<Array<Record<string,unknown>>> {
    const response=await this.fetchImpl(\`\${this.baseUrl}/v1/models\`);
    if(!response.ok) throw new Error(\`EDNAi model discovery failed (\${response.status})\`);
    const body=await response.json() as {data:Array<Record<string,unknown>>};
    return body.data;
  }

  async health():Promise<Record<string,unknown>> {
    const response=await this.fetchImpl(\`\${this.baseUrl}/health\`);
    if(!response.ok) throw new Error(\`EDNAi health check failed (\${response.status})\`);
    return response.json() as Promise<Record<string,unknown>>;
  }
}
export default EDNAi;
