# Real-Time Harmony Engine

A low-latency, real-time vocal harmonizer built in Python. Captures live audio via a Focusrite Scarlett Solo, pitch-shifts it into three parallel harmony voices using WSOLA, and mixes them back in real time at ~23ms latency.

🎥 **[Video Demo](https://drive.google.com/drive/folders/1FDp65XoFdiHWB9RHp_Luu4pR2j9-GzQ6)**

---

## Features

- Real-time multi-voice harmony generation over live microphone input
- WSOLA-based pitch shifting via [pytsmod](https://github.com/KAIST-MACLab/pytsmod)
- Parallel voice processing with dedicated worker threads per harmony voice
- Multiple harmony presets (major/minor triads, barbershop, gospel, octave stacks, custom intervals)
- ASIO low-latency audio support with Focusrite Scarlett Solo integration
- Interactive terminal interface for live preset switching, gain control, and device selection
- Configurable buffer sizes for latency/stability tradeoff

---

## System Architecture

```text
Microphone Input
        │
        ▼
Focusrite Scarlett Solo
        │
        ▼
ASIO Driver Layer
        │
        ▼
Input Callback
        │
        ▼
Voice Worker Threads
 ┌────┼────┐
 ▼    ▼    ▼
Voice 1 Voice 2 Voice 3
        │
        ▼
   Mixer Thread
        │
        ▼
  Output Stream
        │
        ▼
Speakers / Headphones
```

Incoming audio is divided into blocks and distributed across dedicated worker threads. Each thread generates an independent harmony voice using pitch shifting before the signals are mixed together and streamed to the output device. The mixer applies soft clipping to prevent distortion when combining voices.

---

## Technologies

| Layer    | Stack                                      |
| -------- | ------------------------------------------ |
| Language | Python                                     |
| DSP      | NumPy, SciPy, pytsmod (WSOLA)              |
| Audio I/O| sounddevice, ASIO drivers                  |
| Hardware | Focusrite Scarlett Solo                     |

---

## Latency

| Buffer Size  | Approximate Latency | Notes                                   |
| ------------ | ------------------- | --------------------------------------- |
| 512 samples  | ~12 ms              | Lowest latency, more prone to underruns |
| 1024 samples | ~23 ms              | Balanced configuration                  |
| 2048 samples | ~46 ms              | Stable under heavier DSP workloads      |
| 4096 samples | ~93 ms              | Maximum stability                       |

---

## Technical Challenges

**Real-time callback constraints.** Audio callbacks operate under strict deadlines — if processing overruns, glitches occur. Processing was offloaded into worker threads with queue-based communication to keep the callback lightweight.

**Multi-stream synchronization.** Each harmony voice is processed independently, so processed blocks must be synchronized before mixing. This required careful queue management and thread coordination to prevent timing drift.

**Latency vs. stability.** Smaller buffers improve responsiveness but tighten timing margins across the entire pipeline. Buffer configuration is exposed as a tunable parameter.

---

## Why I Built This

Most DSP tutorials cover the math behind audio effects but stop short of building a complete real-time system. I wanted to build one end-to-end — from microphone capture through parallel pitch shifting to mixed output — and learn how professional audio software manages strict timing constraints while processing data continuously.

---

## Installation

```bash
pip install pytsmod sounddevice numpy scipy
```

```bash
python Pytsmod_Harmony_engine.py
```

Requires an ASIO-compatible audio interface (tested with Focusrite Scarlett Solo on Windows).

---

## Future Work

- MIDI controller integration for live performance
- GPU-accelerated DSP processing
- Graphical user interface
- Dynamic key detection and automatic harmony generation

---

## Author

**Mawiignen Tony Mallen-Ntiador**
Computer Science & Applied Physics — Davidson College
