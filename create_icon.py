#!/usr/bin/env python3
"""
Create a custom soundboard icon with an 'S' shaped like a musical note
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_soundboard_icon():
    # Icon dimensions (standard Windows icon size)
    size = 256
    
    # Create a new image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors
    bg_color = (30, 30, 30, 220)  # Dark background with slight transparency
    note_color = (255, 215, 0, 255)  # Gold color for the musical note
    accent_color = (255, 165, 0, 255)  # Orange accent
    
    # Draw background circle
    margin = 10
    draw.ellipse([margin, margin, size-margin, size-margin], 
                fill=bg_color, outline=accent_color, width=3)
    
    # Draw the 'S' shaped like a musical note
    center_x = size // 2
    center_y = size // 2
    
    # Main S curve (musical note style)
    # Top curve
    draw.arc([center_x-60, center_y-80, center_x+20, center_y-20], 
             start=180, end=0, fill=note_color, width=12)
    
    # Bottom curve
    draw.arc([center_x-20, center_y+20, center_x+60, center_y+80], 
             start=0, end=180, fill=note_color, width=12)
    
    # Connecting line
    draw.line([center_x-20, center_y-50, center_x+20, center_y+50], 
              fill=note_color, width=12)
    
    # Musical note stem (make it look more like a note)
    draw.line([center_x+45, center_y-70, center_x+45, center_y-10], 
              fill=note_color, width=8)
    
    # Note head (ellipse at bottom)
    draw.ellipse([center_x+35, center_y-20, center_x+55, center_y-5], 
                fill=note_color)
    
    # Add some musical accent dots
    for i, (x_offset, y_offset) in enumerate([(70, -40), (85, -25), (95, -10)]):
        radius = 4 - i
        draw.ellipse([center_x+x_offset-radius, center_y+y_offset-radius,
                     center_x+x_offset+radius, center_y+y_offset+radius], 
                    fill=accent_color)
    
    # Add subtle sound waves
    for i in range(3):
        offset = 15 + i * 8
        draw.arc([center_x-90-offset, center_y-30, center_x-60-offset, center_y+30], 
                start=270, end=90, fill=(255, 255, 255, 100-i*30), width=2)
    
    # Save as ICO file
    icon_path = os.path.join(os.path.dirname(__file__), 'soundboard_icon.ico')
    
    # Create multiple sizes for the ICO file (Windows standard)
    sizes = [16, 32, 48, 64, 128, 256]
    icon_images = []
    
    for icon_size in sizes:
        resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Save the ICO file
    icon_images[0].save(icon_path, format='ICO', sizes=[(s, s) for s in sizes])
    
    print(f"✅ Custom soundboard icon created: {icon_path}")
    return icon_path

if __name__ == "__main__":
    create_soundboard_icon()
