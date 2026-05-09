"""
PYTSMOD HARMONY ENGINE v2.1 - 3-Part Auto-Harmonizer using pytsmod versions
also has the harcoded outputs

Install the libraries:
    pip install pytsmod sounddevice numpy scipy

Run the file:
    python Pytsmod_Harmony_engine.py
"""

import sounddevice as sd
import numpy as np
import scipy.signal as scipy_signal
import threading
import queue
import sys
import time
import os

try:
    import pytsmod as tsm
    PSOLA_AVAILABLE = True
except ImportError:
    PSOLA_AVAILABLE = False

# -----------------------------------------------------------------
#  OUTPUT DEVICE OVERRIDE
#  Set this to the index number you want for output.
#  Leave as None to auto-detect (will default to Scarlett).
#
#  Common choices from your device list:
#    5  = Speakers (Realtek)         <- laptop built-in speakers
#    6  = Speakers (Focusrite)       <- headphones in Scarlett jack
#    8  = Sceptre L27                <- external monitor speakers
#    36 = Headphones (Realtek)       <- headphones in laptop jack
#
#  Change the number below and save, then run the script.
# -----------------------------------------------------------------

OUTPUT_DEVICE_INDEX = 5     # <-- change this number
INPUT_DEVICE_INDEX  = None  # <-- leave as None to auto-detect Scarlett

# -----------------------------------------------------------------
#  CONFIGURATION
#  Adjust BLOCK_SIZE to tune latency vs stability:
#    512   = ~12ms  (may crackle)
#    1024  = ~23ms  (good if running as admin)
#    2048  = ~46ms  (recommended)
#    4096  = ~93ms  (very stable, noticeable delay)
# -----------------------------------------------------------------

SAMPLE_RATE = 44100
BLOCK_SIZE  = 4096
CHANNELS    = 1
DTYPE       = "float32"
NUM_VOICES  = 3

DEFAULT_INTERVALS = [0, 4, 7]
DEFAULT_GAINS     = [0.85, 0.70, 0.70]

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

PRESETS = {
    "1": {"name": "Major Triad + low 3rd", "intervals": [0,  4,  7, -3]},
    "2": {"name": "Minor Triad + low 5th", "intervals": [0,  3,  7, -5]},
    "3": {"name": "Barbershop (close)",    "intervals": [0,  3,  7, 10]},
    "4": {"name": "Power / 5ths",          "intervals": [0,  7, 12, -5]},
    "5": {"name": "Octave Stack",          "intervals": [0, 12, -12,  7]},
    "6": {"name": "Tight Gospel",          "intervals": [0,  2,  4,  7]},
}

# -----------------------------------------------------------------
#  GLOBAL STATE
# -----------------------------------------------------------------

state = {
    "intervals":   list(DEFAULT_INTERVALS),
    "gains":       list(DEFAULT_GAINS),
    "key_index":   0,
    "running":     True,
    "bypass":      False,
    "input_dev":   None,
    "output_dev":  None,
    "input_name":  "unknown",
    "output_name": "unknown",
}

state_lock = threading.Lock()

# Each voice has its own dedicated input queue — no block stealing
voice_input_queues  = [queue.Queue(maxsize=6) for _ in range(NUM_VOICES)]
voice_output_queues = [queue.Queue(maxsize=6) for _ in range(NUM_VOICES)]
mix_output_q        = queue.Queue(maxsize=6)

# -----------------------------------------------------------------
#  PITCH SHIFTING  (WSOLA via pytsmod)
# -----------------------------------------------------------------

def match_length(audio, target_len):
    if len(audio) > target_len:
        return audio[:target_len]
    if len(audio) < target_len:
        pad = np.zeros(target_len - len(audio), dtype=np.float32)
        return np.concatenate([audio, pad])
    return audio


def pitch_shift_wsola(audio, semitones):
    """
    WSOLA pitch shift via pytsmod.
    WSOLA = Waveform Similarity Overlap Add.
    Designed for voice — smooth on sustained notes.
    Lower latency than phase vocoder, no warbling artifact.
    """
    if semitones == 0:
        return audio.copy()

    ratio = 2.0 ** (semitones / 12.0)

    # pytsmod expects float64 shape (1, N)
    x = audio.astype(np.float64)[np.newaxis, :]

    try:
        shifted = tsm.wsola(x, ratio)
        out = shifted[0].astype(np.float32)
    except Exception:
        return resample_shift(audio, semitones)

    return match_length(out, len(audio))


