import { EDNAi } from "../../packages/js/src/index.js";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com",
});

// Browser example: upload or record a Blob first.
const input = document.querySelector<HTMLInputElement>("#audio")!;
const file = input.files?.[0];
if (!file) throw new Error("Choose an audio file first.");

const result = await ai.voiceTurn(file, "yoruba", {
  filename: file.name,
  system: "Dáhùn ní Yorùbá tó rọrùn.",
});

console.log("Transcript:", result.transcription.text);
console.log("ASR model:", result.transcription.model);
console.log("N-ATLaS response:", result.generation.text);
