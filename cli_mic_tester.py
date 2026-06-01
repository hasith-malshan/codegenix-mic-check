import pyaudio
import numpy as np
import sys
import os

# ANSI color codes for terminal output
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def get_color_bar(peak, max_val=32768, bar_length=50):
    """Generates a colored ASCII progress bar based on volume peak."""
    # Calculate how many blocks to fill
    filled_length = int((peak / max_val) * bar_length)
    filled_length = min(bar_length, filled_length)  # Cap at max length

    bar = ""
    for i in range(bar_length):
        if i < filled_length:
            # Color coding: bottom 60% Green, next 20% Yellow, top 20% Red
            if i < int(bar_length * 0.6):
                bar += f"{GREEN}█{RESET}"
            elif i < int(bar_length * 0.8):
                bar += f"{YELLOW}█{RESET}"
            else:
                bar += f"{RED}█{RESET}"
        else:
            bar += "-"

    return bar


def main():
    p = pyaudio.PyAudio()

    print("=== INMP441 I2S Mic CLI Tester ===")
    print("Scanning for audio input devices...\n")

    # 1. Fetch available input devices
    device_list = []
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev.get('maxInputChannels') > 0:
            device_list.append((i, dev.get('name')))
            print(f"[{i}] {dev.get('name')}")

    if not device_list:
        print("No input devices found! Is the I2S overlay enabled in boot/config.txt?")
        p.terminate()
        sys.exit(1)

    # 2. Prompt user to select a device
    print("-" * 40)
    selected_idx = -1
    while selected_idx == -1:
        try:
            choice = input("Enter the number of your I2S microphone: ")
            idx = int(choice)
            # Validate choice
            if any(dev[0] == idx for dev in device_list):
                selected_idx = idx
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

    # 3. Setup audio stream
    CHUNK = 1024
    RATE = 44100

    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=RATE,
                        input=True,
                        input_device_index=selected_idx,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Failed to open audio stream: {e}")
        p.terminate()
        sys.exit(1)

    # 4. Start monitoring
    os.system('clear' if os.name == 'posix' else 'cls')
    print(f"Monitoring Device [{selected_idx}]... Press Ctrl+C to stop.\n")

    try:
        while True:
            # Read audio chunk
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)

            # Find peak volume
            peak = np.abs(audio_data).max()

            # Generate the colored bar
            bar = get_color_bar(peak)

            # Print the bar with a carriage return '\r' so it overwrites the current line
            # :05d pads the number to 5 digits so it doesn't jump around
            sys.stdout.write(f"\rLevel: [{bar}] {peak:05d}/32768")
            sys.stdout.flush()

    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        print(f"\n\nStopping monitor...")

    finally:
        # Cleanup
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Audio resources released. Goodbye!")


if __name__ == "__main__":
    main()