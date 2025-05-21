import os
import subprocess
import vtk

# 子区标签定义
subfield_labels = {
    "para_sub": 203, "pre_sub": 204, "sub": 205, "CA1": 206,
    "CA3": 208, "CA4": 209, "GC_DG": 210, "HATA": 211,
    "fimbria": 212, "mole_layer": 214, "fissure": 215, "tail": 226
}

def nii_2_mesh(filename_nii, vtk_filename, label):
    """将 NIFTI 文件转换为 VTK 和 STL 曲面"""
    reader = vtk.vtkNIFTIImageReader()
    reader.SetFileName(filename_nii)
    reader.Update()

    surf = vtk.vtkDiscreteMarchingCubes()
    surf.SetInputConnection(reader.GetOutputPort())
    surf.SetValue(0, label)
    surf.Update()

    smoother = vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputConnection(surf.GetOutputPort())
    smoother.SetNumberOfIterations(30)
    smoother.NonManifoldSmoothingOn()
    smoother.NormalizeCoordinatesOn()
    smoother.GenerateErrorScalarsOn()
    smoother.Update()

    writer_vtk = vtk.vtkPolyDataWriter()
    writer_vtk.SetFileName(vtk_filename)
    writer_vtk.SetInputConnection(smoother.GetOutputPort())
    writer_vtk.Write()

    writer_stl = vtk.vtkSTLWriter()
    writer_stl.SetFileName(vtk_filename.replace(".vtk", ".stl"))
    writer_stl.SetInputConnection(smoother.GetOutputPort())
    writer_stl.Write()

def merge_labels_and_convert_to_vtk(label_dir, output_nii, output_vtk):
    """合并所有 label 的 nii.gz 文件并转换为 VTK"""
    try:
        files = [os.path.join(label_dir, f"{sub}.nii.gz") for sub in subfield_labels]
        cmd = ["fslmaths", files[0]]
        for f in files[1:]:
            cmd.extend(["-add", f])
        cmd.extend(["-bin", output_nii])
        subprocess.run(cmd, check=True)

        nii_2_mesh(output_nii, output_vtk, 1)
    except Exception as e:
        print(f"[Error] 合并标签失败: {e}")

def process_scan(scan_dir, label_dir, surf_dir, hemisphere, input_filename):
    """处理单侧：提取每个 label，生成 mesh，并合并生成 combined"""
    os.makedirs(label_dir, exist_ok=True)
    os.makedirs(surf_dir, exist_ok=True)

    if os.path.exists(input_filename):
        for subfield, label in subfield_labels.items():
            output_nii = os.path.join(label_dir, f"{subfield}.nii.gz")
            subprocess.run(["mri_extract_label", input_filename, str(label), output_nii], check=True)

            output_vtk = os.path.join(surf_dir, f"{subfield}.vtk")
            nii_2_mesh(output_nii, output_vtk, 128)

        combined_nii = os.path.join(label_dir, "combined_label.nii.gz")
        combined_vtk = os.path.join(surf_dir, "combined_label.vtk")
        merge_labels_and_convert_to_vtk(label_dir, combined_nii, combined_vtk)

def run_subject_processing(subject_dir, group_name, label_output_dir, surf_output_dir):
    """
    处理一个被试目录下的所有扫描子目录，生成标准结构的 Label 和 Surf 输出。
    """
    subject_id = os.path.basename(subject_dir.rstrip("/"))
    scan_dirs = [d for d in os.listdir(subject_dir) if os.path.isdir(os.path.join(subject_dir, d))]

    for scan in scan_dirs:
        scan_path = os.path.join(subject_dir, scan)
        mri_path = os.path.join(scan_path, "mri")

        lh_path = os.path.join(mri_path, "lh.hippoAmygLabels-T1.v21.FS60.mgz")
        rh_path = os.path.join(mri_path, "rh.hippoAmygLabels-T1.v21.FS60.mgz")

        # 输出路径
        lh_label = os.path.join(label_output_dir, "Left", group_name, subject_id, scan)
        rh_label = os.path.join(label_output_dir, "Right", group_name, subject_id, scan)
        lh_surf = os.path.join(surf_output_dir, "Left", group_name, subject_id, scan)
        rh_surf = os.path.join(surf_output_dir, "Right", group_name, subject_id, scan)

        # 左右脑处理
        if os.path.exists(lh_path):
            process_scan(scan_path, lh_label, lh_surf, "Left", lh_path)
        if os.path.exists(rh_path):
            process_scan(scan_path, rh_label, rh_surf, "Right", rh_path)
