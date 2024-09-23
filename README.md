
---

# ARQ Protocols Simulation

This repository implements three types of Automatic Repeat Request (ARQ) protocols: **Stop-and-Wait**, **Go-Back-N**, and **Selective Repeat**, using Python. It simulates sender-receiver communication over a network, including error injection and error checking techniques like CRC and Checksum.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Requirements](#requirements)
- [Usage](#usage)
- [Running the Simulation](#running-the-simulation)
- [Protocol Overview](#protocol-overview)
- [Limitations](#limitations)

## Introduction
This project is a simulation of data transmission protocols used in networking to ensure error-free communication. The three implemented ARQ protocols handle packet loss and retransmissions differently, making them suitable for various network conditions.

## Features
- **Stop-and-Wait ARQ**: Simple protocol, but inefficient for large networks.
- **Go-Back-N ARQ**: Allows multiple packets to be in transit, improving efficiency.
- **Selective Repeat ARQ**: Only retransmits erroneous packets, making it more efficient for higher error rates.
- **Error Injection**: Simulates real-world network errors.
- **Error Detection**: Implements both **CRC** and **Checksum** techniques for error detection.

## Requirements
- Python 3.x
- Socket library (built-in)
- Git Bash or any other terminal for running the scripts on a single machine
- VS Code or any other code editor

## Usage
To simulate the communication process, you will need to first run the **receiver** program followed by the **sender**. The protocol type and error detection technique are passed as command-line arguments.

### 1. Clone the Repository:
```bash
git clone https://github.com/Suman-Khara/DataFlowControlSimulation.git
cd DataFlowControlSimulation
```

### 2. Running the Simulation:

**Step 1: Start the Receiver**
Run the receiver program with the protocol and error detection technique.
```bash
python receiver.py <protocol> <technique>
```
- `<protocol>`: Choose either `StopAndWait`, `GoBackN`, `SelectiveRepeat` (or `1`, `2`, `3`).
- `<technique>`: Choose either `CRC` or `Checksum` (or `1`, `2`).

Example:
```bash
python receiver.py GoBackN CRC
```

**Step 2: Run the Sender**
In a separate terminal, start the sender program with the protocol, file path, packet size, and error detection technique.
```bash
python sender.py <protocol> <file_path> <packet_size> <technique>
```
- `<protocol>`: Choose either `StopAndWait`, `GoBackN`, `SelectiveRepeat` (or `1`, `2`, `3`).
- `<file_path>`: Path to the input file you want to send.
- `<packet_size>`: Size of each packet (in bytes).
- `<technique>`: Choose either `CRC` or `Checksum` (or `1`, `2`).

Example:
```bash
python sender.py GoBackN data.txt 1024 CRC
```

## Protocol Overview
- **Stop-and-Wait ARQ**: Only one packet is sent and acknowledged at a time. Slow but simple.
- **Go-Back-N ARQ**: Sends a window of packets and retransmits all after an error. More efficient but can lead to redundant retransmissions.
- **Selective Repeat ARQ**: Retransmits only the erroneous packets, making it the most efficient but requiring more complex logic.

## Limitations
- This is a simulation and does not involve a real network.
- No real packet loss, latency, or congestion is simulated outside the injected errors.
- Performance on large-scale networks may vary from the simulated results.
  
## Conclusion
This project demonstrates the working of ARQ protocols, focusing on error handling and throughput in data communication. It highlights the trade-offs between efficiency and complexity in different ARQ schemes.

---
