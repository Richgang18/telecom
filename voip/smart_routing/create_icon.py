#!/usr/bin/env python3
"""
Create a simple icon for the Smart Outbound Dialer application.
This creates a basic ICO file that can be used for the desktop shortcut.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a simple phone icon"""
    # Create a 256x256 image with transparent background
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a phone icon
    # Background circle
    circle_color = (33, 150, 243, 255)  # Blue
    draw.ellipse([20, 20, size-20, size-20], fill=circle_color)
    
    # Phone handset (simplified)
    phone_color = (255, 255, 255, 255)  # White
    
    # Draw phone receiver shape
    # Top part
    draw.ellipse([60, 60, 100, 100], fill=phone_color)
    draw.rectangle([70, 80, 90, 140], fill=phone_color)
    
    # Bottom part
    draw.ellipse([156, 156, 196, 196], fill=phone_color)
    draw.rectangle([166, 116, 186, 176], fill=phone_color)
    
    # Connecting line
    draw.line([90, 100, 166, 156], fill=phone_color, width=20)
    
    # Add call symbol (arrow)
    arrow_color = (76, 175, 80, 255)  # Green
    draw.polygon([
        (180, 80),
        (220, 80),
        (200, 60),
        (240, 60),
        (240, 100),
        (200, 100),
        (220, 80)
    ], fill=arrow_color)
    
    # Save as ICO file with multiple sizes
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    
    # Create multiple sizes for better quality
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []
    
    for icon_size in sizes:
        resized = img.resize(icon_size, Image.Resampling.LANCZOS)
        images.append(resized)
    
    # Save as ICO
    images[0].save(icon_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=images[1:])
    
    print(f"✓ Icon created: {icon_path}")
    return icon_path

def create_simple_icon_without_pil():
    """Create a very basic ICO file without PIL (fallback)"""
    # This creates a minimal 16x16 icon
    icon_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    
    # ICO file header for a 16x16 32-bit icon
    ico_header = bytes([
        0, 0,  # Reserved
        1, 0,  # Type (1 = ICO)
        1, 0,  # Number of images
        16,    # Width
        16,    # Height
        0,     # Color palette
        0,     # Reserved
        1, 0,  # Color planes
        32, 0, # Bits per pixel
        0x28, 0x04, 0, 0,  # Size of image data
        22, 0, 0, 0,  # Offset to image data
    ])
    
    # BMP header
    bmp_header = bytes([
        40, 0, 0, 0,  # Header size
        16, 0, 0, 0,  # Width
        32, 0, 0, 0,  # Height (doubled for ICO)
        1, 0,         # Planes
        32, 0,        # Bits per pixel
        0, 0, 0, 0,   # Compression
        0, 0, 0, 0,   # Image size
        0, 0, 0, 0,   # X pixels per meter
        0, 0, 0, 0,   # Y pixels per meter
        0, 0, 0, 0,   # Colors used
        0, 0, 0, 0,   # Important colors
    ])
    
    # Create a simple blue phone icon (16x16 pixels)
    pixels = []
    for y in range(16):
        for x in range(16):
            # Create a simple phone shape
            if (x >= 4 and x <= 11 and y >= 4 and y <= 11):
                # Blue phone
                pixels.extend([66, 150, 243, 255])  # BGRA format
            else:
                # Transparent
                pixels.extend([0, 0, 0, 0])
    
    # AND mask (all transparent)
    and_mask = bytes([0] * 32)
    
    # Write ICO file
    with open(icon_path, 'wb') as f:
        f.write(ico_header)
        f.write(bmp_header)
        f.write(bytes(pixels))
        f.write(and_mask)
    
    print(f"✓ Basic icon created: {icon_path}")
    return icon_path

if __name__ == "__main__":
    try:
        # Try with PIL first
        from PIL import Image, ImageDraw
        icon_path = create_icon()
        print("Icon created successfully with PIL!")
    except ImportError:
        # Fallback to basic icon
        icon_path = create_simple_icon_without_pil()
        print("Basic icon created successfully!")
    except Exception as e:
        # If all else fails, create basic icon
        print(f"Note: {e}")
        icon_path = create_simple_icon_without_pil()
        print("Basic icon created successfully!")