def resample_shift(audio, semitones):
    """
    Fallback pitch shift via resampling.
    Used if pytsmod is unavailable or throws an error.
    More artifacts on sustained notes but always works.
    """
    if semitones == 0:
        return audio.copy()
    ratio = 2.0 ** (semitones / 12.0)
    n_new = int(round(len(audio) / ratio))
    out   = scipy_signal.resample(audio, n_new).astype(np.float32)
    return match_length(out, len(audio))


def shift_audio(audio, semitones):
    if PSOLA_AVAILABLE:
        return pitch_shift_wsola(audio, semitones)
    return resample_shift(audio, semitones)


# -----------------------------------------------------------------
#  DEVICE DETECTION
# -----------------------------------------------------------------

def resolve_devices():
    """
    Resolves input and output device indices.
    Hardcoded overrides at the top of the file always win.
    """
    devices  = sd.query_devices()
    keywords = ["scarlett", "focusrite"]

    # --- Input ---
    if INPUT_DEVICE_INDEX is not None:
        in_idx = INPUT_DEVICE_INDEX
    else:
        scarlett_in = None
        for idx, dev in enumerate(devices):
            if any(k in dev["name"].lower() for k in keywords):
                if dev["max_input_channels"] > 0 and scarlett_in is None:
                    scarlett_in = idx
        in_idx = scarlett_in if scarlett_in is not None else sd.default.device[0]

    # --- Output ---
    if OUTPUT_DEVICE_INDEX is not None:
        out_idx = OUTPUT_DEVICE_INDEX
    else:
        scarlett_out = None
        for idx, dev in enumerate(devices):
            if any(k in dev["name"].lower() for k in keywords):
                if dev["max_output_channels"] > 0 and scarlett_out is None:
                    scarlett_out = idx
        out_idx = scarlett_out if scarlett_out is not None else sd.default.device[1]

    scarlett_found = any(
        any(k in dev["name"].lower() for k in keywords)
        for dev in devices
    )

    return {
        "input":          in_idx,
        "output":         out_idx,
        "input_name":     devices[in_idx]["name"],
        "output_name":    devices[out_idx]["name"],
        "scarlett_found": scarlett_found,
    }


def list_all_devices():
    print("")
    print("  All detected audio devices:")
    print("")
    for idx, dev in enumerate(sd.query_devices()):
        name = dev["name"]
        tag  = "  << SCARLETT" if any(k in name.lower() for k in ["scarlett", "focusrite"]) else ""
        line = "  [" + str(idx).rjust(2) + "]  " + name.ljust(45)
        line += "  in=" + str(dev["max_input_channels"])
        line += "  out=" + str(dev["max_output_channels"]) + tag
        print(line)
    print("")
    print("  To change output: edit OUTPUT_DEVICE_INDEX at the top of this file")
    print("  To change input : edit INPUT_DEVICE_INDEX  at the top of this file")
    print("")


# -----------------------------------------------------------------
#  VOICE WORKER THREADS
#  Each voice has its own input queue — receives a copy of every
#  block independently so voices never steal from each other
# -----------------------------------------------------------------

def voice_worker(voice_index):
    in_q  = voice_input_queues[voice_index]
    out_q = voice_output_queues[voice_index]

    while state["running"]:
        try:
            block = in_q.get(timeout=0.5)
        except queue.Empty:
            continue

        with state_lock:
            semitones = state["intervals"][voice_index]
            gain      = state["gains"][voice_index]
            bypass    = state["bypass"]

        if bypass:
            if voice_index == 0:
                result = block.copy()
            else:
                result = np.zeros(len(block), dtype=np.float32)
        else:
            result = shift_audio(block, semitones) * gain

        try:
            out_q.put(result, timeout=0.5)
        except queue.Full:
            pass


# -----------------------------------------------------------------
#  MIXER THREAD
# -----------------------------------------------------------------

def mixer_thread():
    while state["running"]:
        voices    = []
        timed_out = False

        for out_q in voice_output_queues:
            try:
                block = out_q.get(timeout=0.5)
                voices.append(block)
            except queue.Empty:
                timed_out = True
                break

        if timed_out or len(voices) != NUM_VOICES:
            continue

        n   = len(voices[0])
        mix = np.zeros(n, dtype=np.float32)
        for v in voices:
            mix += match_length(v, n)

        # Soft clip to prevent harsh digital distortion
        mix = np.tanh(mix)

        try:
            mix_output_q.put(mix, timeout=0.5)
        except queue.Full:
            pass


# -----------------------------------------------------------------
#  OUTPUT THREAD
# -----------------------------------------------------------------

def output_thread():
    while state["running"]:
        with state_lock:
            out_dev = state["output_dev"]
        if out_dev is None:
            time.sleep(0.1)
            continue
        try:
            with sd.OutputStream(
                device=out_dev,
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
            ) as out_stream:
                while state["running"]:
                    try:
                        block = mix_output_q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    out_stream.write(block.reshape(-1, 1))
        except sd.PortAudioError as e:
            print("  Output stream error: " + str(e))
            time.sleep(1.0)


