#!/usr/bin/env python3
"""
Create a custom neon-style "V" icon with glow effects like the provided image
"""

from PIL import Image, ImageDraw, ImageFilter
import os

def create_neon_v_icon():
    # Icon dimensions (standard Windows icon size)
    size = 256
    
    # Create a new image with black background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 255))  # Black background
    
    # Create a larger canvas for glow effects
    glow_size = size + 40
    glow_img = Image.new('RGBA', (glow_size, glow_size), (0, 0, 0, 0))
    draw_glow = ImageDraw.Draw(glow_img)
    
    # Colors for neon effect
    neon_white = (255, 255, 255, 255)     # Bright white core
    neon_purple = (200, 100, 255, 180)    # Purple glow
    neon_blue = (100, 150, 255, 120)      # Blue outer glow
    neon_red = (255, 80, 120, 160)        # Red accent
    
    # Calculate V shape dimensions
    center_x = glow_size // 2
    center_y = glow_size // 2
    v_width = size * 0.6  # V takes up 60% of icon width
    v_height = size * 0.5  # V takes up 50% of icon height
    stroke_width = int(size * 0.12)  # Thicker stroke for neon effect
    
    # Define V shape points
    left_top_x = center_x - v_width // 2
    left_top_y = center_y - v_height // 2
    right_top_x = center_x + v_width // 2
    right_top_y = center_y - v_height // 2
    bottom_x = center_x
    bottom_y = center_y + v_height // 2
    
    # Create multiple glow layers for neon effect
    glow_layers = [
        (stroke_width * 4, neon_blue),     # Outer blue glow
        (stroke_width * 3, neon_purple),   # Purple glow
        (stroke_width * 2, neon_red),      # Red accent
        (stroke_width, neon_white),        # White core
    ]
    
    # Draw glow layers from largest to smallest
    for glow_width, color in glow_layers:
        # Left arm of V
        draw_glow.line([left_top_x, left_top_y, bottom_x, bottom_y], 
                      fill=color, width=glow_width)
        # Right arm of V
        draw_glow.line([right_top_x, right_top_y, bottom_x, bottom_y], 
                      fill=color, width=glow_width)
    
    # Apply gaussian blur for glow effect
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=3))
    
    # Create the main image
    draw = ImageDraw.Draw(img)
    
    # Paste the glow effect centered on the main image
    offset_x = (glow_size - size) // 2
    offset_y = (glow_size - size) // 2
    
    # Crop the glow to fit the main image
    glow_cropped = glow_img.crop((offset_x, offset_y, offset_x + size, offset_y + size))
    
    # Composite the glow onto the black background
    img = Image.alpha_composite(img, glow_cropped)
    
    # Add a sharp white core on top
    draw = ImageDraw.Draw(img)
    core_stroke = int(stroke_width * 0.6)
    
    # Adjust coordinates for the main image
    main_center_x = size // 2
    main_center_y = size // 2
    main_left_top_x = main_center_x - v_width // 2
    main_left_top_y = main_center_y - v_height // 2
    main_right_top_x = main_center_x + v_width // 2
    main_right_top_y = main_center_y - v_height // 2
    main_bottom_x = main_center_x
    main_bottom_y = main_center_y + v_height // 2
    
    # Draw sharp white core
    draw.line([main_left_top_x, main_left_top_y, main_bottom_x, main_bottom_y], 
              fill=neon_white, width=core_stroke)
    draw.line([main_right_top_x, main_right_top_y, main_bottom_x, main_bottom_y], 
              fill=neon_white, width=core_stroke)
    
    # Save as ICO file
    icon_path = os.path.join(os.path.dirname(__file__), 'neon_v_soundboard_icon.ico')
    
    # Create multiple sizes for the ICO file (Windows standard)
    sizes = [16, 32, 48, 64, 128, 256]
    icon_images = []
    
    for icon_size in sizes:
        resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Save the ICO file
    icon_images[0].save(icon_path, format='ICO', sizes=[(s, s) for s in sizes])
    
    print(f"✅ Neon 'V' icon created: {icon_path}")
    return icon_path

if __name__ == "__main__":
    create_neon_v_icon()
