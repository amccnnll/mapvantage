import os
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from PIL import Image
import glob
from datetime import datetime

def load_site_images(site_folder):
    """Load all annotated images for a site and extract dates"""
    
    image_files = glob.glob(os.path.join(site_folder, "*.png")) + glob.glob(os.path.join(site_folder, "*.jpg"))
    
    images_data = []
    
    for img_path in sorted(image_files):
        filename = os.path.basename(img_path)
        
        # Extract date from filename (annotated_2020-05-06 Sitename.png)
        try:
            date_part = filename.split('_')[1].split(' ')[0]  # Get YYYY-MM-DD part
            date_obj = datetime.strptime(date_part, "%Y-%m-%d")
            
            # Load image
            img = Image.open(img_path)
            img_array = np.array(img)
            
            images_data.append({
                'date': date_obj,
                'date_str': date_obj.strftime("%b %d, %Y"),
                'filename': filename,
                'image': img_array,
                'path': img_path
            })
        except Exception as e:
            print(f"Warning: Could not parse date from {filename}: {e}")
            continue
    
    # Sort by date
    images_data.sort(key=lambda x: x['date'])
    
    return images_data

def create_slider_comparison(site_folder, site_name, output_file=None):
    """Create interactive slider comparison for a site"""
    
    print(f"Creating slider comparison for {site_name}...")
    
    # Load images
    images_data = load_site_images(site_folder)
    
    if len(images_data) < 2:
        print(f"Need at least 2 images for comparison. Found {len(images_data)}")
        return None
    
    print(f"Loaded {len(images_data)} images")
    
    # Create figure
    fig = go.Figure()
    
    # Add each image as a frame
    for i, img_data in enumerate(images_data):
        fig.add_trace(
            go.Image(
                z=img_data['image'],
                name=img_data['date_str'],
                visible=(i == 0)  # Only first image visible initially
            )
        )
    
    # Create slider steps
    steps = []
    for i, img_data in enumerate(images_data):
        step = dict(
            method="update",
            args=[{"visible": [False] * len(images_data)},
                  {"title": f"{site_name} - {img_data['date_str']}"}],
            label=img_data['date_str']
        )
        step["args"][0]["visible"][i] = True  # Make this image visible
        steps.append(step)
    
    # Add slider
    sliders = [dict(
        active=0,
        currentvalue={"prefix": "Date: "},
        pad={"t": 50},
        steps=steps
    )]
    
    # Update layout
    fig.update_layout(
        title=f"{site_name} - Timeline Comparison",
        sliders=sliders,
        showlegend=False,
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    # Remove axes
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    
    # Save if output file specified
    if output_file:
        fig.write_html(output_file)
        print(f"Saved interactive comparison to {output_file}")
    
    return fig

def create_opacity_blend(site_folder, site_name, output_file=None):
    """Create two-image opacity blending comparison"""
    
    print(f"Creating opacity blend tool for {site_name}...")
    
    # Load images
    images_data = load_site_images(site_folder)
    
    if len(images_data) < 2:
        print(f"Need at least 2 images for blending. Found {len(images_data)}")
        return None
    
    # Use first and last images for dramatic comparison
    img1 = images_data[0]
    img2 = images_data[-1]
    
    print(f"Comparing {img1['date_str']} vs {img2['date_str']}")
    
    # Create figure with slider for opacity
    fig = go.Figure()
    
    # Add base image (always visible)
    fig.add_trace(
        go.Image(
            z=img1['image'],
            name=f"Base: {img1['date_str']}",
            opacity=1.0
        )
    )
    
    # Add overlay image (variable opacity)
    fig.add_trace(
        go.Image(
            z=img2['image'], 
            name=f"Overlay: {img2['date_str']}",
            opacity=0.5
        )
    )
    
    # Create opacity slider
    steps = []
    for opacity in np.arange(0, 1.1, 0.1):
        step = dict(
            method="update",
            args=[{"opacity": [1.0, opacity]}],
            label=f"{opacity:.1f}"
        )
        steps.append(step)
    
    sliders = [dict(
        active=5,  # Start at 0.5 opacity
        currentvalue={"prefix": "Overlay opacity: "},
        pad={"t": 50},
        steps=steps
    )]
    
    # Update layout
    fig.update_layout(
        title=f"{site_name} - Opacity Blend<br><sub>Base: {img1['date_str']} | Overlay: {img2['date_str']}</sub>",
        sliders=sliders,
        showlegend=False,
        height=600,
        margin=dict(l=0, r=0, t=80, b=0)
    )
    
    # Remove axes
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    
    # Save if output file specified
    if output_file:
        fig.write_html(output_file)
        print(f"Saved opacity blend to {output_file}")
    
    return fig

def create_side_by_side_grid(site_folder, site_name, cols=3, output_file=None):
    """Create a grid view of all images for overview"""
    
    print(f"Creating grid view for {site_name}...")
    
    # Load images
    images_data = load_site_images(site_folder)
    
    if len(images_data) == 0:
        print("No images found!")
        return None
    
    # Calculate grid dimensions
    n_images = len(images_data)
    rows = (n_images + cols - 1) // cols  # Ceiling division
    
    # Create subplots
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[img['date_str'] for img in images_data],
        vertical_spacing=0.05,
        horizontal_spacing=0.02
    )
    
    # Add images to subplots
    for i, img_data in enumerate(images_data):
        row = (i // cols) + 1
        col = (i % cols) + 1
        
        fig.add_trace(
            go.Image(z=img_data['image']),
            row=row, col=col
        )
    
    # Update layout
    fig.update_layout(
        title=f"{site_name} - All Images Overview",
        showlegend=False,
        height=300 * rows,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    # Remove axes for all subplots
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            fig.update_xaxes(visible=False, row=i, col=j)
            fig.update_yaxes(visible=False, row=i, col=j)
    
    # Save if output file specified
    if output_file:
        fig.write_html(output_file)
        print(f"Saved grid view to {output_file}")
    
    return fig

def create_animated_timelapse(site_folder, site_name, output_file=None, duration=800):
    """Create animated GIF-style timelapse"""
    
    print(f"Creating animated timelapse for {site_name}...")
    
    # Load images
    images_data = load_site_images(site_folder)
    
    if len(images_data) < 2:
        print(f"Need at least 2 images for animation. Found {len(images_data)}")
        return None
    
    # Create animated figure
    frames = []
    
    for img_data in images_data:
        frame = go.Frame(
            data=[go.Image(z=img_data['image'])],
            name=img_data['date_str'],
            layout=dict(title=f"{site_name} - {img_data['date_str']}")
        )
        frames.append(frame)
    
    # Create figure with first frame
    fig = go.Figure(
        data=[go.Image(z=images_data[0]['image'])],
        frames=frames
    )
    
    # Add play/pause buttons
    fig.update_layout(
        title=f"{site_name} - Animated Timelapse",
        updatemenus=[dict(
            type="buttons",
            buttons=[
                dict(label="Play", method="animate", 
                     args=[None, {"frame": {"duration": duration, "redraw": True}, 
                                 "fromcurrent": True}]),
                dict(label="Pause", method="animate", 
                     args=[[None], {"frame": {"duration": 0, "redraw": False}, 
                                   "mode": "immediate"}])
            ],
            direction="left",
            pad={"r": 10, "t": 87},
            showactive=False,
            x=0.1, xanchor="right", y=0, yanchor="top"
        )],
        showlegend=False,
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    # Remove axes
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    
    # Save if output file specified
    if output_file:
        fig.write_html(output_file)
        print(f"Saved animated timelapse to {output_file}")
    
    return fig

def generate_all_comparisons(base_data_folder="./data", output_folder="./outputs"):
    """Generate all comparison tools for both sites"""
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    sites = [
        {"name": "Kincardine", "folder": "annotated_kincardine"},
        {"name": "Skinflats", "folder": "annotated_skinflats"}
    ]
    
    print("=== Generating Interactive Comparison Tools ===")
    
    figures = {}
    
    for site in sites:
        site_name = site['name']
        site_folder = os.path.join(base_data_folder, site['folder'])
        
        print(f"\n--- Processing {site_name} ---")
        
        if not os.path.exists(site_folder):
            print(f"Warning: Folder not found: {site_folder}")
            continue
        
        # Generate all comparison types
        figures[f"{site_name.lower()}_slider"] = create_slider_comparison(
            site_folder, site_name, 
            os.path.join(output_folder, f"{site_name.lower()}_slider_comparison.html")
        )
        
        figures[f"{site_name.lower()}_blend"] = create_opacity_blend(
            site_folder, site_name,
            os.path.join(output_folder, f"{site_name.lower()}_opacity_blend.html") 
        )
        
        figures[f"{site_name.lower()}_grid"] = create_side_by_side_grid(
            site_folder, site_name,
            output_file=os.path.join(output_folder, f"{site_name.lower()}_grid_view.html")
        )
        
        figures[f"{site_name.lower()}_animation"] = create_animated_timelapse(
            site_folder, site_name,
            os.path.join(output_folder, f"{site_name.lower()}_timelapse.html")
        )
    
    print(f"\n✅ All comparisons generated! Check the '{output_folder}' folder.")
    print("HTML files can be opened in browser or embedded in Quarto documents.")
    
    return figures

if __name__ == "__main__":
    # Generate all comparisons
    figures = generate_all_comparisons()
    
    print("\nTo use in Quarto, you can embed these HTML files or call the functions directly:")
    print("```python")
    print("from comparison_tools import create_slider_comparison")
    print("fig = create_slider_comparison('./data/annotated_kincardine', 'Kincardine')")
    print("fig.show()")
    print("```")