# -----------------------------------------------------------------
#  INPUT CALLBACK
#  Fans out a fresh copy of every block to all 4 voice queues
# -----------------------------------------------------------------

def input_callback(indata, frames, time_info, status):
    block = indata[:, 0].copy()
    for i in range(NUM_VOICES):
        try:
            voice_input_queues[i].put_nowait(block.copy())
        except queue.Full:
            pass


# -----------------------------------------------------------------
#  TERMINAL UI
# -----------------------------------------------------------------

INTERVAL_NAMES = {
    -12: "Oct-", -10: "m7-",  -9: "M6-",  -8: "m6-",  -7: "P5-",
     -5: "P4-",   -4: "M3-",  -3: "m3-",  -2: "M2-",  -1: "m2-",
      0: "Dry",
      1: "m2+",    2: "M2+",   3: "m3+",   4: "M3+",   5: "P4+",
      7: "P5+",    8: "m6+",   9: "M6+",  10: "m7+",  12: "Oct+",
}


def interval_label(n):
    return INTERVAL_NAMES.get(n, str(n) + "st")


def semitone_str(n):
    return ("+" + str(n)) if n >= 0 else str(n)


def draw_ui():
    with state_lock:
        ivs    = list(state["intervals"])
        gains  = list(state["gains"])
        key    = KEYS[state["key_index"]]
        bypass = state["bypass"]
        in_nm  = state["input_name"]
        out_nm = state["output_name"]

    algo   = "WSOLA / PSOLA (voice optimised)" if PSOLA_AVAILABLE else "Resample fallback - run: pip install pytsmod"
    ms     = str(round((BLOCK_SIZE / SAMPLE_RATE) * 1000))
    status = "[BYPASS - dry only]" if bypass else "[ACTIVE - harmonies on]"
    out_override = "HARDCODED index " + str(OUTPUT_DEVICE_INDEX) if OUTPUT_DEVICE_INDEX is not None else "auto"
    in_override  = "HARDCODED index " + str(INPUT_DEVICE_INDEX)  if INPUT_DEVICE_INDEX  is not None else "auto (Scarlett)"

    os.system("cls")
    print("  +--------------------------------------------------------+")
    print("  |      PYTSMOD HARMONY ENGINE  v2.1  -  4-Part Harmony   |")
    print("  |      WSOLA  |  Parallel voices  |  Scarlett Solo       |")
    print("  +--------------------------------------------------------+")
    print("")
    print("  Input   : " + in_nm + "  [" + in_override + "]")
    print("  Output  : " + out_nm + "  [" + out_override + "]")
    print("  Engine  : " + algo)
    print("  Latency : ~" + ms + "ms  (BLOCK_SIZE=" + str(BLOCK_SIZE) + ")")
    print("  Key     : " + key + "    Status: " + status)
    print("")
    print("  Part    Interval      Semitones    Gain   Level")
    print("  " + "-" * 58)

    for i, (iv, gain) in enumerate(zip(ivs, gains)):
        lbl  = interval_label(iv).ljust(10)
        st_s = semitone_str(iv).rjust(8) + " st"
        bar  = "[" + "#" * int(gain * 16) + "-" * (16 - int(gain * 16)) + "]"
        tag  = "  <- dry" if iv == 0 else ""
        print("  Part " + str(i + 1) + "  " + lbl + "  " + st_s +
              "   " + str(round(gain, 2)).rjust(5) + "  " + bar + tag)

    print("")
    print("  " + "-" * 58)
    print("  PRESETS:")
    for k, v in PRESETS.items():
        print("  [" + k + "]  " + v["name"].ljust(28) + str(v["intervals"]))

    print("")
    print("  " + "-" * 58)
    print("  CONTROLS:")
    print("  [1-6]  Load preset         [i]  Edit intervals manually")
    print("  [g]    Edit voice gains    [k]  Cycle key (display only)")
    print("  [b]    Toggle bypass       [d]  List all devices + indices")
    print("  [r]    Refresh             [q]  Quit")
    print("")
    print("  To change output/input: edit the top of Pytsmod_Harmony_engine.py")
    print("  OUTPUT_DEVICE_INDEX = 5   (laptop speakers)")
    print("  OUTPUT_DEVICE_INDEX = 6   (Scarlett headphone jack)")
    print("  OUTPUT_DEVICE_INDEX = 36  (laptop headphone jack)")
    print("")


