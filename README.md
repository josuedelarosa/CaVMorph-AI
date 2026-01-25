# Fish Morphometrics - Desktop Application

A native desktop application for **automated fish morphometrics and phenotyping** using deep learning. Load images, get 20 anatomical keypoints automatically, compute biologically meaningful measurements, and export results—all offline.

## Features

✅ **Automatic Keypoint Detection** - ViTPose-based model predicts 20 anatomical landmarks  
✅ **Phenotype Computation** - Derived 14 measurements from keypoint pairs (distances, ratios)  
✅ **Batch Processing** - Analyze multiple images with progress tracking  
✅ **Live Preview** - Keypoint overlay visualization  
✅ **Export Options** - CSV (spreadsheet), JSON (raw data), PNG (annotated images)  
✅ **Zero Setup** - No Python, pip, CUDA, or ML frameworks to install  
✅ **Fully Offline** - No internet, no cloud, no tracking  
✅ **Cross-Platform** - Works on macOS, Windows, and Linux  

## System Requirements

| Component | Requirement |
|---|---|
| **OS** | macOS 10.14+, Windows 10+, Ubuntu 18.04+ |
| **RAM** | 4GB minimum (8GB recommended) |
| **Disk** | 2GB free for app + model weights |
| **CPU** | Modern processor (2010+); no GPU required |

## Installation

### macOS

1. Download `Fish Morphometrics.dmg`
2. Open the `.dmg` file
3. Drag **Fish Morphometrics** app to **Applications** folder
4. Eject the DMG
5. Open **Applications** → **Fish Morphometrics**

**First Launch**: macOS may ask for permission. Click "Open" in the security prompt.

### Windows

1. Download `FishMorphometrics_0.1.0_x64-setup.exe`
2. Run the installer
3. Follow the setup wizard
4. Launch from **Start Menu** → **Fish Morphometrics**

### Linux (Ubuntu/Debian)

```bash
# Download and install
wget https://releases.example.com/fish-morphometrics_0.1.0_amd64.deb
sudo dpkg -i fish-morphometrics_0.1.0_amd64.deb

# Launch
fish-morphometrics
```

Or use AppImage:
```bash
wget https://releases.example.com/FishMorphometrics_0.1.0_x86_64.AppImage
chmod +x FishMorphometrics_0.1.0_x86_64.AppImage
./FishMorphometrics_0.1.0_x86_64.AppImage
```

## Usage

### Basic Workflow

1. **Prepare Images**: Ensure fish are already cropped/segmented
   - Supported formats: JPEG, PNG, BMP, TIFF
   - Resolution: Any size (automatically resized internally)
   - Orientation: Lateral view (side profile)

2. **Load Images**:
   - Click **"Select Folder"** button
   - Navigate to folder containing fish images
   - App automatically finds all images (recursively)

3. **Analyze**:
   - Click **"Analyze"** button
   - Progress bar shows inference status
   - First image takes ~5 seconds (model loading)
   - Subsequent images ~0.5-1 second each

4. **Review Results**:
   - Preview shows keypoints overlaid on first image
   - Table displays all 14 phenotypes for each image
   - Scroll to see all measurements

5. **Export**:
   - **CSV**: For Excel, R, Python analysis
   - **JSON**: Raw prediction data (keypoints + scores)
   - **PNG**: Annotated images with keypoints drawn

### Keypoints Explained

20 anatomical landmarks are detected:

```
Example fish (lateral view):

     kp1    kp2   kp3
      •      •      •          (head region)
     /         \
   kp6         kp4
    •           •               (gill & body)
   
   kp5         
    •─────────•─────────•       (dorsal, lateral, ventral)
             kp7       kp8

kp9  •                    • kp11  (pelvic & adipose fins)
      \                  /
       • kp10      • kp12

kp13 •         •         • kp14  (tail region)
      \       /\       /
       • kp15 •  • kp16•
              /  \
            kp17 kp18

              • kp19
              • kp20
```

(Actual keypoint locations are learned from training data)

### Phenotypes (Computed Measurements)

The app computes **14 distances** between keypoint pairs:

| Pair | Description | Use Case |
|---|---|---|
| 0→1 | Head length | Head size |
| 3→2 | Body height (dorsal) | Body depth |
| 4→5 | Gill length | Gill development |
| ... | (9 more pairs) | Various morphological traits |

**Normalization**: If enabled, distances are divided by "standard length" (SL, default pair 0→3) to get **size-independent** measurements for statistical comparison.

### CSV Export Format

```csv
image_path,kp1_x,kp1_y,kp1_conf,kp2_x,kp2_y,kp2_conf,...,pair_0_1_px,pair_0_1_norm,pair_3_2_px,pair_3_2_norm,...
/path/fish1.jpg,123.4,456.7,0.95,128.1,460.2,0.93,...,150.5,0.82,45.3,0.25,...
/path/fish2.jpg,121.2,458.9,0.94,126.8,462.1,0.92,...,148.9,0.81,44.8,0.24,...
```

- `kpX_x`, `kpX_y`: Keypoint coordinates (pixels)
- `kpX_conf`: Confidence score (0-1)
- `pair_i_j_px`: Distance in pixels
- `pair_i_j_norm`: Normalized distance (if enabled)

### JSON Export Format

