import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.widgets import Slider, Button
from PIL import Image
from skimage.filters import threshold_local
from skimage.morphology import skeletonize, remove_small_objects, disk, closing, opening, dilation, erosion
from skimage import morphology
import json
import glob


def load_image_for_processing(image_path):
    """Load and prepare image, ensuring RGB format"""
    img = Image.open(image_path)
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    elif img.mode == 'L':
        img = img.convert('RGB')

    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    return {
        'original': img_array,
        'gray': gray
    }


def create_polygon_mask(image_shape, polygon_points):
    """Create a binary mask from polygon points"""
    mask = np.zeros(image_shape[:2], dtype=np.uint8)

    if len(polygon_points) >= 3:
        # Convert to integer coordinates
        polygon_points = np.array(polygon_points, dtype=np.int32)

        # Fill polygon
        cv2.fillPoly(mask, [polygon_points], 255)

    return mask


class PolygonSelector:
    """Interactive polygon selection tool"""

    def __init__(self, image, site_name):
        self.image = image
        self.site_name = site_name
        self.points = []
        self.polygon = None
        self.fig, self.ax = plt.subplots(figsize=(12, 8))

        self.ax.imshow(image)
        self.ax.set_title(
            f'Click to define analysis area for {site_name}\n(Click points to define polygon, close window when done)')

        # Connect mouse click event
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)

    def on_click(self, event):
        """Handle mouse clicks to add polygon points"""
        if event.inaxes != self.ax:
            return

        if event.button == 1:  # Left click
            # Add point
            x, y = event.xdata, event.ydata
            self.points.append([x, y])

            # Plot the point
            self.ax.plot(x, y, 'ro', markersize=5)

            # If we have at least 2 points, draw lines
            if len(self.points) > 1:
                # Draw line to previous point
                prev_x, prev_y = self.points[-2]
                self.ax.plot([prev_x, x], [prev_y, y], 'r-', linewidth=2)

            # If we have at least 3 points, draw the closing line
            if len(self.points) >= 3:
                if self.polygon:
                    self.polygon.remove()

                # Create polygon patch
                polygon_points = np.array(self.points)
                self.polygon = Polygon(
                    polygon_points, alpha=0.3, facecolor='red', edgecolor='red')
                self.ax.add_patch(self.polygon)

            self.fig.canvas.draw()

            print(f"Added point {len(self.points)}: ({x:.0f}, {y:.0f})")

        elif event.button == 3:  # Right click - remove last point
            if self.points:
                self.points.pop()
                self.ax.clear()
                self.ax.imshow(self.image)
                self.ax.set_title(
                    f'Click to define analysis area for {site_name}\n(Click points to define polygon, close window when done)')

                # Redraw all points and lines
                for i, (x, y) in enumerate(self.points):
                    self.ax.plot(x, y, 'ro', markersize=5)
                    if i > 0:
                        prev_x, prev_y = self.points[i-1]
                        self.ax.plot([prev_x, x], [prev_y, y],
                                     'r-', linewidth=2)

                if len(self.points) >= 3:
                    polygon_points = np.array(self.points)
                    self.polygon = Polygon(
                        polygon_points, alpha=0.3, facecolor='red', edgecolor='red')
                    self.ax.add_patch(self.polygon)

                self.fig.canvas.draw()
                print(f"Removed point. {len(self.points)} points remaining.")

    def get_polygon(self):
        """Return the defined polygon points"""
        return self.points


