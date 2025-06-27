# 🚀 Getting Started

## Theoretical Foundations of HippoMetric

### Introduction to the Longitudinal Lamellar Organization of the Hippocampus

The human hippocampus is essential for memory, learning, and spatial navigation, and is particularly vulnerable to disorders involving structural degeneration. Hippocampal atrophy is a well-established biomarker of disease progression, prompting extensive efforts to localize early morphometric changes through surface-based analyses.

However, accurate modeling of hippocampal morphology remains challenging due to its complex curvature—especially in the head region with variable digitations and medial bending. Existing methods, including surface parameterization (e.g., SPHARM-PDM) and deformable registration (e.g., LDDMM), often struggle with inconsistent folding patterns and subfield segmentation errors in clinical MRI. Skeleton-based approaches improve volumetric representation but may misalign with the natural axis of curvature, leading to inaccurate regional metrics.

Despite morphological variability, the hippocampus exhibits a consistent **lamellar organization**: thin transverse slices aligned along a stable longitudinal axis (Andersen et al., 2000; Sloviter & Lomo, 2012; Pak et al., 2022). This axis follows a characteristic curved trajectory, preserved across subfields, including in the uncus (Ding & Van Hoesen, 2015; Adler et al., 2018). The lamellar structure reflects both anatomical continuity and functional organization, supported by electrophysiological evidence of interlamellar connectivity and predominant information flow along the long axis.

Modeling the hippocampus according to this biologically grounded lamellar framework offers a more consistent and anatomically faithful basis for morphological analysis than traditional boundary- or skeleton-based methods.

<img src="_static/images/Figure1.png" alt="Figure 1. Lamellar organization of the hippocampus" width="400"/>

---

### Introduction to the Medial-axis Geometry

The medial axis geometry provides an intuitive and mathematically rigorous framework to represent an object’s intrinsic shape. Unlike surface-based methods that focus only on boundary characteristics, medial representations use the object’s internal structure to define shape via its **skeleton**, preserving both global topology and local geometry.

Originally proposed by Blum and mathematically formalized by Damon et al. (2003, 2008), the **medial representation (m-rep)** defines shape through the trajectory of **maximal inscribed balls (MIBs)** within the object. The center points of these MIBs form a smooth **medial manifold**, and their radii describe local thickness. Since each boundary point is tangent to one or more MIBs, the boundary can be fully reconstructed from the medial data.

Further developments by Pizer et al. (2006) introduced **skeletal representations (s-reps)**, which generalize the medial concept into a statistical shape framework. S-reps have been widely used in medical image analysis for shape modeling, deformation analysis, and population-level statistics.

In 3D medial geometry, each point on the medial surface defines **spoke vectors** extending to the boundary, forming a radial field that satisfies strict geometric constraints:
- Each spoke is perpendicular to the medial surface.
- The boundary normals at the spoke tips align with spoke directions.
- Fold curves on the medial surface define third vectors pointing to surface ridges.

This **radial map** ensures a one-to-one correspondence between the medial surface and the object boundary, enabling precise reconstruction and consistent shape comparisons. These properties make medial-axis geometry particularly suitable for analyzing anatomical structures with complex curvature, such as the hippocampus.

<img src="_static/images/Figure2.png" alt="Figure 2. Medial axis" width="600"/>

---

## Step-by-Step Example

### 1. Prepare Your Data

HippoMetric requires structural T1-weighted MRI scans that have been processed with FreeSurfer.

We recommend organizing your data by group, subject, and scan session, like this:

```bash
raw_data_dir/
└── group1/
└── sub-001/
├── scan01/
├── scan02/
└── ...
```

Each `scanXX` folder stores the result of one MRI session. The folder name reflects the temporal order of scans (e.g., `scan01` = first visit, `scan02` = second visit).

To process each scan using FreeSurfer:

```bash
recon-all -i /path/to/input_T1.nii.gz \
          -sd /path/to/raw_data_dir/group1/sub-001 \
          -s scan01 \
          -all
```
Repeat this for all scans (scan02, scan03, etc.), updating the -s parameter each time. You can also write a simple batch script to automatically process all scans using this folder naming convention.

After processing, your subject folder should look like:

```bash
sub-001/
├── scan01/  # FreeSurfer output for first timepoint
├── scan02/  # FreeSurfer output for second timepoint
└── ...
```
Each scan folder (e.g., scan01/) must be a valid FreeSurfer subject directory containing mri/, surf/, label/, and other subfolders required for downstream processing.

Alternatively, you can first run recon-all following your original raw data structure, and then reorganize the output into the above format before using HippoMetric.

---

### 2. Run HippoMetric main pipeline

After FreeSurfer processing, run HippoMetric’s segmentation module to extract hippocampal subfields and generate initial surface meshes.

Before running the main module, make sure you have activated the appropriate environment:

```bash
conda activate deformetrica
```
Then run the pipeline from the HippoMetric root directory:

```bash
python step1_segmentHA.py --subjects sub-001 sub-002 --fs_subjects_dir /path/to/freesurfer/subjects
```

The run_HippoMetric.py script includes 10 modular steps, which can be selectively executed by adjusting the flags in the script (e.g., run_step1=True). This allows flexible control and easy debugging of each processing stage.

Below is a description of each step:

#### Step 1. Hippocampal Subfield Segmentation
This step calls FreeSurfer’s segmentHA_T1.sh <subject_id> to perform subfield segmentation.
FreeSurfer supports GPU acceleration for this step.  
If you prefer to run this segmentation separately (e.g., in batch mode), we highly recommend you set `run_step1=False` in the script, and use GPU to accelerate hippocampal subfield segmentation via the `segmentHA_T1.sh` script.

