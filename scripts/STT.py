import torch
from transformers import pipeline

asr = pipeline(
    "automatic-speech-recognition",
    model="nvidia/parakeet-tdt-0.6b-v3",
    device="cuda:0",
    dtype=torch.float16,
)

result = asr("test.wav")
print(result["text"])
