import sys
import subprocess

# === Auto-install missing modules ===
required_modules = ["Pillow", "watchdog"]

for module in required_modules:
    try:
        if module == "Pillow":
            __import__("PIL")
        else:
            __import__(module)
    except ImportError:
        print(f"Installing missing module: {module}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", module])

import os
import time
import traceback
import shutil
import queue
import threading
import json
from PIL import Image, ImageDraw
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import filedialog

# === CONFIGURATION ===
CONFIG_FILE = "settings.json"

# Load or create config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
else:
    cfg = {}

INPUT_FOLDER = cfg.get("input_folder", r"C:\Users\Coody\Pictures\Screenshots\TP Icon Rounder")
OUTPUT_FOLDER = cfg.get("output_folder", r"D:\Scruplez\Touch Portal\icons\soundboard icons")
PROCESSED_FOLDER = cfg.get("processed_folder", r"C:\Users\Coody\Pictures\Screenshots\TP Icon Rounder\processed images")
OVERLAY_PATH = cfg.get("overlay_path", r"D:\Scruplez\Scripts\Icon Rounder for TP\glass overlay.png")
CORNER_RADIUS_PERCENT = cfg.get("corner_radius_percent", 0.15)

ICON_SIZE = (112, 112)
SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.webp']

dialog_queue = queue.Queue()

# === HELPER FUNCTIONS ===
def round_corners(image, radius_percent):
    radius = int(min(image.size) * radius_percent)
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    result = image.copy()
    result.putalpha(mask)
    return result

def safe_move(src, dst_folder, filename):
    os.makedirs(dst_folder, exist_ok=True)
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(dst_folder, new_filename)):
        new_filename = f"{name} ({counter}){ext}"
        counter += 1
    shutil.move(src, os.path.join(dst_folder, new_filename))

def process_image(filepath):
    try:
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext not in SUPPORTED_FORMATS:
            return
        base_img = Image.open(filepath).convert("RGBA")
        base_img = base_img.resize(ICON_SIZE, Image.LANCZOS)
        rounded_img = round_corners(base_img, CORNER_RADIUS_PERCENT)
        overlay = Image.open(OVERLAY_PATH).convert("RGBA").resize(ICON_SIZE, Image.LANCZOS)
        final_img = Image.alpha_composite(rounded_img, overlay)
        output_path = os.path.join(OUTPUT_FOLDER, f"{name}.png")
        final_img.save(output_path, format="PNG")
        safe_move(filepath, PROCESSED_FOLDER, filename)
        print(f"✅ Processed: {filename}")
    except Exception:
        print(f"❌ Failed: {os.path.basename(filepath)}")
        traceback.print_exc()

# === WATCHDOG HANDLER ===
class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            time.sleep(1)
            process_image(event.src_path)

# === DIALOG HANDLING ===
def open_dialog(option):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    if option == "1":
        path = filedialog.askdirectory(title="Select Input Folder")
    elif option == "2":
        path = filedialog.askdirectory(title="Select Output Folder")
    elif option == "3":
        path = filedialog.askdirectory(title="Select Processed Images Folder")
    elif option == "4":
        path = filedialog.askopenfilename(title="Select Overlay Image File", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.webp")])
    else:
        path = None
    root.destroy()
    return path

def prompt_change_setting(option):
    global CORNER_RADIUS_PERCENT
    if option in ["1", "2", "3", "4"]:
        dialog_queue.put(option)
    elif option == "5":
        while True:
            try:
                new_value = input("Enter new corner roundness percentage (e.g., 15 for 15% or press Enter to cancel): ").strip()
                if new_value == "":
                    print("↩ Cancelled corner roundness change.\n")
                    break
                if new_value.isdigit():
                    CORNER_RADIUS_PERCENT = int(new_value) / 100
                    cfg["corner_radius_percent"] = CORNER_RADIUS_PERCENT
                    save_config()
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print("🟢 Watching for new images...")
                    print_status()
                    break
                else:
                    print("❌ Invalid input. Please enter a number.")
            except Exception as e:
                print(f"❌ Error changing roundness: {e}")
                break

def save_config():
    global cfg, INPUT_FOLDER, OUTPUT_FOLDER, PROCESSED_FOLDER, OVERLAY_PATH, CORNER_RADIUS_PERCENT
    cfg["input_folder"] = INPUT_FOLDER
    cfg["output_folder"] = OUTPUT_FOLDER
    cfg["processed_folder"] = PROCESSED_FOLDER
    cfg["overlay_path"] = OVERLAY_PATH
    cfg["corner_radius_percent"] = CORNER_RADIUS_PERCENT
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def print_status():
    print(f"\nWatching folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"Processed images folder: {PROCESSED_FOLDER}")
    print(f"Overlay image: {OVERLAY_PATH}\n")
    print("Press 1 to change input folder")
    print("Press 2 to change output folder")
    print("Press 3 to change processed images folder")
    print("Press 4 to change overlay image file")
    print(f"Press 5 to change corner roundness (Currently: {int(CORNER_RADIUS_PERCENT * 100)}%)\n")

def hotkey_listener():
    import msvcrt
    while True:
        time.sleep(0.1)
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8", errors="ignore")
            if key in ["1", "2", "3", "4", "5"]:
                prompt_change_setting(key)

# === MAIN ===
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print("🟢 Watching for new images...")
    print_status()

    observer = Observer()
    observer.schedule(ImageHandler(), path=INPUT_FOLDER, recursive=False)
    observer.start()

    threading.Thread(target=hotkey_listener, daemon=True).start()

    try:
        while True:
            try:
                option = dialog_queue.get_nowait()
            except queue.Empty:
                option = None

            if option and option in ["1", "2", "3", "4"]:
                path = open_dialog(option)
                if path:
                    if option == "1":
                        INPUT_FOLDER = path
                    elif option == "2":
                        OUTPUT_FOLDER = path
                    elif option == "3":
                        PROCESSED_FOLDER = path
                    elif option == "4":
                        OVERLAY_PATH = path
                    save_config()
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print("🟢 Watching for new images...")
                    print("\n✅ Setting updated!\n")
                    print_status()

            time.sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
