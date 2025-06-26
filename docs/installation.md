# 📦 Installation Guide

HippoMetric is a Python-based toolkit for hippocampal shape modeling and morphometric analysis. It supports data processed by FreeSurfer and integrates with downstream structural pipelines.

## Operating System and Hardware Requirements

HippoMetric is designed to run on **Linux-based systems**.  
GPU acceleration is **highly recommended** for efficient processing, especially for hippocampal subfield segmentation and diffeomorphic modeling.

> ✅ The pipeline has been tested and successfully run on systems with the following configuration:

- **OS**: Ubuntu 18.04
- **GPU**: NVIDIA TITAN RTX 24GB
- **CUDA**: Version compatible with FreeSurfer GPU tools and Deformetrica (if applicable)

> ⚠️ Although CPU-based execution is possible, it will significantly increase processing time and is **not recommended** .

---

## Python Installation

HippoMetric is compatible with **Python 3.7+** and has been tested on Linux and macOS environments. Some modules may require additional setup for Windows compatibility.

---

## Dependencies

The following Python packages are required to run HippoMetric:

- **numpy** – core array and mathematical operations
- **pandas** – tabular data manipulation
- **scipy** – distance computations and file I/O
- **vtk** – shape modeling, surface processing, and visualization
- **xml.etree.ElementTree** – parsing and generating XML (standard library)
- **argparse** – command-line argument handling (standard library)
- **subprocess** – system command execution (standard library)
- **os**, **shutil**, **glob**, **pathlib**, **logging** – standard library utilities for file operations

**Notes:**

- `vtk` is essential for 3D surface processing and must be properly installed (see [PyPI: vtk](https://pypi.org/project/vtk/)).
- `scipy.io` is used for loading `.mat` files.
- All standard library modules (e.g., `os`, `pathlib`, `argparse`) come bundled with Python ≥3.7 and require no additional installation.

HippoMetric requires external softwares:

- [**FreeSurfer**](https://surfer.nmr.mgh.harvard.edu/) – hippocampal subfield segmentation
- [**Deformetrica**](https://www.deformetrica.org/) - diffeomorphic shape registration
- [**FSL**](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki) – used for voxel-wise image processing  
---

## Installation

### Option 1 – Install via pip

We will release a pip package soon. For now, please use the GitHub source version.

### Option 2 – Install from GitHub

Clone the repository and install the package manually:

```bash
git clone https://github.com/your-username/HippoMetric.git
cd HippoMetric
pip install -r requirements.txt