def enhanced_adaptive_creek_extraction(images, mask=None, block_size=25, offset=5,
                                       connectivity_closing=3, connectivity_dilation=1,
                                       min_object_size=50):
    """Enhanced adaptive threshold with connectivity improvements"""

    gray = images['gray']

    # Apply adaptive threshold to the FULL image first (no mask)
    adaptive_thresh = threshold_local(
        gray, block_size=block_size, offset=offset)
    binary = gray < adaptive_thresh

    # Invert if needed (creeks should be dark/True)
    if np.sum(binary) > binary.size / 2:
        binary = ~binary

    # NOW apply the mask to the binary result (not the raw image)
    if mask is not None:
        # Erode mask slightly to avoid edge effects
        mask_eroded = erosion(mask > 0, disk(2))
        binary = binary & mask_eroded

    # Connectivity improvements

    # 1. Morphological closing to connect nearby segments
    if connectivity_closing > 0:
        binary = closing(binary, disk(connectivity_closing))

    # 2. Small dilation to help connect gaps
    if connectivity_dilation > 0:
        binary = dilation(binary, disk(connectivity_dilation))
        # Follow with erosion to maintain width
        binary = erosion(binary, disk(connectivity_dilation))

    # 3. Remove small noise objects
    binary_cleaned = remove_small_objects(binary, min_size=min_object_size)

    # 4. Fill small holes within creek areas
    binary_filled = morphology.remove_small_holes(
        binary_cleaned, area_threshold=20)

    # 5. Final cleanup - opening to smooth
    binary_final = opening(binary_filled, disk(1))

    # Apply mask one final time to ensure clean boundaries
    if mask is not None:
        mask_eroded = erosion(mask > 0, disk(2))
        binary_final = binary_final & mask_eroded

    # Skeletonize to get centerlines
    skeleton = skeletonize(binary_final)

    return {
        'adaptive_thresh': (gray < adaptive_thresh).astype(np.uint8) * 255,
        'binary_raw': binary.astype(np.uint8) * 255,
        'binary_cleaned': binary_cleaned.astype(np.uint8) * 255,
        'binary_filled': binary_filled.astype(np.uint8) * 255,
        'binary_final': binary_final.astype(np.uint8) * 255,
        'skeleton': skeleton.astype(np.uint8) * 255,
        'name': 'Enhanced Adaptive'
    }