def ui_loop():
    draw_ui()

    while state["running"]:
        try:
            ch = input("  Command > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            state["running"] = False
            break

        if not ch:
            draw_ui()
            continue

        if ch in PRESETS:
            new_iv = list(PRESETS[ch]["intervals"])
            with state_lock:
                state["intervals"] = new_iv
            print("  Loaded: " + PRESETS[ch]["name"])
            time.sleep(0.4)
            draw_ui()

        elif ch == "i":
            print("")
            print("  Enter 4 semitone values e.g.  0 4 7 -3")
            try:
                vals = [int(x) for x in input("  Intervals > ").strip().split()]
                if len(vals) != 4:
                    raise ValueError()
                vals = [max(-24, min(24, v)) for v in vals]
                with state_lock:
                    state["intervals"] = vals
                print("  Set: " + str(vals))
            except ValueError:
                print("  ERROR: need exactly 4 integers  e.g.  0 4 7 -3")
            time.sleep(0.6)
            draw_ui()

        elif ch == "g":
            print("")
            print("  Enter 4 gain values (0.0-1.0) e.g.  0.85 0.70 0.70 0.65")
            try:
                vals = [float(x) for x in input("  Gains > ").strip().split()]
                if len(vals) != 4:
                    raise ValueError()
                vals = [max(0.0, min(1.0, v)) for v in vals]
                with state_lock:
                    state["gains"] = vals
                print("  Set: " + str(vals))
            except ValueError:
                print("  ERROR: need exactly 4 floats  e.g.  0.85 0.70 0.70 0.65")
            time.sleep(0.6)
            draw_ui()

        elif ch == "k":
            with state_lock:
                state["key_index"] = (state["key_index"] + 1) % 12
                k = KEYS[state["key_index"]]
            print("  Key: " + k)
            time.sleep(0.3)
            draw_ui()

        elif ch == "b":
            with state_lock:
                state["bypass"] = not state["bypass"]
                bp = state["bypass"]
            print("  BYPASS ON - dry only" if bp else "  BYPASS OFF - harmonies active")
            time.sleep(0.4)
            draw_ui()

        elif ch == "d":
            list_all_devices()
            input("  Press Enter to continue...")
            draw_ui()

        elif ch == "r":
            draw_ui()

        elif ch == "q":
            state["running"] = False
            print("")
            print("  Shutting down...")

        else:
            print("  Unknown command. Type r to refresh.")


# -----------------------------------------------------------------
#  MAIN
# -----------------------------------------------------------------

def main():
    print("")
    print("  Pytsmod Harmony Engine v2.1 starting up...")
    print("")

    if not PSOLA_AVAILABLE:
        print("  WARNING: pytsmod not installed.")
        print("  Run:  pip install pytsmod")
        print("  Running on resample fallback — install pytsmod for best results.")
        print("")

    print("  Resolving audio devices...")
    dev = resolve_devices()

    if dev["scarlett_found"]:
        print("  Scarlett Solo detected on system.")
    else:
        print("  WARNING: No Scarlett found - using system defaults.")

    print("  Input  -> [" + str(dev["input"])  + "] " + dev["input_name"])
    print("  Output -> [" + str(dev["output"]) + "] " + dev["output_name"])

    if OUTPUT_DEVICE_INDEX is not None:
        print("  Output HARDCODED to index " + str(OUTPUT_DEVICE_INDEX) + " - Scarlett will not override.")
    if INPUT_DEVICE_INDEX is not None:
        print("  Input  HARDCODED to index " + str(INPUT_DEVICE_INDEX))

    state["input_dev"]   = dev["input"]
    state["output_dev"]  = dev["output"]
    state["input_name"]  = dev["input_name"]
    state["output_name"] = dev["output_name"]

    time.sleep(0.8)

    # Boost thread priority on Windows
    try:
        import ctypes
        handle = ctypes.windll.kernel32.GetCurrentThread()
        ctypes.windll.kernel32.SetThreadPriority(handle, 15)
    except Exception:
        pass

    # Start 4 voice worker threads
    for i in range(NUM_VOICES):
        t = threading.Thread(target=voice_worker, args=(i,), daemon=True)
        t.start()

    # Start mixer thread
    threading.Thread(target=mixer_thread, daemon=True).start()

    # Start output thread
    threading.Thread(target=output_thread, daemon=True).start()

    try:
        with sd.InputStream(
            device=state["input_dev"],
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=input_callback,
        ):
            ui_loop()

    except sd.PortAudioError as e:
        print("")
        print("  AUDIO ERROR: " + str(e))
        print("  Check that your Scarlett Solo is plugged in")
        print("  and not currently in use by another app.")
        print("")
        sys.exit(1)

    state["running"] = False
    print("  Goodbye.")
    print("")


if __name__ == "__main__":
    main()
