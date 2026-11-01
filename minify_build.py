import json
import pathlib
import subprocess

DIST = pathlib.Path("dist")

# 1. Minify JavaScript
app_js = DIST / "app.js"
temp_js = DIST / "app.min.js"

print("Minifying app.js...")

subprocess.run(
    [
        "npx", "--yes", "terser",
        str(app_js),
        "--compress",
        "--mangle",
        "--output", str(temp_js),
    ],
    check=True,
)

temp_js.replace(app_js)

# 2. Minify all JSON files
json_files = list(DIST.rglob("*.json"))

print(f"Minifying {len(json_files)} JSON files...")

for path in json_files:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

