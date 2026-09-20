import sounddevice as sd
import torch

torch.set_num_threads(4)

tts, _ = torch.hub.load(
    repo_or_dir="snakers4/silero-models",
    model="silero_tts",
    language="ru",
    speaker="v5_5_ru",
)

tts.to("cpu")

audio = tts.apply_tts(
    text="Здравствуйте. Горы гиро на Ермошкина, чем могу помочь?",
    speaker="xenia",
    sample_rate=24_000,
).numpy()

sd.play(audio, samplerate=24_000)
sd.wait()
