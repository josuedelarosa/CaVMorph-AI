# Fish Morphometrics - Automated Analysis Tool

<div align="center">

**Automated fish morphometric analysis using deep learning**

Detect 20 anatomical keypoints • Measure 14 phenotypes • Export in seconds

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)]()
[![Status](https://img.shields.io/badge/status-active-success.svg)]()

</div>

---

## 🎯 Features

- **🔍 20 Keypoint Detection**: Snout, eye, fins, body landmarks with confidence scores
- **📐 14 Phenotype Measurements**: Standard length, body depth, fin positions, ratios
- **🎨 Confidence Visualization**: Color-coded keypoints (🔴 low → 🟠 medium → 🟢 high confidence)
- **📊 Batch Processing**: Analyze entire folders of images with progress tracking
- **💾 Multiple Export Formats**: CSV (spreadsheet), JSON (raw data), annotated images
- **🖥️ Cross-Platform**: Native macOS, Windows, and Linux support
- **⚡ Fast & Local**: No internet required, runs entirely on your machine
- **🔒 Privacy First**: Zero telemetry, no data leaves your computer

---

## 📦 Installation

### Quick Start (macOS)

1. **Download** the latest DMG from [Releases](#)
2. **Install** - Drag **Fish Morphometrics.app** to `/Applications`
3. **First Launch** - Choose your setup:
   - ✅ **Use Existing Environment** (if you have `cavfish310` conda env)
   - 🆕 **Create New Environment** (15-30 min auto-install)
4. **Start Analyzing** - App launches automatically after setup

### Build from Source

```bash
# Prerequisites: Node.js 18+, Rust 1.70+, Python 3.10
git clone https://github.com/yourusername/cavfish-inference.git
cd cavfish-inference/desktop
npm install
npm run tauri build
```

---

## 🚀 Quick Start Guide

### 1. Launch Application
Wait ~10 seconds for backend to initialize (watch the connection status)

### 2. Select Images
- Click **"📁 Select Folder"** and choose your fish photos
- Supported formats: JPG, PNG, TIFF, BMP
- Best results: Side-view images, 800-2000px width

### 3. Analyze
- Click **"🔍 Analyze Images"**
- Processing speed: ~2-5 images/second
- Progress bar shows real-time status

### 4. Review Results
- Click any result to view keypoints and measurements
- Keypoints are color-coded by confidence:
  - 🔴 **Red** (0-50%): Low confidence - verify manually
  - 🟠 **Orange** (50-75%): Medium confidence  
  - 🟢 **Green** (75-100%): High confidence - reliable

### 5. Export Data
Choose your format:
- **📥 CSV**: Spreadsheet-ready, opens in Excel/Numbers
- **📥 JSON**: Raw data for custom analysis
- **📥 Images**: Annotated photos with keypoints drawn

---

## 🎨 Keypoint Visualization

### Confidence-Based Colors
The app uses a gradient to show detection quality:

| Confidence | Color | Meaning |
|------------|-------|---------|
| 0-50% | 🔴 Red | Low confidence - manual verification recommended |
| 50-75% | 🟠 Orange | Medium confidence - generally reliable |
| 75-100% | 🟢 Green | High confidence - trusted detection |

### Normalized Keypoint Sizes
- Automatically scales based on image resolution
- Larger images = proportionally larger keypoints
- Consistent visibility across all image sizes

### 20 Anatomical Landmarks
1. Snout Tip
2. Lower Jaw
3. Eye Center
4. Operculum Rear
5. Pectoral Fin Base
6. Pelvic Fin Base
7. Dorsal Fin Front
8. Dorsal Fin Rear
9. Adipose Fin
10. Caudal Fin Top
11. Caudal Fin Center
12. Caudal Fin Bottom
13. Anal Fin Front
14. Anal Fin Rear
15. Body Midpoint 1
16. Body Midpoint 2
17. Body Midpoint 3
18. Lateral Line Front
19. Lateral Line Mid
20. Lateral Line Rear

*Edit `models/cavfish_v1/meta.json` to customize names*

---

## 📐 Phenotype Measurements

The app automatically calculates 14 biologically relevant measurements:

| Phenotype | Description | Keypoint Pair |
|-----------|-------------|---------------|
| **Standard Length** | Snout to caudal fin base | 1 → 11 |
| **Body Depth** | Maximum vertical height | 7 → 13 |
| **Head Length** | Snout to operculum | 1 → 4 |
| **Pre-Dorsal Length** | Snout to dorsal fin | 1 → 7 |
| **Caudal Peduncle Length** | Body to tail | Various |
| **Eye Diameter** | Eye size | 3 region |
| **Fin Base Lengths** | Pectoral, pelvic, dorsal, anal | Multiple pairs |

All measurements are provided in:
- **Pixels** (raw coordinates)
- **Normalized** (scaled by standard length)

*Edit `models/cavfish_v1/meta.json` to add custom phenotypes*

---

## 🔧 Customization

### Change Keypoint Names
Edit `models/cavfish_v1/meta.json`:
```json
{
  "keypoint_names": [
    "Your Custom Name 1",
    "Your Custom Name 2",
    ...
  ]
}
```

### Add Custom Phenotypes
Edit `models/cavfish_v1/meta.json`:
```json
{
  "phenotype_pairs": [
    [0, 10],  // Keypoint indices to measure
    [5, 15]
  ],
  "phenotype_names": [
    "Custom Measurement 1",
    "Custom Measurement 2"
  ]
}
```

### Change App Icon
1. Replace `desktop/src-tauri/icons/icon.png` with your 1024x1024 PNG
2. Rebuild: `cd desktop && npm run tauri build`

### Adjust Keypoint Display
Edit `desktop/src/App.vue` → `drawKeypointsOnCanvas()`:
```typescript
// Line ~950: Adjust size calculation
const baseSize = Math.max(3, Math.min(10, canvasAvg / 100))
// Increase divisor for smaller keypoints, decrease for larger
```

---

## 🛠️ Technical Architecture

### Stack
- **Frontend**: Vue 3 + TypeScript + Vite
- **Desktop Framework**: Tauri (Rust) - 60% smaller than Electron
- **Backend**: Python (FastAPI + Uvicorn)
- **ML Model**: PyTorch + MMPose + ViTPose
- **Environment**: Conda (isolated Python 3.10)

### How It Works
1. **App Launch** → Rust spawns Python backend on random port
2. **Image Analysis** → Backend runs ViTPose inference on CPU
3. **Keypoint Detection** → Model predicts (x, y, confidence) for each point
4. **Phenotype Calculation** → Custom head computes distances/ratios
5. **Overlay Generation** → OpenCV draws keypoints on image
6. **Frontend Display** → Vue renders results with confidence colors

### System Requirements
- **OS**: macOS 10.15+, Windows 10+, Ubuntu 20.04+
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 3GB for app + models
- **CPU**: Any modern processor (GPU optional)

### Data Privacy
- ✅ **100% Local**: No data transmission
- ✅ **No Telemetry**: Zero analytics or tracking
- ✅ **Open Source**: Audit the code yourself
- ✅ **Offline**: No internet connection required

---

## 📸 Screenshots

### Main Interface
*Analysis view with image list and real-time progress*

### Confidence Visualization
*Keypoints color-coded: red (low) → orange (mid) → green (high)*

### Export Options
*CSV, JSON, and annotated image export*

*(Add screenshots in `/docs/screenshots/` directory)*

---

## 🐛 Troubleshooting

### Images don't load in preview
**Symptom**: Gray background with keypoints only, no fish photo

**Solutions**:
1. Click 🔍 **Debug Console** icon (top-right) to view logs
2. Look for: `❌ Failed to load overlay image from base64`
3. If found, check `desktop/src-tauri/tauri.conf.json`:
   ```json
   "security": {
     "csp": "img-src 'self' data: blob:;"
   }
   ```
4. Rebuild if CSP was wrong

### Backend won't start
**Symptom**: "Connecting to backend... (attempt 12/12)" error

**Solutions**:
1. Check conda environment:
   ```bash
   conda env list | grep cavfish310
   ```
2. Verify Python:
   ```bash
   conda activate cavfish310
   python --version  # Should be 3.10
   ```
3. Check backend logs:
   ```bash
   /Applications/Fish\ Morphometrics.app/Contents/MacOS/Fish\ Morphometrics
   ```

### Keypoints are misaligned
**Symptom**: Keypoints don't match fish anatomy

**Possible Causes**:
- Image quality too low (< 800px width)
- Fish not in side view
- Unusual fish species not in training data
- Occlusion (fish partially hidden)

**Solutions**:
1. Use higher resolution images
2. Ensure clear side-view photos
3. Check confidence colors - red points are unreliable
4. Manually verify low-confidence detections

### First-run setup fails
**Symptom**: Environment creation hangs or errors

**Solutions**:
1. Ensure conda is installed:
   ```bash
   conda --version
   ```
2. Check internet connection (needed for package downloads)
3. Try manual setup:
   ```bash
   conda create -n cavfish310 python=3.10 -y
   conda activate cavfish310
   cd backend
   pip install -r requirements.txt
   ```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Credits & Acknowledgments

### Built With
- **[MMPose](https://github.com/open-mmlab/mmpose)** - OpenMMLab pose estimation framework
- **[ViTPose](https://github.com/ViTAE-Transformer/ViTPose)** - Vision Transformer for pose estimation
- **[Tauri](https://tauri.app/)** - Lightweight desktop framework
- **[Vue 3](https://vuejs.org/)** - Progressive JavaScript framework
- **[PyTorch](https://pytorch.org/)** - Deep learning library

### Developers
- **Project Lead**: [Your Name]
- **ML Model**: [Model Developer]
- **UI/UX**: [Designer Name]

### Research Citation
If you use this tool in research, please cite:
```bibtex
@software{fish_morphometrics_2026,
  title = {Fish Morphometrics: Automated Analysis Tool},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/yourusername/cavfish-inference}
}
```

---

## 📧 Support & Contact

- **🐛 Bug Reports**: [GitHub Issues](https://github.com/yourusername/cavfish-inference/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/yourusername/cavfish-inference/discussions)
- **📖 Documentation**: [Full Docs](https://docs.yourproject.com)
- **✉️ Email**: support@yourproject.com

---

## 🗺️ Roadmap

### Current Version (v0.1.0)
- [x] 20 keypoint detection
- [x] 14 phenotype measurements
- [x] Confidence visualization
- [x] Batch processing
- [x] CSV/JSON/Image export

### Upcoming Features
- [ ] **GPU Acceleration**: 10x faster processing
- [ ] **Custom Model Training**: Train on your own fish species
- [ ] **3D Analysis**: Depth estimation from multiple views
- [ ] **Time Series**: Track growth over time
- [ ] **Cloud Sync**: Optional backup to your cloud storage
- [ ] **Mobile App**: iOS/Android companion

---

<div align="center">

**Made with ❤️ for marine biology and ichthyology research**

[Report Bug](https://github.com/yourusername/cavfish-inference/issues) • [Request Feature](https://github.com/yourusername/cavfish-inference/issues) • [Documentation](https://docs.yourproject.com)

</div>

Before installing, you need **Miniforge3** (conda) installed:

```bash
# Install Miniforge via Homebrew (recommended)
brew install --cask miniforge

# Or download directly from GitHub
# https://github.com/conda-forge/miniforge/releases
```

#### Installing the App

1. Download `Fish Morphometrics.dmg`
2. Open the `.dmg` file
3. Drag **Fish Morphometrics** app to **Applications** folder
4. Eject the DMG
5. Open **Applications** → **Fish Morphometrics**

#### First Launch Setup

On first launch, the app will automatically:
1. ✓ Detect your conda installation
2. ✓ Create a Python 3.10 environment (`cavfish310`)
3. ✓ Install PyTorch with MPS support (for Apple Silicon)
4. ✓ Install mmpose, mmengine, mmcv
5. ✓ Install FastAPI and other dependencies
6. ✓ Download model weights (~1GB)

This process takes **10-20 minutes** depending on your internet connection.

**First Launch Note**: macOS may ask for permission. Click "Open" in the security prompt.

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

### First-Run Setup Issues

**"Conda not found" Error**
- Ensure Miniforge is installed: `brew install --cask miniforge`
- Restart your computer after installing
- Check installation: `which conda` should show a path

**Setup stuck at "Installing mmpose"**
- This step can take 5-10 minutes
- Check internet connection
- mmpose is installed via pip from source, which takes time

**Setup fails with package errors**
- Retry setup using the "Retry" button
- Ensure stable internet connection
- Check disk space (needs ~3GB free)

**Model download failed**
- Check internet connection
- Retry setup
- If using corporate network, VPN may block downloads

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
