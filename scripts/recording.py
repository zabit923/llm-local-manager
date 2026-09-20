import sounddevice as sd
import soundfile as sf

sample_rate = 16_000
duration_seconds = 5

print("Говори...")
audio = sd.rec(
    int(sample_rate * duration_seconds),
    samplerate=sample_rate,
    channels=1,
    dtype="float32",
)
sd.wait()

sf.write("test.wav", audio, sample_rate)
print("Создан test.wav")