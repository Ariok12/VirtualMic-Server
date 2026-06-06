# VirtualMic PC Server

![VirtualMic Server Icon](icon.ico)

**VirtualMic Server** is the companion Windows receiver application for the [VirtualMic Android App](https://github.com/Ariok12/VirtualMic). It captures low-latency UDP audio streams sent from your phone and routes them directly into your PC's audio system.

## ✨ Features

- **Ultra-Low Latency**: Processes incoming UDP raw PCM audio streams with near-zero delay.
- **Auto-Discovery (mDNS)**: Automatically broadcasts its IP and Port on the local network using Zeroconf, allowing the Android app to connect with a single tap.
- **Dynamic Format Switching**: Automatically adapts to 16kHz, 44.1kHz, and 48kHz sample rates, as well as Mono and Stereo channels.
- **VB-Cable Integration**: Designed to seamlessly output audio into "VB-Audio Virtual Cable", allowing you to use your phone as a mic in Discord, OBS, Zoom, and games.
- **System Tray Support**: Can be minimized to the Windows system tray so it runs silently in the background.

## 🚀 Installation & Usage

### Prerequisites
- Python 3.8+ installed on Windows.
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) installed (highly recommended for routing the audio to other applications).

### Setup
1. Clone this repository:
   ```bash
   git clone https://github.com/Ariok12/VirtualMic-Server.git
   ```
2. Navigate to the project directory:
   ```bash
   cd VirtualMic-Server
   ```
3. Install the required Python dependencies:
   ```bash
   pip install pyaudio numpy customtkinter pystray pillow zeroconf
   ```

### Running the Server
Run the python script:
```bash
python server.py
```
- Select your preferred output device from the dropdown (select `CABLE Input (VB-Audio Virtual Cable)` to use it as a mic).
- Ensure your PC and Phone are on the same Wi-Fi network.
- Open the VirtualMic Android app, click the 🔍 search button, and start streaming!

## 🛠️ Building an Executable (.exe)
You can compile this Python script into a standalone `.exe` using `PyInstaller`:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --icon "icon.ico" --name "VirtualMicServer" --add-data "icon.ico;." "server.py"
```

## 📜 License
This project is open-source and available under the MIT License.
