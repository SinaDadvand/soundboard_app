#!/usr/bin/env python3
"""
Create a custom soundboard icon using the golden treble clef design
"""

from PIL import Image, ImageDraw
import os

def create_treble_clef_icon():
    # Icon dimensions (standard Windows icon size)
    size = 256
    
    # Create a new image with dark background
    img = Image.new('RGBA', (size, size), (30, 30, 30, 255))  # Dark background
    draw = ImageDraw.Draw(img)
    
    # Colors
    gold_color = (255, 215, 0, 255)  # Gold color for the treble clef
    
    # Scale factor to fit the treble clef nicely in the icon
    center_x = size // 2
    center_y = size // 2
    scale = 0.8  # Make it slightly smaller to have some padding
    
    # Draw the treble clef shape (simplified version)
    # Main curved body of the treble clef
    # Top loop
    draw.ellipse([center_x-30*scale, center_y-80*scale, center_x+30*scale, center_y-20*scale], 
                outline=gold_color, width=int(8*scale))
    
    # Middle section - vertical line
    draw.line([center_x+20*scale, center_y-50*scale, center_x+20*scale, center_y+60*scale], 
              fill=gold_color, width=int(8*scale))
    
    # Bottom spiral
    draw.arc([center_x-40*scale, center_y+30*scale, center_x+40*scale, center_y+90*scale], 
             start=0, end=270, fill=gold_color, width=int(8*scale))
    
    # Inner spiral detail
    draw.arc([center_x-20*scale, center_y+40*scale, center_x+20*scale, center_y+80*scale], 
             start=180, end=90, fill=gold_color, width=int(6*scale))
    
    # Top curl detail
    draw.arc([center_x-15*scale, center_y-70*scale, center_x+25*scale, center_y-30*scale], 
             start=90, end=270, fill=gold_color, width=int(6*scale))
    
    # Note head at bottom
    draw.ellipse([center_x+15*scale, center_y+55*scale, center_x+35*scale, center_y+75*scale], 
                fill=gold_color)
    
    # Save as ICO file
    icon_path = os.path.join(os.path.dirname(__file__), 'treble_clef_icon.ico')
    
    # Create multiple sizes for the ICO file (Windows standard)
    sizes = [16, 32, 48, 64, 128, 256]
    icon_images = []
    
    for icon_size in sizes:
        resized = img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        icon_images.append(resized)
    
    # Save the ICO file
    icon_images[0].save(icon_path, format='ICO', sizes=[(s, s) for s in sizes])
    
    print(f"✅ Treble clef icon created: {icon_path}")
    return icon_path

if __name__ == "__main__":
    create_treble_clef_icon()
