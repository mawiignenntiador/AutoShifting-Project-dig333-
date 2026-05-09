# Real-Time Low-Latency Audio Processing System

## Overview

This project is a real-time low-latency audio processing system built in Python using a Focusrite Scarlett Solo audio interface and ASIO drivers. The application captures live audio streams, performs real-time DSP (Digital Signal Processing) operations, and outputs processed audio with minimal latency.

The primary focus of the project was not only audio transformation, but also understanding and implementing:

- Real-time audio streaming
- Low-latency processing pipelines
- Buffer management
- Audio thread optimization
- DSP performance constraints
- Hardware/software audio synchronization

The system was designed as a practical exploration of how modern audio engines process live signals under strict timing requirements.

---

# Tech Stack

- **Python 3**
- **pytsmod**
  - Time-scale modification and pitch shifting
- **sounddevice**
  - Real-time audio streaming and callback handling
- **ASIO Drivers**
  - Low-latency audio communication
- **Focusrite Scarlett Solo**
  - USB audio interface for live input/output processing

---

# Core Features

- Real-time audio input/output streaming
- Low-latency DSP pipeline
- Buffer-based audio processing
- Live signal transformation
- Audio callback processing architecture
- ASIO-based low-latency communication
- Modular DSP experimentation environment

---

# System Architecture

```text
Audio Input
    ↓
Scarlett Solo Interface
    ↓
ASIO Driver Layer
    ↓
sounddevice Stream Callback
    ↓
Real-Time Buffer Processing
    ↓
pytsmod DSP Engine
    ↓
Output Buffer
    ↓
Audio Output
```

---

# Project Objectives

## Real-Time Audio Processing

The project was built around maintaining continuous real-time audio throughput while avoiding:

- Buffer underruns
- Audio dropouts
- Thread blocking
- Excessive processing latency

---

## Low-Latency Optimization

Special focus was placed on reducing end-to-end latency through:

- ASIO driver integration
- Buffer size tuning
- Lightweight DSP operations
- Efficient callback execution
- Reduced memory allocation during streams

---

## DSP Experimentation

The processing pipeline supports experimentation with:

- Pitch shifting
- Time-scale modification
- Live signal manipulation
- Streaming DSP operations

---

# Installation

## Install Dependencies

```bash
pip install pytsmod sounddevice numpy
```

# Buffering and Latency Work

A major component of the project involved understanding how real-time systems handle audio buffering under timing constraints.

## Buffer Size Testing

Different buffer sizes were tested to balance:

- Latency
- Stream stability
- CPU utilization
- DSP processing overhead

### Tested Configurations

| Buffer Size  | Purpose                         |
| ------------ | ------------------------------- |
| 512 samples  | Lower latency real-time testing |
| 1024 samples | Balanced latency and stability  |
| 2048 samples | Stability-focused processing    |

Smaller buffers reduced perceived latency but increased the likelihood of underruns and audio instability during heavier DSP workloads. Larger buffers improved stability at the cost of increased round-trip latency.

---

# Real-Time Processing Considerations

The DSP pipeline was optimized to minimize:

- Callback execution time
- Memory allocations
- Blocking operations
- Processing overhead

This was critical to maintaining uninterrupted audio streams under low-latency conditions.

---

# Performance Focus Areas

- Real-time callback execution
- Stream synchronization
- Audio throughput stability
- Buffer scheduling
- DSP efficiency
- Low-latency hardware communication

---

# Technical Challenges

- Preventing audio underruns
- Maintaining stable streams at smaller buffer sizes
- Managing CPU load during DSP operations
- Synchronizing input/output streams in real time
- Balancing processing complexity with latency requirements

---

# Future Improvements

- Expanded DSP effect chain
- Multi-threaded processing pipeline
- MIDI device integration
- Recording and writing to an audio file.

---

# Learning Outcomes

This project provided hands-on experience with:

- Real-time systems programming
- Low-latency audio architecture
- Audio buffer management
- DSP pipeline optimization
- Python-based audio streaming
- ASIO driver integration
- Performance tuning for live audio applications

---

# License

MIT License