```json
[
  {
    "image_path": "/path/fish1.jpg",
    "keypoints": [[x1, y1], [x2, y2], ..., [x20, y20]],
    "keypoint_scores": [s1, s2, ..., s20],
    "extra_pred_fields": {
      "phenotypes": [
        {
          "id": 0,
          "pair": [0, 1],
          "name": "pair_0_1",
          "value_px": 150.5,
          "value_norm": 0.82
        },
        ...
      ]
    },
    "overlay_path": "/tmp/fish1_overlay.png"
  },
  ...
]
```

## Troubleshooting

### App Won't Start

- **Verify installation**: Check that app is in Applications (macOS) or Program Files (Windows)
- **Restart computer**: Clear any port conflicts
- **Check disk space**: Ensure 2GB+ free

### "Backend Startup Failed"

- Wait 30+ seconds (first launch can be slow)
- Check system RAM (should have 4GB+ free)
- Try launching app again

### "Model Not Found"

- Ensure app is properly installed (didn't move it after install)
- Reinstall the app (may be corrupted download)

### Images Not Loading

- Confirm image format: JPEG, PNG, BMP, TIFF only
- Check file permissions (read access required)
- Verify image file is not corrupted (try opening in Preview/Photos)

### Poor Keypoint Quality

- Ensure fish are **lateral view** (side profile)
- Verify fish are **fully visible** (not cropped)
- Check image **quality** (sufficient pixels, not blurry)
- Model was trained on specific fish species—performance may vary for other species

### Exporting to Folder Fails

- Check output folder **exists** and is **writable**
- Ensure sufficient **disk space**
- Try a different folder path
- Run as Administrator (Windows) if permission denied

## Performance Tips

### Faster Batch Processing

1. Optimize image folder structure
   - Use shallow folder hierarchy (not deeply nested)
   - Move infrequently-analyzed images to separate folder

2. Leave app running
   - Model stays loaded in memory
   - Each new image ~0.5 seconds
   - Closing app resets memory

3. Use SSD
   - Image loading faster from SSD vs. HDD
   - Reduces I/O bottleneck

### Limiting RAM Usage

- Don't analyze 10,000 images in one batch
- Process in chunks (500 images at a time)
- Close app between batches

## Data & Privacy

✅ **No data is sent anywhere**
- All processing happens locally on your computer
- No internet connection required
- Images and results never leave your machine

✅ **Your data is yours**
- Export results in standard formats (CSV, JSON, PNG)
- Use in any statistical software (R, Python, Excel, etc.)
- No vendor lock-in

## Advanced Usage

### Analyzing Different Fish Species

The model was trained on **[specific species]**. Performance may vary for other species. If you need:

- Custom training → Contact research team
- Different model → Use source code to train

### Using with Python

Export to JSON and process with pandas:

```python
import json
import pandas as pd

# Load predictions
with open('results.json') as f:
    preds = json.load(f)

# Extract phenotypes
phenotypes_list = []
for pred in preds:
    phenos = pred['extra_pred_fields']['phenotypes']
    for pheno in phenos:
        phenotypes_list.append({
            'image': pred['image_path'],
            'pair': f"{pheno['pair'][0]}_{pheno['pair'][1]}",
            'value_px': pheno['value_px'],
            'value_norm': pheno.get('value_norm')
        })

df = pd.DataFrame(phenotypes_list)
df.to_csv('phenotypes.csv', index=False)
```

### Using with R

```r
# Load CSV
df <- read.csv('results.csv')

# Analyze phenotypes
library(ggplot2)
ggplot(df, aes(x=pair_0_1_norm, y=pair_3_2_norm)) +
  geom_point() +
  labs(title='Fish Morphometrics',
       x='SL-normalized Head Length',
       y='SL-normalized Body Height')
```

## Model Information

- **Architecture**: Vision Transformer (ViT) base + custom heatmap head
- **Input**: 192×256 pixels, RGB
- **Output**: 20 keypoints (x, y, confidence)
- **Backbone**: Pre-trained on ImageNet, fine-tuned on fish dataset
- **Speed**: ~1 FPS on CPU (Intel i7/M1/Ryzen 5+)
- **Accuracy**: Trained with domain-specific losses including phenotype constraints

## System Information

View app version and system details:
- Menu → **About** (or **Help** → **About**)
- Shows app version, OS, Python version, device (CPU/GPU)

## Getting Help

- **Documentation**: See `ARCHITECTURE.md` for technical details
- **Issues**: Report bugs via GitHub Issues
- **Questions**: Contact research team
- **Source Code**: Available on GitHub (for developers)

## Citation

If you use this app in research, please cite:

```bibtex
@software{cavfish_morphometrics_2024,
  title={Fish Morphometrics: Automated Phenotyping with Deep Learning},
  author={Your Name and Collaborators},
  year={2024},
  url={https://github.com/yourrepo}
}
```

## License

This application is provided as-is for research and education purposes. See `LICENSE` file for details.

## Version History

### v0.1.0 (2024-01-24)
- Initial release
- 20-keypoint ViTPose model
- 14 phenotype measurements
- Batch inference
- CSV/JSON/PNG export
- Cross-platform support

---

**Last Updated**: 2024-01-24  
**Developed by**: Aquaculture Research Team  
**Repository**: https://github.com/yourrepo  
**Issues/Feedback**: https://github.com/yourrepo/issues
