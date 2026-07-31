import os

src_path = r"C:\Users\ap338\.gemini\antigravity\brain\a55b3dd0-bb70-4399-a2dd-183609298845\.system_generated\steps\83\content.md"
dest_dir = r"M:\iquer\ai_modules"
dest_path = os.path.join(dest_dir, "haarcascade_frontalface_default.xml")

os.makedirs(dest_dir, exist_ok=True)

with open(src_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Write lines starting from line index 8 (9th line, <?xml version="1.0"?>)
with open(dest_path, "w", encoding="utf-8") as f:
    f.writelines(lines[8:])

print("Successfully extracted Haar Cascade XML to", dest_path)
