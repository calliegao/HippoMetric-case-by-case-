# 📊 Examples

## Overview
Brief introduction about what examples are included and how to use them.

## Example 1: Single Subject Processing
HippoMetric supports case-by-case analysis, allowing you to process one subject across multiple timepoints in a controlled, stepwise fashion.
### Example Folder Structure

Your input directory should follow this nested structure:

```bash
group1/
└── 002_S_0413/
├── scan01/ # FreeSurfer output for baseline
├── scan02/ # FreeSurfer output for follow-up
└── ...
```

Each `scanXX` folder must be a valid FreeSurfer subject directory (i.e., contains `mri/`, `surf/`, `label/`, etc.).

### Run the Pipeline

Activate your deformetrica environment first:

```bash
conda activate deformetrica
```

Then run the pipeline script:

```bash
python run_HippoMetric.py
```
You can customize the pipeline steps by modifying the script's main block:

```bash
if __name__ == "__main__":
    work_dir = Path("/home/nagao/test_case")
    base_dir = "/home/nagao/test_case/adni/group1"
    subject_id = "002_S_0413"
    group_name = "group1"

    run_pipeline(
        base_dir,
        subject_id,
        group_name,
        run_step1=True,   # Segment subfields
        run_step2=True,   # Convert label to surface
        run_step3=True,   # Refine surface
        run_step4=True,   # Register surfaces
        run_step5=True,   # Split into baseline and follow-up
        run_step6=True,   # Create deformetrica configs
        run_step7=True,   # Run diffeomorphic modeling
        run_step8=True,   # Extract skeletal representation
        run_step9=True,   # Refine spokes
        run_step10=True   # Merge baseline into follow-up
    )
```

💡 Tip: You can enable or disable specific steps to debug or resume processing from any stage.

## Example 2: Batch Processing Multiple Subjects

While `run_HippoMetric.py` is designed to process a single subject with all its scans (i.e., a **case-by-case** pipeline), you can easily process multiple subjects by writing a simple batch script that iterates through your dataset.

### Recommended Folder Structure

Each group folder should contain subject folders, and each subject folder should include one or more scan subfolders (e.g., scan01, scan02, etc.).

```bash
group1/
├── 002_S_0413/
│ ├── scan01/ # FreeSurfer results for the first timepoint
│ ├── scan02/ # FreeSurfer results for follow-up
│ └── ...
├── 013_S_4573/
│ ├── scan01/
│ └── ...
```

### Batch Script Example

You can use the following Python script to run HippoMetric for all subjects in a group:

```bash
import os
from pathlib import Path
from run_HippoMetric import run_pipeline

# Define working directories
work_dir = Path("/home/nagao/test_case")
base_dir = work_dir / "adni" / "group1"
group_name = "group1"

# Loop through each subject in the group
for subject_folder in base_dir.iterdir():
    if subject_folder.is_dir():
        subject_id = subject_folder.name
        print(f"\n[INFO] Processing subject: {subject_id}")

        run_pipeline(
            base_dir=str(base_dir),
            subject_id=subject_id,
            group_name=group_name,
            run_step1=False,  # Skip segmentation if already done
            run_step2=True,
            run_step3=True,
            run_step4=True,
            run_step5=True,
            run_step6=True,
            run_step7=True,
            run_step8=True,
            run_step9=True,
            run_step10=True
        )
```

This script assumes:

You have already organized your dataset by subject and scan (as shown above).

Each scan folder contains valid FreeSurfer output.

You want to run steps 2–10 for each subject.

You can adjust the run_stepX=True/False flags to customize the workflow based on your needs (e.g., re-running specific modules or skipping completed ones).

## Example 3: Visualizing Results

### 🔍 Check Results of Rigid Registration

After Step 4 (rigid surface registration), you can visualize the alignment quality using:

```bash
python CheckRegistration.py
```

Make sure to update the input/output folder paths and specify the hippocampal subregion to check.
The script will generate per-scan visualization results for each subject under the output folder.

The green surface represents the template, while the red surfaces represent the subject’s hippocampal combined_label surfaces across multiple timepoints.

Example: Below is the rigid registration result for one subject scanned three times.

<img src="_static/images/registration.png" alt="Results of surface ragid registration of a subject." width="400"/>

### 🔍 Check Spokes of the Skeletal Representation of Hippocampal Subfields
After Step 9 (Refine Spokes), you can visualize the medial-axis spokes for a specific subject and subfield using:

```bash
python CheckSpokes.py
```

Update the script with the correct input path and the subfield you wish to inspect.
A pop-up window will display the boundary surface and spoke vectors for the selected subfield.

📏 The thickness of each subfield is calculated as the length of the spoke vector.

Example: Below are refined spoke visualizations for multiple hippocampal subfields.

<img src="_static/images/spokes.png" alt="Results of refined spokes of a subject." width="800"/>


