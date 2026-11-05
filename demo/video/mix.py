"""Soundtrack from real CC0 recordings only (sfx/, see CREDITS.tsv): a looped synth bed under every scene and one
recording on each visible cue from out/events.json. A riser ends on its cue; everything else starts on it.
usage: python mix.py out/events.json out/audio.wav"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 48000
HERE = Path(__file__).parent
# scene sound type -> (recording, gain dB)
MAP = {'whoosh': ('whoosh', -10), 'drop': ('click', -6), 'kalimba': ('click', -12), 'tick': ('click', -4),
       'bell': ('ding', -8), 'harp': ('ping', -9), 'pluck': ('impact', -12), 'sub': ('impact', -4),
       'swell': ('riser', -10), 'clink': ('ding', -6), 'sparkle': ('impact', -8), 'typing': ('typing', -10)}


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, 'float32').reshape(-1, 2)


events = json.load(open(sys.argv[1]))
n = int(json.load(open(Path(sys.argv[1]).with_name('meta.json')))['duration'] * SR)
loop, bed, i = load(HERE / 'sfx' / 'bed.wav'), np.zeros((n, 2), 'float32'), 0
while i < n:  # loop the bed, fade in at the start and out over the last 4 s
    k = min(len(loop), n - i); bed[i:i + k] = loop[:k]; i += k
fade = np.ones(n, 'float32'); fade[:SR] = np.linspace(0, 1, SR); fade[-4 * SR:] = np.linspace(1, 0, 4 * SR)
out = bed * fade[:, None] * 10 ** (-20 / 20)
clips = {name: load(HERE / 'sfx' / f'{name}.wav') for name, _ in MAP.values()}
placed = 0
for e in events:
    if e['type'] not in MAP:
        continue
    name, db = MAP[e['type']]
    x = clips[name] * 10 ** ((db + e.get('gain', 0)) / 20)
    i = int(e['t'] * SR) - (len(x) if name == 'riser' else 0); i = max(i, 0); j = min(len(out), i + len(x))
    out[i:j] += x[:j - i]; placed += 1
out /= max(1.0, np.abs(out).max() / 0.89)
with wave.open(sys.argv[2], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((out * 32767).astype('<i2').tobytes())
print(json.dumps({'recordings': placed, 'seconds': round(len(out) / SR, 1)}))
