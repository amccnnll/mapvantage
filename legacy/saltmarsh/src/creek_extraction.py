import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from PIL import Image
from skimage import filters, segmentation, morphology, measure
from skimage.filters import threshold_otsu, threshold_local
from skimage.morphology import skeletonize, remove_small_objects, disk, closing, opening
from skimage.segmentation import watershed
from scipy import ndimage
import glob


def load_test_image(image_path):
    """Load and prepare image for processing"""

    # Load image
    img = Image.open(image_path)

    # Convert to RGB if needed (removes alpha channel)
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    elif img.mode == 'L':
        img = img.convert('RGB')

    img_array = np.array(img)

    # Convert to different color spaces for analysis
    if len(img_array.shape) == 3:
        # RGB image
        rgb = img_array
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    else:
        # Grayscale image (shouldn't happen now)
        gray = img_array
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)

    return {
        'original': rgb,
        'gray': gray,
        'hsv': hsv,
        'lab': lab
    }


def method1_edge_detection(images, low_thresh=50, high_thresh=150):
    """Method 1: Canny edge detection + morphological operations"""

    gray = images['gray']

    # Apply Canny edge detection
    edges = cv2.Canny(gray, low_thresh, high_thresh)

    # Morphological operations to connect creek segments
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Remove small noise
    edges_cleaned = remove_small_objects(
        edges_closed.astype(bool), min_size=50)

    # Skeletonize to get centerlines
    skeleton = skeletonize(edges_cleaned)

    return {
        'raw_edges': edges,
        'closed_edges': edges_closed,
        'cleaned_edges': edges_cleaned.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'Edge Detection'
    }


def method2_water_segmentation(images, h_min=0, h_max=180, s_min=30, v_max=100):
    """Method 2: Color-based water segmentation"""

    hsv = images['hsv']

    # Define water color range (typically darker, more saturated)
    lower_water = np.array([h_min, s_min, 0])
    upper_water = np.array([h_max, 255, v_max])

    # Create water mask
    water_mask = cv2.inRange(hsv, lower_water, upper_water)

    # Morphological operations to clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    water_cleaned = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, kernel)
    water_cleaned = cv2.morphologyEx(water_cleaned, cv2.MORPH_CLOSE, kernel)

    # Remove small objects
    water_cleaned = remove_small_objects(
        water_cleaned.astype(bool), min_size=100)

    # Get creek centerlines
    skeleton = skeletonize(water_cleaned)

    return {
        'water_mask': water_mask,
        'water_cleaned': water_cleaned.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'Water Segmentation'
    }


def method3_adaptive_threshold(images, block_size=25, offset=5):
    """Method 3: Adaptive thresholding for local contrast"""

    gray = images['gray']

    # Apply adaptive threshold
    adaptive_thresh = threshold_local(
        gray, block_size=block_size, offset=offset)
    binary = gray < adaptive_thresh

    # Invert if needed (creeks should be dark)
    if np.sum(binary) > binary.size / 2:
        binary = ~binary

    # Clean up
    binary_cleaned = remove_small_objects(binary, min_size=100)
    binary_cleaned = morphology.closing(binary_cleaned, disk(3))

    # Skeletonize
    skeleton = skeletonize(binary_cleaned)

    return {
        'adaptive_thresh': (gray < adaptive_thresh).astype(np.uint8) * 255,
        'binary_cleaned': binary_cleaned.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'Adaptive Threshold'
    }


def method4_watershed(images, markers_threshold=0.3):
    """Method 4: Watershed segmentation"""

    gray = images['gray']

    # Create markers for watershed using simple gradient
    # Calculate gradient using Sobel
    grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient = np.sqrt(grad_x**2 + grad_y**2)

    # Markers for sure background and sure foreground
    markers = np.zeros_like(gray)
    markers[gray < np.percentile(gray, 20)] = 1  # Dark areas (potential water)
    markers[gray > np.percentile(gray, 80)] = 2  # Light areas (sure land)

    # Apply watershed
    labels = watershed(gradient, markers)

    # Extract water regions (label 1)
    water_regions = (labels == 1)

    # Clean and skeletonize
    water_cleaned = remove_small_objects(water_regions, min_size=100)
    skeleton = skeletonize(water_cleaned)

    return {
        'gradient': gradient,
        'markers': markers,
        'labels': labels,
        'water_regions': water_regions.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'Watershed'
    }