class CreekTuningInterface:
    """Interactive interface for tuning creek extraction parameters"""

    def __init__(self, image_path, mask_points=None):
        self.image_path = image_path
        self.images = load_image_for_processing(image_path)
        self.mask_points = mask_points
        self.mask = None

        if mask_points and len(mask_points) >= 3:
            self.mask = create_polygon_mask(
                self.images['original'].shape, mask_points)

        # Initial parameters
        self.params = {
            'block_size': 25,
            'offset': 5,
            'connectivity_closing': 3,
            'connectivity_dilation': 1,
            'min_object_size': 50
        }

        self.setup_interface()
        self.update_display()

    def setup_interface(self):
        """Setup the matplotlib interface with sliders"""

        # Create figure with subplots
        self.fig = plt.figure(figsize=(16, 10))

        # Image displays
        self.ax_original = plt.subplot(2, 3, 1)
        self.ax_binary = plt.subplot(2, 3, 2)
        self.ax_skeleton = plt.subplot(2, 3, 3)
        self.ax_overlay = plt.subplot(2, 3, 4)
        # Wide subplot for processing stages
        self.ax_stages = plt.subplot(2, 3, (5, 6))

        # Create sliders
        slider_height = 0.03
        slider_width = 0.3
        slider_left = 0.1

        # Block size slider (must be odd)
        ax_block_size = plt.axes(
            [slider_left, 0.02, slider_width, slider_height])
        self.slider_block_size = Slider(ax_block_size, 'Block Size', 5, 101,
                                        valinit=self.params['block_size'], valstep=2)

        # Offset slider
        ax_offset = plt.axes([slider_left, 0.06, slider_width, slider_height])
        self.slider_offset = Slider(ax_offset, 'Offset', -20, 20,
                                    valinit=self.params['offset'], valstep=1)

        # Connectivity closing slider
        ax_closing = plt.axes([slider_left, 0.10, slider_width, slider_height])
        self.slider_closing = Slider(ax_closing, 'Connectivity', 0, 10,
                                     valinit=self.params['connectivity_closing'], valstep=1)

        # Connectivity dilation slider
        ax_dilation = plt.axes(
            [slider_left, 0.14, slider_width, slider_height])
        self.slider_dilation = Slider(ax_dilation, 'Gap Closing', 0, 5,
                                      valinit=self.params['connectivity_dilation'], valstep=1)

        # Min object size slider
        ax_min_size = plt.axes(
            [slider_left, 0.18, slider_width, slider_height])
        self.slider_min_size = Slider(ax_min_size, 'Min Size', 10, 200,
                                      valinit=self.params['min_object_size'], valstep=5)

        # Connect slider events
        self.slider_block_size.on_changed(self.update_params)
        self.slider_offset.on_changed(self.update_params)
        self.slider_closing.on_changed(self.update_params)
        self.slider_dilation.on_changed(self.update_params)
        self.slider_min_size.on_changed(self.update_params)

        # Save button
        ax_save = plt.axes([0.85, 0.02, 0.1, 0.05])
        self.button_save = Button(ax_save, 'Save Params')
        self.button_save.on_clicked(self.save_parameters)

        plt.tight_layout()

    def update_params(self, val):
        """Update parameters from sliders"""
        self.params['block_size'] = int(self.slider_block_size.val)
        self.params['offset'] = int(self.slider_offset.val)
        self.params['connectivity_closing'] = int(self.slider_closing.val)
        self.params['connectivity_dilation'] = int(self.slider_dilation.val)
        self.params['min_object_size'] = int(self.slider_min_size.val)

        self.update_display()

    def update_display(self):
        """Update all display panels with current parameters"""

        # Run creek extraction with current parameters
        result = enhanced_adaptive_creek_extraction(
            self.images,
            mask=self.mask,
            **self.params
        )

        # Clear all axes
        for ax in [self.ax_original, self.ax_binary, self.ax_skeleton, self.ax_overlay]:
            ax.clear()

        # Original with mask overlay
        self.ax_original.imshow(self.images['original'])
        if self.mask is not None:
            # Show mask as semi-transparent overlay
            mask_overlay = np.zeros_like(self.images['original'])
            mask_overlay[self.mask > 0] = [255, 255, 0]  # Yellow
            self.ax_original.imshow(mask_overlay, alpha=0.3)
        self.ax_original.set_title('Original + Mask')
        self.ax_original.axis('off')

        # Binary result
        self.ax_binary.imshow(result['binary_final'], cmap='gray')
        self.ax_binary.set_title('Creek Areas')
        self.ax_binary.axis('off')

        # Skeleton
        self.ax_skeleton.imshow(result['skeleton'], cmap='gray')
        self.ax_skeleton.set_title('Creek Centerlines')
        self.ax_skeleton.axis('off')

        # Overlay skeleton on original
        overlay = self.images['original'].copy()
        skeleton_coords = np.where(result['skeleton'] > 0)
        if len(skeleton_coords[0]) > 0:
            overlay[skeleton_coords[0], skeleton_coords[1]] = [255, 0, 0]
        self.ax_overlay.imshow(overlay)
        self.ax_overlay.set_title('Centerlines Overlay')
        self.ax_overlay.axis('off')

        # Processing stages
        self.ax_stages.clear()
        stages = ['Raw Binary', 'Cleaned', 'Filled', 'Final']
        stage_images = [result['binary_raw'], result['binary_cleaned'],
                        result['binary_filled'], result['binary_final']]

        for i, (stage_name, stage_img) in enumerate(zip(stages, stage_images)):
            # Bottom row, 2 columns per stage
            ax_stage = plt.subplot(2, 8, 9 + i * 2)
            ax_stage.imshow(stage_img, cmap='gray')
            ax_stage.set_title(stage_name, fontsize=8)
            ax_stage.axis('off')

        self.fig.canvas.draw()

    def save_parameters(self, event):
        """Save current parameters to file"""
        filename = f"creek_params_{os.path.basename(self.image_path).split('.')[0]}.json"

        save_data = {
            'parameters': self.params,
            'mask_points': self.mask_points,
            'image_path': self.image_path
        }

        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"✅ Parameters saved to {filename}")
        print(f"Parameters: {self.params}")


