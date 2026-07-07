import os
import sys

from PIL import Image

src_path = sys.argv[1] if len(sys.argv) > 1 else "frontend/public/kairos-icon.png"
src = Image.open(src_path).convert("RGB")

out_dir = "frontend/public/icons"
os.makedirs(out_dir, exist_ok=True)

for size in (192, 512):
    src.resize((size, size), Image.LANCZOS).save(f"{out_dir}/icon-{size}.png", "PNG")

maskable = Image.new("RGB", (512, 512), (11, 18, 14))
inner = src.resize((398, 398), Image.LANCZOS)
maskable.paste(inner, ((512 - 398) // 2, (512 - 398) // 2))
maskable.save(f"{out_dir}/maskable-512.png", "PNG")

src.resize((180, 180), Image.LANCZOS).save(f"{out_dir}/apple-touch-icon.png", "PNG")
src.resize((64, 64), Image.LANCZOS).save(f"{out_dir}/favicon-64.png", "PNG")

print(f"icon set written to {out_dir} from {src_path}")
