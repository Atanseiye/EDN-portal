from ednai import EDNAi

client = EDNAi(base_url="http://localhost:8000")
response = client.generate(
    "Ṣàlàyé ohun tí API jẹ́ fún developer tuntun.",
    system="Dáhùn ní Yorùbá tó rọrùn.",
    temperature=0.2,
)
print(response.text)