```bash
segmentHA_T1.sh <subject_id> --gpu
```

#### Step 2. Convert Labels to Surfaces
This step converts the segmented hippocampal labels to surface meshes and merges 10 subfields (CA1, CA3, CA4, Sub, Sub_pre, Sub_para, GC_DG, Mole_layer, HATA, Tail) into one combined hippocampal label.
Output is saved to the output/Surf/ folder.

#### Step 3. Surface Refinement
This step smooths the boundary and simplifies the mesh from Step 2.
Output is saved to output/RefinedSurf/.

#### Step 4. Surface Rigid Registration
This step performs rigid registration of baseline (e.g., scan01) surfaces to a template. Follow-up scans (scan02, etc.) are registered to the baseline surface.
Results are saved in output/RegedRefinedSurf/.

#### Step 5. Split Baseline and Follow-ups
This step separates each subject’s scans into Baseline and FollowUps folders for further modeling.

#### Step 6. Generate and Update Deformation Configurations
This step generates and modifies configuration files: model_L.xml, model_R.xml, and data_set.xml for each baseline scan.

#### Step 7. Template-to-Subject Diffeomorphic Deformation
This step performs diffeomorphic shape registration from the template to each subject’s baseline hippocampus, generating an initial skeletal representation.
Results are saved in:
```bash
/output/Baseline/<Side>/<Group>/<Subject ID>/<Scan>/output/
```

#### Step 8. Extract Spokes (Skeletal Vectors)
This step extracts the skeletal representation from Step 7 into two separate point sets: base points and terminal points of spokes.
Outputs are saved as:
```bash
/output/Baseline/<Side>/<Group>/<Subject ID>/<Scan>/*.pt.vtk  
/output/Baseline/<Side>/<Group>/<Subject ID>/<Scan>/*.ps.vtk
```
#### Step 9. Refine Spokes
This step refines spokes based on medial-axis geometric constraints and applies the same process to follow-up scans.

#### Step 10. Merge Baseline and Follow-ups
Finally, this step merges the baseline data back into the FollowUps folder, so all timepoints are stored together for downstream analysis.

### 3. Compute Hippocampal Morphometric Measures

In the previous step, each subject’s hippocampus has been represented using a skeletal model. These models are stored in the `FollowUps` folder.  
This step computes morphometric features based on those skeletal representations.

To extract surface-based morphometry:

```bash
python FinalStep_Measure.py
```
This script exports the processed data into structured .csv files.

Since the full hippocampal model is constructed by merging 10 anatomical subfields, both combined and subfield-wise measures can be calculated.
To compute the volume of the entire hippocampus and each subfield individually, run:
```bash
python FinalStep_MeasureVolume.py
```
These measurements include:

Combined hippocampal volume (summed across subfields)

Subfield volumes (CA1, CA3, CA4, Sub, Sub_pre, Sub_para, GC_DG, Mole_layer, HATA, Tail)

Additional shape metrics from skeletal spokes (e.g., thickness, curvature)

The output CSV files will be saved in a structured format for each group and timepoint.

### 4. Quality Control and Regroup Local Measurements

Due to potential errors introduced during deformation and spoke refinement, morphometric measurements require quality control.  
This step removes unreliable data points and reorganizes local measurements for better interpretability.

To perform quality control and regrouping, open **RStudio** and run the following script:

```r
source("CleanMeasurements.r")
```
This script performs two key functions:

Quality Control:
Filters out invalid measurements based on geometric constraints and spoke integrity.

Regrouping of Local Features:
Aggregates fine-grained vertex-wise measurements (e.g., thickness, width) into biologically meaningful composite indices.
The following regrouped indices are generated:

- AllHippoLamellaIndex
- AllHippoSupInfIndex
- AllHippoLatVenIndex
- AllHippoAtlasIndex
- AllHippoHBTIndex
- AllHippoLamellaAtlasIndex
- AllHippoHBTAtlasIndex
- AllHippoLamellaSupInfLatVenIndex
- AllHippoHBTSupInfLatVenIndex

Each index corresponds to a specific anatomical partition (e.g., lamellae, dorsoventral layers, or medial-lateral axes), providing higher-level morphological summaries.

For each subfield, lamellar-wise thickness is also computed, where the lamella ID matches the full hippocampal lamella segmentation.

Whether you should use regrouped features or the direct QC’d measurements from FinalStep.Measure.py depends on your research goals:

Use regrouped features if you are interested in region-level or anatomically constrained variations.

Use QC’d pointwise features if you aim to detect fine-scale local changes or perform vertex-based analysis.

## Summary

HippoMetric is a surface-based morphometry pipeline designed for biologically-informed modeling and precise quantification of hippocampal morphology across multiple timepoints.

The pipeline includes:

- Subfield segmentation using FreeSurfer
- Surface conversion and mesh optimization
- Template-based diffeomorphic shape modeling
- Medial-axis skeletal representation extraction
- Computation of local and global shape features (e.g., thickness, curvature, volume)
- Quality control of geometric measurements
- Regrouping of vertex-wise features into biologically meaningful composite indices

With its modular design, HippoMetric enables flexible processing for both longitudinal and cross-sectional studies, and supports high-throughput batch analysis.

Final outputs are structured in CSV format, ready for statistical analysis in tools such as R, Python, or MATLAB.  
Researchers can choose between **fine-grained vertex-wise features** or **regrouped region-level indices** depending on their analytical needs.

HippoMetric is especially suited for detecting subtle morphological changes in hippocampus-related neurological and psychiatric disorders.