def method5_lab_contrast(images):
    """Method 5: LAB color space contrast enhancement"""

    lab = images['lab']

    # Use L channel (lightness) - creeks should be darker
    l_channel = lab[:, :, 0]

    # Apply Otsu threshold on L channel
    thresh = threshold_otsu(l_channel)
    binary = l_channel < thresh

    # Clean up
    binary_cleaned = remove_small_objects(binary, min_size=50)
    binary_cleaned = morphology.closing(binary_cleaned, disk(2))
    binary_cleaned = morphology.opening(binary_cleaned, disk(1))

    # Skeletonize
    skeleton = skeletonize(binary_cleaned)

    return {
        'l_channel': l_channel,
        'binary': binary.astype(np.uint8) * 255,
        'binary_cleaned': binary_cleaned.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'LAB Contrast'
    }


def run_all_methods(image_path):
    """Run all creek extraction methods on a test image"""

    print(
        f"Testing creek extraction methods on: {os.path.basename(image_path)}")

    # Load image
    images = load_test_image(image_path)

    # Run all methods
    results = {}

    try:
        results['method1'] = method1_edge_detection(images)
        print("✅ Method 1: Edge detection completed")
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")

    try:
        results['method2'] = method2_water_segmentation(images)
        print("✅ Method 2: Water segmentation completed")
    except Exception as e:
        print(f"❌ Method 2 failed: {e}")

    try:
        results['method3'] = method3_adaptive_threshold(images)
        print("✅ Method 3: Adaptive threshold completed")
    except Exception as e:
        print(f"❌ Method 3 failed: {e}")

    try:
        results['method4'] = method4_watershed(images)
        print("✅ Method 4: Watershed completed")
    except Exception as e:
        print(f"❌ Method 4 failed: {e}")

    try:
        results['method5'] = method5_lab_contrast(images)
        print("✅ Method 5: LAB contrast completed")
    except Exception as e:
        print(f"❌ Method 5 failed: {e}")

    return images, results


def plot_comparison(images, results, save_path=None):
    """Create comparison plot of all methods"""

    n_methods = len(results)
    if n_methods == 0:
        print("No results to plot!")
        return

    # Create subplot grid
    fig, axes = plt.subplots(
        2, n_methods + 1, figsize=(4 * (n_methods + 1), 8))

    # Original image in first column
    axes[0, 0].imshow(images['original'])
    axes[0, 0].set_title('Original Image')
    axes[0, 0].axis('off')

    axes[1, 0].imshow(images['gray'], cmap='gray')
    axes[1, 0].set_title('Grayscale')
    axes[1, 0].axis('off')

    # Results for each method
    for i, (method_key, result) in enumerate(results.items()):
        col = i + 1

        # Show main result (usually cleaned binary)
        if 'binary_cleaned' in result:
            axes[0, col].imshow(result['binary_cleaned'], cmap='gray')
        elif 'water_cleaned' in result:
            axes[0, col].imshow(result['water_cleaned'], cmap='gray')
        elif 'cleaned_edges' in result:
            axes[0, col].imshow(result['cleaned_edges'], cmap='gray')
        else:
            axes[0, col].imshow(np.zeros_like(images['gray']), cmap='gray')

        axes[0, col].set_title(f"{result['name']}\n(Processed)")
        axes[0, col].axis('off')

        # Show skeleton/centerlines
        if 'skeleton' in result:
            # Overlay skeleton on original for better visualization
            overlay = images['original'].copy()
            skeleton_coords = np.where(result['skeleton'] > 0)
            if len(skeleton_coords[0]) > 0:
                # Now all images are RGB (3 channels)
                overlay[skeleton_coords[0], skeleton_coords[1]] = [
                    255, 0, 0]  # Red centerlines

            axes[1, col].imshow(overlay)
            axes[1, col].set_title(f"{result['name']}\n(Centerlines)")
        else:
            axes[1, col].imshow(images['original'])
            axes[1, col].set_title(f"{result['name']}\n(No skeleton)")

        axes[1, col].axis('off')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Comparison saved to: {save_path}")

    plt.show()


