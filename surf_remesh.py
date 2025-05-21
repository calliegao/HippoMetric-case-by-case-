# file: remesh_utils.py

import os
from pathlib import Path
import vtk

# 每个亚区的目标四边形数
TARGET_QUAD_COUNTS = {
    "combined_label": 2500,
    "CA1": 1400,
    "CA3": 600,
    "CA4": 600,
    "GC-DG": 1200,
    "HATA": 140,
    "mole_layer": 2000,
    "para_sub": 150,
    "pre_sub": 800,
    "sub": 1000,
    "tail": 800,
}

def remesh_stl(input_path: Path, output_path: Path, target_quad_count: int):
    """对单个 STL 网格进行 remesh 并保存"""
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(input_path))
    reader.Update()
    mesh = reader.GetOutput()

    connectivity = vtk.vtkConnectivityFilter()
    connectivity.SetInputData(mesh)
    connectivity.SetExtractionModeToLargestRegion()
    connectivity.Update()
    largest_region = connectivity.GetOutput()

    reduction = 1 - target_quad_count / max(1, largest_region.GetNumberOfPoints())
    decimate = vtk.vtkQuadricDecimation()
    decimate.SetInputData(largest_region)
    decimate.SetTargetReduction(reduction)
    decimate.Update()

    writer = vtk.vtkSTLWriter()
    writer.SetFileName(str(output_path))
    writer.SetInputData(decimate.GetOutput())
    writer.Write()

def remesh_subject_stl(hemi_input_dir: Path, hemi_output_dir: Path):
    os.makedirs(hemi_output_dir, exist_ok=True)

    for file in hemi_input_dir.glob("*.stl"):
        base_name = file.stem
        output_file = hemi_output_dir / f"Remesh_{base_name}.stl"
        target_quad_count = TARGET_QUAD_COUNTS.get(base_name, 2500)

        try:
            remesh_stl(file, output_file, target_quad_count)
            print(f"[Remesh] 完成: {output_file}")
        except Exception as e:
            print(f"[Remesh] 失败: {file}，错误：{e}")

