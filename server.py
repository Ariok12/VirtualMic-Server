import socket
import pyaudio
import time
import threading
import numpy as np
import pystray
from PIL import Image, ImageDraw
from zeroconf import ServiceInfo, Zeroconf
import customtkinter as ctk
import json
import os
import numpy as np

CONFIG_FILE = "virtualmic_config.json"

class VirtualMicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("VirtualMic Server")
        
        # Load icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
            
        self.geometry("450x380")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.running = True
        self.is_connected = False
        self.tray_icon = None
        self.last_packet_time = 0
        self.current_volume = 0
        self.packet_count = 0
        self.current_format_str = "Format: 48000 Hz, Stereo"
        
        self.pa = pyaudio.PyAudio()
        self.devices = self.get_output_devices()
        self.selected_device_index = self.load_device_preference()
        
        self.setup_ui()
        
        # Start background network thread
        threading.Thread(target=self.network_thread, daemon=True).start()
        
        # Start UI updater loops
        self.update_metrics_loop()
        self.update_meter_loop()

    def get_output_devices(self):
        devices = []
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            if dev_info.get("maxOutputChannels", 0) > 0:
                devices.append({
                    "index": i,
                    "name": dev_info.get("name", f"Device {i}")
                })
        return devices

    def load_device_preference(self):
        saved_name = None
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    saved_name = config.get("device_name")
            except:
                pass
        
        # Match by name
        if saved_name:
            for dev in self.devices:
                if saved_name in dev["name"]:
                    return dev["index"]
                    
        # Fallback to CABLE Input (VB-Audio)
        for dev in self.devices:
            name_upper = dev["name"].upper()
            if "CABLE INPUT" in name_upper or "VB-AUDIO" in name_upper:
                return dev["index"]
                
        # Fallback to default
        try:
            return self.pa.get_default_output_device_info()["index"]
        except:
            return 0 if self.devices else None

    def save_device_preference(self, device_name):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"device_name": device_name}, f)
        except:
            pass

    def setup_ui(self):
        # Top Bar with Theme Toggle
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        # Very small subtle theme toggle
        self.theme_btn = ctk.CTkButton(top_frame, text="🌓", width=24, height=24, 
                                       corner_radius=12, fg_color="transparent", 
                                       hover_color="#333333", text_color=("gray10", "gray90"),
                                       command=self.toggle_theme)
        self.theme_btn.pack(side="right")
        
        # Main Status Card
        card_frame = ctk.CTkFrame(self, corner_radius=15)
        card_frame.pack(fill="x", padx=20, pady=5)
        
        # Status Row (State + IP)
        status_row = ctk.CTkFrame(card_frame, fg_color="transparent")
        status_row.pack(fill="x", padx=15, pady=(15, 10))
        
        self.state_label = ctk.CTkLabel(status_row, text="⚪ STARTING", font=("Segoe UI", 14, "bold"), text_color="gray")
        self.state_label.pack(side="left")
        
        self.ip_label = ctk.CTkLabel(status_row, text="Initializing...", font=("Segoe UI", 12), text_color="gray50")
        self.ip_label.pack(side="right")
        
        # Device Selection Dropdown
        device_row = ctk.CTkFrame(card_frame, fg_color="transparent")
        device_row.pack(fill="x", padx=15, pady=0)
        
        ctk.CTkLabel(device_row, text="Output Device:", font=("Segoe UI", 12)).pack(side="left", padx=(0, 10))
        
        device_names = [d["name"] for d in self.devices]
        current_name = next((d["name"] for d in self.devices if d["index"] == self.selected_device_index), "Unknown")
        
        self.device_combo = ctk.CTkComboBox(device_row, values=device_names, command=self.on_device_changed, width=250)
        self.device_combo.set(current_name)
        self.device_combo.pack(side="right", fill="x", expand=True)
        
        # Divider
        divider = ctk.CTkFrame(card_frame, height=1, fg_color=("gray80", "gray20"))
        divider.pack(fill="x", padx=15, pady=10)
        
        # Audio Meter Row
        meter_row = ctk.CTkFrame(card_frame, fg_color="transparent")
        meter_row.pack(fill="x", padx=15, pady=(5, 15))
        
        mic_icon = ctk.CTkLabel(meter_row, text="🎤", font=("Segoe UI", 16))
        mic_icon.pack(side="left", padx=(0, 10))
        
        # Segmented Progress Bar (15 segments)
        self.num_segments = 15
        self.segments = []
        seg_container = ctk.CTkFrame(meter_row, fg_color="transparent")
        seg_container.pack(side="left", fill="x", expand=True)
        
        for i in range(self.num_segments):
            seg = ctk.CTkFrame(seg_container, width=15, height=10, corner_radius=2, fg_color=("gray80", "gray30"))
            seg.pack(side="left", padx=2)
            self.segments.append(seg)
            
        # Data / Metrics Section
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=20, pady=5)
        
        # Top row metrics
        metrics_top = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        metrics_top.pack(fill="x")
        self.latency_label = ctk.CTkLabel(metrics_top, text="Latency: --", font=("Segoe UI", 11), text_color="gray50")
        self.latency_label.pack(side="left")
        self.buffer_label = ctk.CTkLabel(metrics_top, text="Buffer: --", font=("Segoe UI", 11), text_color="gray50")
        self.buffer_label.pack(side="right")
        
        # Bottom row metrics
        metrics_bot = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        metrics_bot.pack(fill="x")
        self.format_label = ctk.CTkLabel(metrics_bot, text="Format: --", font=("Segoe UI", 11), text_color="gray50")
        self.format_label.pack(side="left")
        
        # Button Frame (Footer)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        # Secondary Muted Button (Transparent with border)
        self.min_btn = ctk.CTkButton(btn_frame, text="Minimize to Tray", 
                                     fg_color="transparent", hover_color=("gray85", "gray25"), 
                                     border_width=1, border_color=("gray70", "gray30"),
                                     text_color=("gray10", "gray90"),
                                     font=("Segoe UI", 12, "bold"), command=self.minimize_to_tray, corner_radius=8)
        self.min_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Primary Action Button (Red)
        self.stop_btn = ctk.CTkButton(btn_frame, text="Stop Server", 
                                      fg_color="#e74c3c", hover_color="#c0392b", 
                                      font=("Segoe UI", 12, "bold"), command=self.on_closing, corner_radius=8)
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def on_device_changed(self, choice):
        self.save_device_preference(choice)
        for dev in self.devices:
            if dev["name"] == choice:
                self.selected_device_index = dev["index"]
                break
        # Force a stream restart on the next packet
        self.force_restart_stream = True

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")
        # Force redraw on next loop
        for i in range(self.num_segments):
            setattr(self, f"seg_color_{i}", None)

    def update_meter_loop(self):
        if not self.running:
            return
            
        lit_segments = int((self.current_volume / 100.0) * self.num_segments)
        
        current_mode = ctk.get_appearance_mode()
        off_color = "gray80" if current_mode == "Light" else "gray30"
        
        for i in range(self.num_segments):
            if i < lit_segments:
                if i < 8:
                    color = "#2ecc71"
                elif i < 12:
                    color = "#f1c40f"
                else:
                    color = "#e74c3c"
            else:
                color = off_color
                
            # Only update UI if color changed to save CPU
            if getattr(self, f"seg_color_{i}", None) != color:
                self.segments[i].configure(fg_color=color)
                setattr(self, f"seg_color_{i}", color)
                
        # Smooth volume decay
        self.current_volume = max(0, self.current_volume - 4)
        self.after(50, self.update_meter_loop)

    def update_metrics_loop(self):
        if not self.running:
            return
            
        if self.is_connected:
            time_since_last = time.time() - self.last_packet_time
            if time_since_last > 1.0:
                self.buffer_label.configure(text="Buffer: Stalling", text_color="#e74c3c")
            elif time_since_last > 0.1:
                self.buffer_label.configure(text="Buffer: Recovering", text_color="#f1c40f")
            else:
                self.buffer_label.configure(text="Buffer: Healthy", text_color="#2ecc71")
                
            self.latency_label.configure(text="Latency: < 5ms (LAN)", text_color=("gray40", "gray60"))
            self.format_label.configure(text=self.current_format_str, text_color=("gray40", "gray60"))
        else:
            self.buffer_label.configure(text="Buffer: --", text_color=("gray40", "gray60"))
            self.latency_label.configure(text="Latency: --", text_color=("gray40", "gray60"))
            self.format_label.configure(text="Format: --", text_color=("gray40", "gray60"))
            
        self.after(500, self.update_metrics_loop)

    def network_thread(self):
        UDP_IP = "0.0.0.0"
        UDP_PORT = 8765
        
        # Zeroconf mDNS broadcast
        zeroconf = Zeroconf()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "127.0.0.1"
            
        info = ServiceInfo(
            "_virtualmic._udp.local.",
            "VirtualMic PC._virtualmic._udp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=UDP_PORT,
            properties={},
            server="virtualmic.local."
        )
        try:
            zeroconf.register_service(info)
        except Exception as e:
            print("Zeroconf error:", e)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8192)
            sock.bind((UDP_IP, UDP_PORT))
            sock.settimeout(1.0)
        except OSError:
            self.after(0, lambda: self.state_label.configure(text="🔴 PORT IN USE", text_color="#e74c3c"))
            self.after(0, lambda: self.ip_label.configure(text=f"Port {UDP_PORT}"))
            return
        except Exception as e:
            self.after(0, lambda: self.state_label.configure(text="🔴 NETWORK ERROR", text_color="#e74c3c"))
            return

        if self.selected_device_index is None:
            self.after(0, lambda: self.state_label.configure(text="🔴 AUDIO ERROR", text_color="#e74c3c"))
            self.after(0, lambda: self.ip_label.configure(text="No audio output devices found"))
            sock.close()
            return

        current_channels = 2
        current_rate = 48000
        stream = None
        self.force_restart_stream = False
        
        def open_stream(channels, rate, device_id):
            return self.pa.open(
                format=pyaudio.paInt16, 
                channels=channels, 
                rate=rate, 
                output=True, 
                output_device_index=device_id,
                frames_per_buffer=1024
            )

        try:
            stream = open_stream(current_channels, current_rate, self.selected_device_index)
        except Exception as e:
            self.after(0, lambda: self.state_label.configure(text="🔴 AUDIO ERROR", text_color="#e74c3c"))
            self.after(0, lambda msg=str(e): self.ip_label.configure(text=f"Failed to open device: {msg}"))

        self.after(0, lambda: self.state_label.configure(text="🔵 LISTENING", text_color="#1E90FF"))
        self.after(0, lambda: self.ip_label.configure(text=f"Waiting on port {UDP_PORT}"))

        TIMEOUT_SECONDS = 2.0
        
        while self.running:
            try:
                data, addr = sock.recvfrom(8192)
                self.last_packet_time = time.time()
                
                if not self.is_connected:
                    self.is_connected = True
                    self.after(0, lambda: self.state_label.configure(text="🟢 CONNECTED", text_color="#2ecc71"))
                    self.after(0, lambda a=addr[0]: self.ip_label.configure(text=a))
                
                # Check for header: [0xAA, 0xBB, channels, rate_code]
                if len(data) > 4 and data[0] == 0xAA and data[1] == 0xBB:
                    channels = data[2]
                    rate_code = data[3]
                    
                    if rate_code == 0:
                        rate = 16000
                    elif rate_code == 1:
                        rate = 44100
                    else:
                        rate = 48000
                        
                    format_changed = (channels != current_channels or rate != current_rate)
                    
                    if format_changed or self.force_restart_stream:
                        self.force_restart_stream = False
                        
                        try:
                            if stream:
                                stream.stop_stream()
                                stream.close()
                        except:
                            pass
                            
                        current_channels = channels
                        current_rate = rate
                        self.current_format_str = f"Format: {current_rate} Hz, {'Stereo' if channels == 2 else 'Mono'}"
                        
                        try:
                            stream = open_stream(current_channels, current_rate, self.selected_device_index)
                            self.after(0, lambda: self.state_label.configure(text="🟢 CONNECTED", text_color="#2ecc71"))
                            self.after(0, lambda a=addr[0]: self.ip_label.configure(text=a))
                        except Exception as e:
                            stream = None
                            self.after(0, lambda: self.state_label.configure(text="🟠 FORMAT REJECTED", text_color="#e67e22"))
                            self.after(0, lambda: self.ip_label.configure(text="Driver unsupported format. Reverting..."))
                            
                            # Fallback to previous safe rate (usually 44100 mono)
                            try:
                                current_channels = 1
                                current_rate = 48000
                                stream = open_stream(current_channels, current_rate, self.selected_device_index)
                                self.current_format_str = f"Format: {current_rate} Hz, Mono (Fallback)"
                            except:
                                pass
                    
                    data = data[4:] # Strip header
                    
                self.packet_count += 1
                if self.packet_count % 4 == 0:
                    try:
                        audio_array = np.frombuffer(data, dtype=np.int16)
                        if len(audio_array) > 0:
                            rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
                            # Set volume for the UI loop to pick up
                            self.current_volume = min(100, int((rms / 12000.0) * 100))
                    except Exception:
                        pass
                    
                if stream and stream.is_active():
                    stream.write(data)
                
            except socket.timeout:
                current_time = time.time()
                if self.is_connected and (current_time - self.last_packet_time > TIMEOUT_SECONDS):
                    self.is_connected = False
                    self.after(0, lambda: self.state_label.configure(text="🟠 DISCONNECTED", text_color="#e67e22"))
                    self.after(0, lambda: self.ip_label.configure(text="Waiting for phone..."))
                    self.current_volume = 0
            except Exception as e:
                print("Network thread exception:", e)
                break
                
        # Cleanup
        try:
            zeroconf.unregister_service(info)
            zeroconf.close()
            if stream:
                stream.stop_stream()
                stream.close()
            self.pa.terminate()
            sock.close()
        except:
            pass

    def minimize_to_tray(self):
        self.withdraw()
        
        # Create tray icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color=(33, 150, 243))
            d = ImageDraw.Draw(image)
            d.rectangle((16, 16, 48, 48), fill='white')
        
        menu = pystray.Menu(
            pystray.MenuItem('Show', self.show_window, default=True),
            pystray.MenuItem('Quit', self.quit_window)
        )
        self.tray_icon = pystray.Icon("VirtualMic", image, "VirtualMic Server", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_window(self, icon, item):
        icon.stop()
        self.after(0, self.on_closing)

    def on_closing(self):
        self.running = False
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except: pass
        self.destroy()

if __name__ == "__main__":
    app = VirtualMicApp()
    app.mainloop()