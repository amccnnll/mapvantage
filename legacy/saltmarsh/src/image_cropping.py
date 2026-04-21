import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import numpy as np


def get_images_by_site(data_folder):
    """Get all images organized by site name"""
    images_by_site = {}

    for filename in os.listdir(data_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Extract site name from filename "YYYY-MM-DD Sitename"
            parts = filename.split(' ', 1)  # Split on first space only
            if len(parts) == 2:
                site_name = parts[1].rsplit('.', 1)[0]  # Remove file extension

                if site_name not in images_by_site:
                    images_by_site[site_name] = []
                images_by_site[site_name].append(filename)

    return images_by_site


def interactive_crop_selector(image_path, site_name):
    """Interactive tool to select crop area"""
    print(f"\n=== Selecting crop area for {site_name} ===")
    print("Instructions:")
    print("1. The image will display")
    print("2. Click TWO points to define opposite corners of crop area")
    print("3. A red rectangle will show your selection")
    print("4. Close the window when satisfied")

    # Load and display image
    img = Image.open(image_path)
    img_array = np.array(img)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img_array)
    ax.set_title(f'{site_name} - Click 2 points to define crop area')

    # Get two corner points
    print(f"\nClick TWO corner points on the {site_name} image...")
    coords = plt.ginput(2, timeout=0)  # Wait indefinitely for clicks

    if len(coords) != 2:
        print("Error: Need exactly 2 points")
        return None

    # Calculate crop bounds
    x1, y1 = int(coords[0][0]), int(coords[0][1])
    x2, y2 = int(coords[1][0]), int(coords[1][1])

    # Ensure proper order (top-left to bottom-right)
    left = min(x1, x2)
    right = max(x1, x2)
    top = min(y1, y2)
    bottom = max(y1, y2)

    # Draw rectangle to show selection
    width = right - left
    height = bottom - top
    rect = patches.Rectangle((left, top), width, height,
                             linewidth=3, edgecolor='red', facecolor='none')
    ax.add_patch(rect)
    ax.set_title(f'{site_name} - Crop area selected (close window when ready)')

    plt.show(block=True)  # Block until window closed

    crop_bounds = {
        'left': left,
        'top': top,
        'right': right,
        'bottom': bottom,
        'width': width,
        'height': height
    }

    print(f"Crop bounds for {site_name}:")
    print(f"  Left: {left}, Top: {top}")
    print(f"  Right: {right}, Bottom: {bottom}")
    print(f"  Size: {width} x {height} pixels")

    return crop_bounds


def preview_crop(image_path, crop_bounds, site_name):
    """Preview the cropped result"""
    img = Image.open(image_path)

    # Apply crop
    cropped = img.crop((crop_bounds['left'], crop_bounds['top'],
                       crop_bounds['right'], crop_bounds['bottom']))

    # Show before and after
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Original with crop area highlighted
    ax1.imshow(img)
    rect = patches.Rectangle((crop_bounds['left'], crop_bounds['top']),
                             crop_bounds['width'], crop_bounds['height'],
                             linewidth=2, edgecolor='red', facecolor='none')
    ax1.add_patch(rect)
    ax1.set_title(f'{site_name} - Original with crop area')
    ax1.axis('off')

    # Cropped result
    ax2.imshow(cropped)
    ax2.set_title(f'{site_name} - Cropped result')
    ax2.axis('off')

    plt.tight_layout()
    plt.show()

    return cropped


def batch_crop_site(data_folder, site_name, image_files, crop_bounds, output_folder):
    """Apply crop bounds to all images of a site"""

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    print(
        f"\n=== Batch processing {len(image_files)} images for {site_name} ===")

    for filename in image_files:
        print(f"Processing: {filename}")

        # Load image
        img_path = os.path.join(data_folder, filename)
        img = Image.open(img_path)

        # Apply crop
        cropped = img.crop((crop_bounds['left'], crop_bounds['top'],
                           crop_bounds['right'], crop_bounds['bottom']))

        # Save cropped image
        output_path = os.path.join(output_folder, f"cropped_{filename}")
        cropped.save(output_path)

    print(
        f"✅ Completed! All {site_name} images cropped and saved to {output_folder}")

# Main workflow


def main():
    # Try different possible paths based on where script is run from
    possible_data_paths = [
        "./data",      # Running from /saltmarshes/
        "../data",     # Running from /saltmarshes/src/
        "data"         # Alternative format
    ]

    data_folder = None

    print("Looking for data folder...")
    for path in possible_data_paths:
        print(f"  Trying: {path}")
        if os.path.exists(path):
            data_folder = path
            print(f"  ✅ Found data folder at: {path}")
            break
        else:
            print(f"  ❌ Not found")

    if data_folder is None:
        print("\nError: Could not find data folder.")
        print(f"Current working directory: {os.getcwd()}")
        print("Make sure you have a 'data' folder with your images.")
        return

    # Get images by site
    images_by_site = get_images_by_site(data_folder)

    print("Found the following sites:")
    for site, files in images_by_site.items():
        print(f"  {site}: {len(files)} images")

    # Store crop bounds for each site
    crop_bounds_by_site = {}

    # Process each site
    for site_name, image_files in images_by_site.items():
        print(f"\n{'='*50}")
        print(f"Processing site: {site_name}")

        # Use first image as reference for cropping
        reference_image = os.path.join(data_folder, image_files[0])
        print(f"Using reference image: {image_files[0]}")

        # Get crop bounds interactively
        crop_bounds = interactive_crop_selector(reference_image, site_name)

        if crop_bounds is None:
            print(f"Skipping {site_name} - no valid crop area selected")
            continue

        # Preview the crop
        print(f"\nPreviewing crop for {site_name}...")
        preview_crop(reference_image, crop_bounds, site_name)

        # Confirm before batch processing
        confirm = input(
            f"\nProceed with batch cropping all {len(image_files)} {site_name} images? (y/n): ")

        if confirm.lower() == 'y':
            # Create output folder in same directory as data folder
            if data_folder == "./data":
                # Running from main
                output_folder = f"./cropped_{site_name.lower()}"
            elif data_folder == "../data":
                # Running from src
                output_folder = f"../cropped_{site_name.lower()}"
            else:
                output_folder = f"cropped_{site_name.lower()}"     # Fallback

            batch_crop_site(data_folder, site_name, image_files,
                            crop_bounds, output_folder)
            crop_bounds_by_site[site_name] = crop_bounds
        else:
            print(f"Skipped batch processing for {site_name}")

    print(f"\n{'='*50}")
    print("Summary of crop bounds:")
    for site, bounds in crop_bounds_by_site.items():
        print(
            f"{site}: {bounds['width']}x{bounds['height']} at ({bounds['left']}, {bounds['top']})")


if __name__ == "__main__":
    main()
