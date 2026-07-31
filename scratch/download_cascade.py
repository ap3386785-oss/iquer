import urllib.request
import os

url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
dest_dir = r"M:\iquer\ai_modules"
dest_path = os.path.join(dest_dir, "haarcascade_frontalface_default.xml")

os.makedirs(dest_dir, exist_ok=True)

print("Downloading Haar Cascade XML from GitHub...")
try:
    urllib.request.urlretrieve(url, dest_path)
    print("Download completed successfully!")
    # Read first and last lines to verify
    with open(dest_path, "r", encoding="utf-8") as f:
        content = f.read()
    print("Downloaded file size:", len(content), "bytes")
    print("File starts with:", content[:100])
    print("File ends with:", content[-100:])
except Exception as e:
    print("Error during download:", e)
