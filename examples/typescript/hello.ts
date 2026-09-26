import { EDNAi } from "../../packages/js/src/index.js";

const ai = new EDNAi({ baseUrl: "http://localhost:8000" });
const result = await ai.generate("Ka bayyana API ga sabon developer da Hausa.");
console.log(result.text);
