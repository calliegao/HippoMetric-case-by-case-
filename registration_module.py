import os
import vtk
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk

def read_stl(filepath):
    """读取 STL 文件的点和三角形数据。"""
    reader = vtk.vtkSTLReader()
    reader.SetFileName(filepath)
    reader.Update()
    polydata = reader.GetOutput()

    # 检查文件是否有效
    if polydata.GetNumberOfPoints() == 0:
        print(f"Warning: No points found in {filepath}. Skipping.")
        return None, None

    # 提取点数据
    points = vtk_to_numpy(polydata.GetPoints().GetData())
    
    # 提取单元数据
    cells = vtk_to_numpy(polydata.GetPolys().GetData())  # 获取单元数据
    if cells.size == 0:
        print(f"Warning: No cells found in {filepath}. Skipping.")
    
    return points, cells


def read_vtk(filepath):
    """读取 VTK 文件的点数据和单元数据。"""
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filepath)
    reader.Update()
    polydata = reader.GetOutput()

    # 检查文件是否有效
    if polydata.GetNumberOfPoints() == 0:
        print(f"Warning: No points found in {filepath}. Skipping.")
        return None, None

    # 提取点数据
    points = vtk_to_numpy(polydata.GetPoints().GetData())
    
    # 提取单元数据
    cells = vtk_to_numpy(polydata.GetPolys().GetData())  # 获取单元数据
    if cells.size == 0:
        print(f"Warning: No cells found in {filepath}. Skipping.")
    
    return points, cells


def points_to_polydata(points, cells=None):
    """将点数据转换为 vtkPolyData 格式，考虑到可能有单元数据。"""
    polydata = vtk.vtkPolyData()
    vtk_points = vtk.vtkPoints()
    vtk_points.SetData(numpy_to_vtk(points))
    polydata.SetPoints(vtk_points)
    
    if cells is not None and cells.size > 0:
        # 需要将单元数据添加到 polydata 中
        vtk_cells = vtk.vtkCellArray()
        
        # cells 为 flat list，按三个点为一组组成三角形单元
        for i in range(0, len(cells), 4):  # 每四个数字构成一个三角形
            # vtkCells.InsertNextCell() 需要插入每个三角形的三个点的索引
            vtk_cells.InsertNextCell(3)  # 3表示单元格包含3个点
            vtk_cells.InsertCellPoint(cells[i+1])  # 第一个点索引
            vtk_cells.InsertCellPoint(cells[i+2])  # 第二个点索引
            vtk_cells.InsertCellPoint(cells[i+3])  # 第三个点索引
        
        polydata.SetPolys(vtk_cells)

    return polydata


def rigid_registration(source_points, target_points, source_cells=None, target_cells=None):
    """刚性配准（基于 ICP）。"""
    # 将 numpy 点数据和单元数据转换为 vtkPolyData
    source_polydata = points_to_polydata(source_points, source_cells)
    target_polydata = points_to_polydata(target_points, target_cells)

    # 设置 ICP 转换
    icp = vtk.vtkIterativeClosestPointTransform()
    icp.SetSource(source_polydata)  # 源点集
    icp.SetTarget(target_polydata)  # 目标点集
    icp.GetLandmarkTransform().SetModeToRigidBody()
    icp.SetMaximumNumberOfIterations(50)
    icp.StartByMatchingCentroidsOn()
    icp.Update()

    # 获取变换矩阵
    matrix = icp.GetMatrix()

    # 应用变换矩阵到源点集
    transformed_points = []
    for point in source_points:
        x, y, z, _ = matrix.MultiplyPoint([*point, 1.0])
        transformed_points.append([x, y, z])

    return np.array(transformed_points)


def save_polydata_to_vtk(polydata, output_filepath):
    """将 polydata 保存为 VTK 文件。"""
    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(output_filepath)
    writer.SetInputData(polydata)
    writer.Write()
    print(f"Saved transformed polydata to {output_filepath}")

def apply_transform(points, matrix):
    """应用变换矩阵到点集。"""
    transformed_points = []
    for point in points:
        x, y, z, _ = matrix.MultiplyPoint([*point, 1.0])
        transformed_points.append([x, y, z])
    return np.array(transformed_points)

