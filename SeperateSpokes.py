import os
import vtk
import pandas as pd
import numpy as np

def extract_spokes(subject_dir, subfield_list_path):
    """
    输入：
        subject_dir: 该被试的路径，如 /data03/ng/adni_test/data/Baseline/Left/group/subject/scan
        subfield_list_path: 亚区表格路径，如 /data03/ng/adni_test/subfield_list_00.xlsx
    功能：
        对一个被试（左右各一次）重构的hippocampus进行spokes点提取和保存
    """

    # 读取亚区信息
    subfield_info = pd.read_excel(subfield_list_path, header=None)
    subfield_list = subfield_info[0].values
    num_vector = subfield_info[2].astype(int).values
    N_whole = num_vector.sum()
    L_subfield = len(subfield_info)

    # surface vtk 文件路径
    surface_path = os.path.join(subject_dir, 'output', 'GeodesicRegression__Reconstruction__hippo__tp_1__age_3.00.vtk')
    if not os.path.exists(surface_path):
        print(f"VTK surface not found: {surface_path}")
        return

    # 读取 VTK 文件
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(surface_path)
    reader.Update()
    sub_surf = reader.GetOutput()

    # 获取点矩阵
    points = sub_surf.GetPoints()
    raw_pts = [points.GetPoint(i) for i in range(points.GetNumberOfPoints())]
    raw_pts = np.array(raw_pts)[1002:, :]  # 去掉前1002个点

    # 遍历每个亚区，提取 pt 和 ps 并写入 vtk 文件
    for iw in range(L_subfield):
        subfield_name = subfield_list[iw]
        tmp_num = num_vector[iw]

        past_num_vector = num_vector[iw:]
        minus_num = past_num_vector.sum()
        pt_start_row = N_whole - minus_num + 1
        pt_end_row = pt_start_row - 1 + tmp_num // 2
        ps_start_row = pt_end_row + 1
        ps_end_row = ps_start_row - 1 + tmp_num // 2

        pt = raw_pts[pt_start_row-1:pt_end_row, :]
        ps = raw_pts[ps_start_row-1:ps_end_row, :]

        def write_vtk(file_name, points):
            poly_data = vtk.vtkPolyData()
            vtk_points = vtk.vtkPoints()
            for pt in points:
                vtk_points.InsertNextPoint(pt)
            poly_data.SetPoints(vtk_points)
            writer = vtk.vtkPolyDataWriter()
            writer.SetFileName(file_name)
            writer.SetInputData(poly_data)
            writer.Write()

        write_name_pt = os.path.join(subject_dir, f"{subfield_name}_pt.vtk")
        write_name_ps = os.path.join(subject_dir, f"{subfield_name}_ps.vtk")
        write_vtk(write_name_pt, pt)
        write_vtk(write_name_ps, ps)

        print(f"Saved: {write_name_pt} and {write_name_ps}")
