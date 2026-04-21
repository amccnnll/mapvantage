import os
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np


def extract_info_from_filename(filename):
    """Extract date and site name from filename like 'cropped_2020-05-06 Saltflats.png'"""
    # Remove 'cropped_' prefix and file extension
    name_part = filename.replace('cropped_', '').rsplit('.', 1)[0]

    # Split on first space to separate date and site
    parts = name_part.split(' ', 1)
    if len(parts) == 2:
        date_str = parts[0]
        site_name = parts[1]

        # Format date nicely (2020-05-06 -> May 6, 2020)
        try:
            year, month, day = date_str.split('-')
            months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            formatted_date = f"{months[int(month)]} {int(day)}, {year}"
        except:
            formatted_date = date_str  # Fallback to original if parsing fails

        return formatted_date, site_name

    return filename, "Unknown Site"


def draw_north_arrow(draw, x, y, size, rotation_degrees=0, color='white', outline_color='black'):
    """Draw a north arrow at specified position with optional rotation"""

    # Convert rotation to radians (positive rotation = clockwise)
    rotation_rad = math.radians(rotation_degrees)

    # Arrow points - pointing up initially
    arrow_points = [
        (0, -size),      # Arrow tip (top)
        (-size//3, size//2),   # Left base
        (0, size//4),          # Center notch
        (size//3, size//2),    # Right base
    ]

    # Rotate and translate points
    rotated_points = []
    for px, py in arrow_points:
        # Rotate
        rx = px * math.cos(rotation_rad) - py * math.sin(rotation_rad)
        ry = px * math.sin(rotation_rad) + py * math.cos(rotation_rad)
        # Translate to final position
        rotated_points.append((x + rx, y + ry))

    # Draw arrow
    draw.polygon(rotated_points, fill=color, outline=outline_color, width=2)


def add_text_with_background(draw, text, position, font, text_color='white', bg_color='black', padding=5):
    """Add text with a solid background for better readability"""

    # Get text dimensions
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x, y = position

    # Draw solid background rectangle
    bg_box = [
        x - padding,
        y - padding,
        x + text_width + padding,
        y + text_height + padding
    ]

    draw.rectangle(bg_box, fill=bg_color, outline='white', width=1)

    # Draw text
    draw.text((x, y), text, font=font, fill=text_color)


def annotate_image(image_path, output_path, site_name, north_rotation=0):
    """Annotate a single image with date, site name, and north arrow"""

    # Load image
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Extract info from filename
    filename = os.path.basename(image_path)
    date_str, extracted_site = extract_info_from_filename(filename)

    # Use provided site name or extracted one
    display_site = site_name if site_name else extracted_site

    # Try to load a nice font, fallback to default
    try:
        # Try different common font locations
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "arial.ttf",  # Windows
        ]
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, size=24)
                break
            except:
                continue

        if font is None:
            font = ImageFont.load_default()

    except:
        font = ImageFont.load_default()

    # Get image dimensions
    width, height = img.size

    # Add date and site name (top-left)
    title_text = f"{display_site} - {date_str}"
    add_text_with_background(draw, title_text, (20, 20), font)

    # Add north arrow (top-right)
    arrow_x = width - 60
    arrow_y = 60
    arrow_size = 25

    # Draw "N" label first (use same font, smaller size if possible)
    try:
        n_font = ImageFont.truetype("arial.ttf", size=16)
    except:
        n_font = font  # Use same font as title

    add_text_with_background(
        draw, "N", (arrow_x - 8, arrow_y + arrow_size + 10), n_font)

    # Draw north arrow with specified rotation
    draw_north_arrow(draw, arrow_x, arrow_y, arrow_size,
                     rotation_degrees=north_rotation)

    # Save annotated image
    img.save(output_path)
    print(f"✅ Annotated: {os.path.basename(output_path)}")


def process_site_folder(input_folder, output_folder, site_name, north_rotation=0):
    """Process all images in a site folder"""

    if not os.path.exists(input_folder):
        print(f"❌ Input folder not found: {input_folder}")
        return

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)

    # Get all image files
    image_files = [f for f in os.listdir(input_folder)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        print(f"❌ No image files found in {input_folder}")
        return

    print(f"\n=== Processing {len(image_files)} images for {site_name} ===")
    print(f"North arrow rotation: {north_rotation}°")

    for filename in sorted(image_files):
        input_path = os.path.join(input_folder, filename)
        output_filename = filename.replace('cropped_', 'annotated_')
        output_path = os.path.join(output_folder, output_filename)

        try:
            annotate_image(input_path, output_path, site_name, north_rotation)
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")


def main():
    # Base data folder
    base_data_folder = "./data"  # Adjust if needed

    # Site configurations
    sites = [
        {
            'name': 'Kincardine',
            'input_folder': os.path.join(base_data_folder, 'cropped_kincardine'),
            'output_folder': os.path.join(base_data_folder, 'annotated_kincardine'),
            'north_rotation': 0  # True north (straight up)
        },
        {
            'name': 'Skinflats',
            'input_folder': os.path.join(base_data_folder, 'cropped_skinflats'),
            'output_folder': os.path.join(base_data_folder, 'annotated_skinflats'),
            'north_rotation': -72  # 72 degrees to the left (counter-clockwise)
        }
    ]

    print("=== Image Annotation Tool ===")
    print("Adding dates, site names, and north arrows to cropped images")

    for site in sites:
        process_site_folder(
            site['input_folder'],
            site['output_folder'],
            site['name'],
            site['north_rotation']
        )

    print(f"\n{'='*50}")
    print("✅ Annotation complete!")
    print("Check the annotated_kincardine and annotated_skinflats folders.")


if __name__ == "__main__":
    main()