def define_site_polygon(site_folder, site_name):
    """Define a polygon mask for a site using the first available image"""

    # Get first image from site
    image_files = glob.glob(os.path.join(site_folder, "*.png")) + \
        glob.glob(os.path.join(site_folder, "*.jpg"))

    if not image_files:
        print(f"No images found in {site_folder}")
        return None

    reference_image_path = sorted(image_files)[0]
    print(f"Using reference image: {os.path.basename(reference_image_path)}")

    # Load image
    images = load_image_for_processing(reference_image_path)

    # Create polygon selector
    print("\n=== Polygon Selection ===")
    print("Left click: Add point")
    print("Right click: Remove last point")
    print("Close window: Finish selection")

    selector = PolygonSelector(images['original'], site_name)
    plt.show()

    polygon_points = selector.get_polygon()

    if len(polygon_points) >= 3:
        print(f"✅ Polygon defined with {len(polygon_points)} points")

        # Save polygon for this site
        polygon_file = f"polygon_{site_name.lower()}.json"
        with open(polygon_file, 'w') as f:
            json.dump({
                'site_name': site_name,
                'polygon_points': polygon_points,
                'reference_image': reference_image_path
            }, f, indent=2)

        print(f"Polygon saved to {polygon_file}")
        return polygon_points
    else:
        print("❌ Need at least 3 points to define polygon")
        return None


def interactive_creek_tuning(site_folder, site_name, polygon_points=None):
    """Launch interactive tuning interface"""

    # Get first image for tuning
    image_files = glob.glob(os.path.join(site_folder, "*.png")) + \
        glob.glob(os.path.join(site_folder, "*.jpg"))

    if not image_files:
        print(f"No images found in {site_folder}")
        return

    reference_image = sorted(image_files)[0]
    print(f"Tuning parameters on: {os.path.basename(reference_image)}")

    # Launch tuning interface
    tuner = CreekTuningInterface(reference_image, polygon_points)
    plt.show()


def main():
    """Main workflow for creek extraction refinement"""

    print("=== Creek Extraction Refinement Tool ===")
    print()

    # Available sites
    kincardine_folder = "./data/annotated_kincardine"
    skinflats_folder = "./data/annotated_skinflats"

    sites_available = []
    if os.path.exists(kincardine_folder):
        sites_available.append(("Kincardine", kincardine_folder))
    if os.path.exists(skinflats_folder):
        sites_available.append(("Skinflats", skinflats_folder))

    if not sites_available:
        print("❌ No annotated image folders found!")
        return

    print("Available sites:")
    for i, (name, folder) in enumerate(sites_available):
        n_images = len(glob.glob(os.path.join(folder, "*.png")) +
                       glob.glob(os.path.join(folder, "*.jpg")))
        print(f"{i+1}. {name} ({n_images} images)")

    print()
    print("Workflow:")
    print("1. Define polygon mask (analysis area) for a site")
    print("2. Interactive parameter tuning")
    print("3. Load saved polygon and tune parameters")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        # Define polygon mask
        print("\nSelect site for polygon definition:")
        for i, (name, folder) in enumerate(sites_available):
            print(f"{i+1}. {name}")

        site_choice = int(input("Enter site number: ")) - 1
        if 0 <= site_choice < len(sites_available):
            site_name, site_folder = sites_available[site_choice]
            polygon_points = define_site_polygon(site_folder, site_name)

            if polygon_points:
                # Immediately go to tuning
                print(f"\nNow tuning parameters for {site_name}...")
                interactive_creek_tuning(
                    site_folder, site_name, polygon_points)

    elif choice == '2':
        # Parameter tuning without polygon
        print("\nSelect site for parameter tuning:")
        for i, (name, folder) in enumerate(sites_available):
            print(f"{i+1}. {name}")

        site_choice = int(input("Enter site number: ")) - 1
        if 0 <= site_choice < len(sites_available):
            site_name, site_folder = sites_available[site_choice]
            interactive_creek_tuning(site_folder, site_name)

    elif choice == '3':
        # Load saved polygon and tune
        print("\nSelect site:")
        for i, (name, folder) in enumerate(sites_available):
            print(f"{i+1}. {name}")

        site_choice = int(input("Enter site number: ")) - 1
        if 0 <= site_choice < len(sites_available):
            site_name, site_folder = sites_available[site_choice]

            # Try to load saved polygon
            polygon_file = f"polygon_{site_name.lower()}.json"
            if os.path.exists(polygon_file):
                with open(polygon_file, 'r') as f:
                    data = json.load(f)
                polygon_points = data['polygon_points']
                print(f"✅ Loaded polygon with {len(polygon_points)} points")
            else:
                print(f"❌ No saved polygon found ({polygon_file})")
                polygon_points = None

            interactive_creek_tuning(site_folder, site_name, polygon_points)


if __name__ == "__main__":
    main()
