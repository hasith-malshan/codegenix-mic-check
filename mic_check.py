import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import threading


class I2SMicTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("INMP441 I2S Mic Tester")
        self.root.geometry("400x200")

        self.p = pyaudio.PyAudio()
        self.is_running = False
        self.stream = None

        # 1. Fetch available input devices
        self.device_list = []
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if dev.get('maxInputChannels') > 0:
                self.device_list.append(f"{i}: {dev.get('name')}")

        # 2. Setup the UI
        ttk.Label(root, text="Select I2S Microphone:", font=("Arial", 12)).pack(pady=10)

        self.dev_var = tk.StringVar()
        if self.device_list:
            self.dev_var.set(self.device_list[0])

        self.combo = ttk.Combobox(root, textvariable=self.dev_var, values=self.device_list, width=40, state="readonly")
        self.combo.pack(pady=5, padx=10)

        self.btn = ttk.Button(root, text="Start Monitoring", command=self.toggle_test)
        self.btn.pack(pady=10)

        # 3. Setup the Volume Meter Canvas
        self.canvas = tk.Canvas(root, width=300, height=30, bg="black", highlightthickness=1,
                                highlightbackground="gray")
        self.canvas.pack(pady=10)
        self.bar = self.canvas.create_rectangle(0, 0, 0, 30, fill="green")

    def toggle_test(self):
        if not self.is_running:
            self.start()
        else:
            self.stop()

    def start(self):
        if not self.dev_var.get():
            return

        # Extract the device index from the dropdown string
        idx = int(self.dev_var.get().split(":")[0])

        try:
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,  # Standard audio rate
                                      input=True,
                                      input_device_index=idx,
                                      frames_per_buffer=1024)
            self.is_running = True
            self.btn.config(text="Stop Monitoring")

            # Start background thread for reading audio to prevent GUI freezing
            self.thread = threading.Thread(target=self.read_audio, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"Failed to open audio stream: {e}")

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.btn.config(text="Start Monitoring")
        self.canvas.coords(self.bar, 0, 0, 0, 30)  # Reset meter

    def read_audio(self):
        while self.is_running:
            try:
                # exception_on_overflow=False prevents crashes if the Pi lags
                data = self.stream.read(1024, exception_on_overflow=False)

                # Convert raw bytes to 16-bit integers
                audio_data = np.frombuffer(data, dtype=np.int16)

                # Find the peak volume in this chunk
                peak = np.abs(audio_data).max()

                # Convert peak volume to the pixel width of the canvas (max 16-bit val is 32767)
                width = int((peak / 32768.0) * 300)

                # Schedule the GUI update
                self.root.after(0, self.update_meter, width)
            except Exception as e:
                print("Audio read error:", e)
                break

    def update_meter(self, width):
        # Change color based on how loud it is
        color = "green"
        if width > 180: color = "yellow"
        if width > 260: color = "red"

        self.canvas.coords(self.bar, 0, 0, width, 30)
        self.canvas.itemconfig(self.bar, fill=color)


def on_closing():
    app.stop()
    app.p.terminate()
    root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = I2SMicTesterApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)  # Clean exit handling
    root.mainloop()