# ---- 核心处理函数 ----
def process_subject(subject_folder, template_file, output_folder, side, study):
    """处理每个被试的数据，先对最小扫描号配准模板，再对其余扫描配准最小扫描"""
    print(f"Processing subject folder: {subject_folder}")

    # 找到扫描文件夹中编号最小的 ScanXX
    scan_folders = [f for f in os.listdir(subject_folder) if f.startswith('Scan') and os.path.isdir(os.path.join(subject_folder, f))]
    if not scan_folders:
        print(f"Warning: No Scan folders found in {subject_folder}. Skipping.")
        return
    scan_folders.sort()  # 按名称排序，确保 ScanXX 中 XX 最小的在最前
    primary_scan_folder = scan_folders[0]
    primary_scan_path = os.path.join(subject_folder, primary_scan_folder)

    # 输出文件夹，保持目录层级结构
    output_subject_folder = os.path.join(output_folder, side, study, os.path.basename(subject_folder))
    primary_output_folder = os.path.join(output_subject_folder, primary_scan_folder)
    os.makedirs(primary_output_folder, exist_ok=True)

    # 第一步：对最小的 ScanXX 文件夹执行模板配准
    remesh_combined_label_file = os.path.join(primary_scan_path, 'Remesh_combined_label.stl')
    if not os.path.exists(remesh_combined_label_file):
        print(f"Warning: {remesh_combined_label_file} not found. Skipping primary scan.")
        return

    # 读取 Remesh_combined_label.stl
    remesh_points, remesh_cells = read_stl(remesh_combined_label_file)
    if remesh_points is None:
        print(f"Failed to read STL file: {remesh_combined_label_file}")
        return

    # 读取模板文件
    template_points, template_cells = read_vtk(template_file)
    if template_points is None:
        print(f"Failed to read template file: {template_file}")
        return

    # 配准模板并获取形变矩阵
    source_polydata = points_to_polydata(remesh_points, remesh_cells)
    target_polydata = points_to_polydata(template_points, template_cells)

    icp = vtk.vtkIterativeClosestPointTransform()
    icp.SetSource(source_polydata)
    icp.SetTarget(target_polydata)
    icp.GetLandmarkTransform().SetModeToRigidBody()
    icp.SetMaximumNumberOfIterations(50)
    icp.StartByMatchingCentroidsOn()
    icp.Update()
    transform_matrix = icp.GetMatrix()

    # 保存 primary_scan_folder 中的配准结果
    transformed_points = apply_transform(remesh_points, transform_matrix)
    transformed_polydata = points_to_polydata(transformed_points, remesh_cells)
    primary_transformed_label_path = os.path.join(primary_output_folder, 'Remesh_combined_label_transformed.vtk')
    save_polydata_to_vtk(transformed_polydata, primary_transformed_label_path)

    # 对 primary_scan_folder 中其他 STL 文件应用变形矩阵
    for filename in os.listdir(primary_scan_path):
        if filename.endswith('.stl') and filename != 'Remesh_combined_label.stl':
            stl_file = os.path.join(primary_scan_path, filename)
            stl_points, stl_cells = read_stl(stl_file)
            if stl_points is None:
                print(f"Failed to read STL file: {stl_file}")
                continue

            transformed_points = apply_transform(stl_points, transform_matrix)
            transformed_polydata = points_to_polydata(transformed_points, stl_cells)

            output_file = os.path.join(primary_output_folder, f'{filename[:-4]}_transformed.vtk')
            save_polydata_to_vtk(transformed_polydata, output_file)

    # 第二步：对其余 ScanXX 文件夹进行配准
    for scan_folder in scan_folders[1:]:
        scan_path = os.path.join(subject_folder, scan_folder)
        output_scan_folder = os.path.join(output_subject_folder, scan_folder)
        os.makedirs(output_scan_folder, exist_ok=True)

        remesh_combined_label_file = os.path.join(scan_path, 'Remesh_combined_label.stl')
        if not os.path.exists(remesh_combined_label_file):
            print(f"Warning: {remesh_combined_label_file} not found. Skipping {scan_folder}.")
            continue

        # 读取 Remesh_combined_label.stl
        remesh_points, remesh_cells = read_stl(remesh_combined_label_file)
        if remesh_points is None:
            print(f"Failed to read STL file: {remesh_combined_label_file}")
            continue

        # 读取 primary_scan_folder 的配准结果
        primary_transformed_points, primary_transformed_cells = read_vtk(primary_transformed_label_path)
        if primary_transformed_points is None:
            print(f"Failed to read transformed label: {primary_transformed_label_path}")
            continue

        # 配准并获取形变矩阵
        source_polydata = points_to_polydata(remesh_points, remesh_cells)
        target_polydata = points_to_polydata(primary_transformed_points, primary_transformed_cells)

        icp.SetSource(source_polydata)
        icp.SetTarget(target_polydata)
        icp.Update()
        transform_matrix = icp.GetMatrix()

        # 保存 Remesh_combined_label.stl 的配准结果
        transformed_points = apply_transform(remesh_points, transform_matrix)
        transformed_polydata = points_to_polydata(transformed_points, remesh_cells)
        transformed_label_path = os.path.join(output_scan_folder, 'Remesh_combined_label_transformed.vtk')
        save_polydata_to_vtk(transformed_polydata, transformed_label_path)

        # 对 scan_folder 中其他 STL 文件应用变形矩阵
        for filename in os.listdir(scan_path):
            if filename.endswith('.stl') and filename != 'Remesh_combined_label.stl':
                stl_file = os.path.join(scan_path, filename)
                stl_points, stl_cells = read_stl(stl_file)
                if stl_points is None:
                    print(f"Failed to read STL file: {stl_file}")
                    continue

                transformed_points = apply_transform(stl_points, transform_matrix)
                transformed_polydata = points_to_polydata(transformed_points, stl_cells)

                output_file = os.path.join(output_scan_folder, f'{filename[:-4]}_transformed.vtk')
                save_polydata_to_vtk(transformed_polydata, output_file)


# ---- 主函数入口 ----

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Case-by-case rigid registration for one subject.")
    parser.add_argument("--subject_folder", type=str, required=True, help="Path to the subject folder (e.g., 002-S-1234)")
    parser.add_argument("--template_file", type=str, required=True, help="Path to the VTK template file")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to save the output files")
    parser.add_argument("--side", type=str, choices=["Left", "Right"], required=True, help="Hemisphere: Left or Right")
    parser.add_argument("--study", type=str, required=True, help="Study type, e.g., ADNI")

    args = parser.parse_args()

    process_subject(
        subject_folder=args.subject_folder,
        template_file=args.template_file,
        output_folder=args.output_folder,
        side=args.side,
        study=args.study
    )
