"""
Script to convert the generated PNG icon to a proper Windows .ico file.
Requires Pillow: pip install Pillow
"""

from PIL import Image
import os

def create_ico_from_png(png_path: str, ico_path: str):
    """Convert a PNG image to a multi-size Windows .ico file."""
    img = Image.open(png_path).convert("RGBA")

    # Windows ico standard sizes (largest to smallest)
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

    # Resize to largest and save as ico with all sizes embedded
    img_256 = img.resize((256, 256), Image.LANCZOS)
    img_256.save(
        ico_path,
        format="ICO",
        sizes=ico_sizes
    )
    print(f"✅ Icon saved: {ico_path}")
    print(f"   Sizes embedded: {[f'{s[0]}x{s[1]}' for s in ico_sizes]}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to the generated PNG (copy it here first or update this path)
    png_path = os.path.join(script_dir, "soundboard_icon_source.png")
    ico_path = os.path.join(script_dir, "neon_v_soundboard_icon.ico")

    if not os.path.exists(png_path):
        print(f"❌ PNG not found at: {png_path}")
        print("   Please copy the generated PNG to that location and re-run.")
    else:
        create_ico_from_png(png_path, ico_path)