def test_on_multiple_images(site_folder, n_images=3, output_folder="./creek_extraction_tests"):
    """Test methods on multiple images from a site"""

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)

    # Get image files
    image_files = glob.glob(os.path.join(site_folder, "*.png")) + \
        glob.glob(os.path.join(site_folder, "*.jpg"))
    image_files = sorted(image_files)[:n_images]  # Take first n images

    if len(image_files) == 0:
        print(f"No images found in {site_folder}")
        return

    print(f"\nTesting on {len(image_files)} images from {site_folder}")
    print("="*60)

    for i, img_path in enumerate(image_files):
        print(
            f"\nProcessing image {i+1}/{len(image_files)}: {os.path.basename(img_path)}")

        try:
            # Run all methods
            images, results = run_all_methods(img_path)

            # Create comparison plot
            output_name = f"comparison_{os.path.basename(img_path).split('.')[0]}.png"
            output_path = os.path.join(output_folder, output_name)

            plot_comparison(images, results, save_path=output_path)

        except Exception as e:
            print(f"❌ Error processing {img_path}: {e}")
            continue

    print(f"\n✅ Testing complete! Check results in {output_folder}")


def interactive_parameter_tuning(image_path):
    """Interactive tool to tune parameters for best results"""

    print("=== Interactive Parameter Tuning ===")
    print(f"Testing on: {os.path.basename(image_path)}")

    images = load_test_image(image_path)

    while True:
        print("\nWhich method would you like to tune?")
        print("1. Edge Detection (Canny thresholds)")
        print("2. Water Segmentation (HSV ranges)")
        print("3. Adaptive Threshold (block size, offset)")
        print("4. Exit")

        choice = input("Enter choice (1-4): ").strip()

        if choice == '1':
            print("\nTuning Edge Detection...")
            low = int(input("Low threshold (default 50): ") or "50")
            high = int(input("High threshold (default 150): ") or "150")

            result = method1_edge_detection(images, low, high)

            plt.figure(figsize=(12, 4))
            plt.subplot(1, 3, 1)
            plt.imshow(images['original'])
            plt.title('Original')
            plt.axis('off')

            plt.subplot(1, 3, 2)
            plt.imshow(result['cleaned_edges'], cmap='gray')
            plt.title('Cleaned Edges')
            plt.axis('off')

            plt.subplot(1, 3, 3)
            overlay = images['original'].copy()
            skeleton_coords = np.where(result['skeleton'] > 0)
            if len(skeleton_coords[0]) > 0:
                # Handle both RGB and RGBA images
                if overlay.shape[2] == 4:  # RGBA
                    overlay[skeleton_coords[0], skeleton_coords[1]] = [
                        255, 0, 0, 255]
                else:  # RGB
                    overlay[skeleton_coords[0],
                            skeleton_coords[1]] = [255, 0, 0]
            plt.imshow(overlay)
            plt.title('Centerlines')
            plt.axis('off')

            plt.tight_layout()
            plt.show()

        elif choice == '2':
            print("\nTuning Water Segmentation...")
            s_min = int(input("Min saturation (default 30): ") or "30")
            v_max = int(input("Max value/brightness (default 100): ") or "100")

            result = method2_water_segmentation(
                images, s_min=s_min, v_max=v_max)

            plt.figure(figsize=(12, 4))
            plt.subplot(1, 3, 1)
            plt.imshow(images['original'])
            plt.title('Original')
            plt.axis('off')

            plt.subplot(1, 3, 2)
            plt.imshow(result['water_cleaned'], cmap='gray')
            plt.title('Water Mask')
            plt.axis('off')

            plt.subplot(1, 3, 3)
            overlay = images['original'].copy()
            skeleton_coords = np.where(result['skeleton'] > 0)
            if len(skeleton_coords[0]) > 0:
                # Handle both RGB and RGBA images
                if overlay.shape[2] == 4:  # RGBA
                    overlay[skeleton_coords[0], skeleton_coords[1]] = [
                        255, 0, 0, 255]
                else:  # RGB
                    overlay[skeleton_coords[0],
                            skeleton_coords[1]] = [255, 0, 0]
            plt.imshow(overlay)
            plt.title('Centerlines')
            plt.axis('off')

            plt.tight_layout()
            plt.show()

        elif choice == '3':
            print("\nTuning Adaptive Threshold...")
            block_size = int(
                input("Block size (odd number, default 25): ") or "25")
            offset = int(input("Offset (default 5): ") or "5")

            result = method3_adaptive_threshold(images, block_size, offset)

            plt.figure(figsize=(12, 4))
            plt.subplot(1, 3, 1)
            plt.imshow(images['original'])
            plt.title('Original')
            plt.axis('off')

            plt.subplot(1, 3, 2)
            plt.imshow(result['binary_cleaned'], cmap='gray')
            plt.title('Binary Cleaned')
            plt.axis('off')

            plt.subplot(1, 3, 3)
            overlay = images['original'].copy()
            skeleton_coords = np.where(result['skeleton'] > 0)
            if len(skeleton_coords[0]) > 0:
                overlay[skeleton_coords[0], skeleton_coords[1]] = [255, 0, 0]
            plt.imshow(overlay)
            plt.title('Centerlines')
            plt.axis('off')

            plt.tight_layout()
            plt.show()

        elif choice == '4':
            break
        else:
            print("Invalid choice!")


