import { EDNAi } from "../../packages/js/src/index.js";

const ai = new EDNAi({
  baseUrl: "https://ednai-6znf.onrender.com",
});

// Browser example: upload/record a Blob first.
const input = document.querySelector<HTMLInputElement>("#audio")!;
const file = input.files?.[0];
if (!file) throw new Error("Choose an audio file first.");

const transcript = await ai.transcribe(file, "yoruba", file.name);
console.log(transcript.text, transcript.model);

// Device TTS is supplementary and is not an N-ATLaS model.
await ai.speak(transcript.text, "yoruba");
