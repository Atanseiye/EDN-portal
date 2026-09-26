from ednai import EDNAi

ai = EDNAi(base_url="https://ednai-6znf.onrender.com")

result = ai.transcribe("sample.wav", language="yoruba")

print(result.text)
print(result.model)