def main():
    """Main function to run creek extraction experiments"""

    print("=== Creek Extraction Experiment Tool ===")
    print()

    # Default paths
    kincardine_folder = "./data/annotated_kincardine"
    skinflats_folder = "./data/annotated_skinflats"

    # Check which folders exist
    sites_available = []
    if os.path.exists(kincardine_folder):
        sites_available.append(("Kincardine", kincardine_folder))
    if os.path.exists(skinflats_folder):
        sites_available.append(("Skinflats", skinflats_folder))

    if not sites_available:
        print("❌ No annotated image folders found!")
        print("Make sure you have ./data/annotated_kincardine/ and/or ./data/annotated_skinflats/")
        return

    print("Available sites:")
    for i, (name, folder) in enumerate(sites_available):
        n_images = len(glob.glob(os.path.join(folder, "*.png")) +
                       glob.glob(os.path.join(folder, "*.jpg")))
        print(f"{i+1}. {name} ({n_images} images)")

    print()
    print("What would you like to do?")
    print("1. Test all methods on a few images from each site")
    print("2. Interactive parameter tuning on a single image")
    print("3. Test all methods on a single image")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        # Test on multiple images from all sites
        for name, folder in sites_available:
            test_on_multiple_images(folder, n_images=2,
                                    output_folder=f"./creek_tests_{name.lower()}")

    elif choice == '2':
        # Interactive tuning
        print("\nSelect site for interactive tuning:")
        for i, (name, folder) in enumerate(sites_available):
            print(f"{i+1}. {name}")

        site_choice = int(input("Enter site number: ")) - 1
        if 0 <= site_choice < len(sites_available):
            folder = sites_available[site_choice][1]
            image_files = glob.glob(os.path.join(
                folder, "*.png")) + glob.glob(os.path.join(folder, "*.jpg"))

            if image_files:
                # Use first image for tuning
                interactive_parameter_tuning(sorted(image_files)[0])
            else:
                print("No images found in selected folder!")

    elif choice == '3':
        # Single image test
        print("\nSelect site:")
        for i, (name, folder) in enumerate(sites_available):
            print(f"{i+1}. {name}")

        site_choice = int(input("Enter site number: ")) - 1
        if 0 <= site_choice < len(sites_available):
            folder = sites_available[site_choice][1]
            image_files = sorted(glob.glob(os.path.join(
                folder, "*.png")) + glob.glob(os.path.join(folder, "*.jpg")))

            if image_files:
                print(f"\nUsing image: {os.path.basename(image_files[0])}")
                images, results = run_all_methods(image_files[0])
                plot_comparison(images, results)
            else:
                print("No images found in selected folder!")


if __name__ == "__main__":
    main()
