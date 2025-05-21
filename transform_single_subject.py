#!/usr/bin/env python
import numpy as np
import os
import vtk
import xml.etree.ElementTree as ET
import argparse

def change_one_xml(xml_path, xml_dw, update_content):
    doc = ET.parse(xml_path)
    root = doc.getroot()
    sub1 = root.find(xml_dw)
    sub1.text = update_content
    doc.write(xml_path)

def CalculateSurfDist(RegressedSurf, OriginalSurf):
    surf_reader = vtk.vtkPolyDataReader()
    surf_reader.SetFileName(RegressedSurf)
    surf_reader.Update()
    RegressedSurf_vtk = surf_reader.GetOutput()

    surf_reader.SetFileName(OriginalSurf)
    surf_reader.Update()
    OriginalSurf_vtk = surf_reader.GetOutput()

    num_pt = RegressedSurf_vtk.GetNumberOfPoints()
    pt_dist = 0
    for i in range(num_pt):
        pt = np.array(RegressedSurf_vtk.GetPoint(i))
        p_closestPoint = np.array(OriginalSurf_vtk.GetPoint(i))
        pt_dist += np.linalg.norm(pt - p_closestPoint)

    return pt_dist

def run_regression(case_dir, model_xml_path, opt_param_xml_path, cache_dir):
    os.environ['MKL_THREADING_LAYER'] = 'GNU'
    os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'

    os.makedirs(cache_dir, exist_ok=True)
    os.system(f"cp {case_dir}/data_set.xml {cache_dir}")

    outputdir = os.path.join(case_dir, "output")
    os.makedirs(outputdir, exist_ok=True)

    cmd = f"deformetrica estimate {model_xml_path} data_set.xml -p {opt_param_xml_path} -o {outputdir}"
    print(f"Running command: {cmd}")  # 打印命令行，便于检查
    
    dist = 0
    N = 15
    eps = 1

    for cyclnum in range(N):
        if dist < eps:
            print(f"[INFO] Regression round {cyclnum+1}")
            print(f"[INFO] Distance between surfaces at round {cyclnum+1}: {dist:.6f}")
            kernel_width = 3 + cyclnum * 0.5
            change_one_xml(model_xml_path, './/deformation-parameters/kernel-width', str(kernel_width))
            os.system(cmd)

            vtk1 = f"{outputdir}/GeodesicRegression__GeodesicFlow__hippo__tp_1__age_1.00.vtk"
            vtk3 = f"{outputdir}/GeodesicRegression__GeodesicFlow__hippo__tp_3__age_3.00.vtk"

            dist = CalculateSurfDist(vtk3, vtk1)
        else:
            print(f"[INFO] Regression succeeded at round {cyclnum+1}")
            return

    print(f"[WARN] Regression did not converge after {N} rounds")

if __name__ == '__main__':
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run deformetrica regression for a single subject's hippocampus.")
    parser.add_argument('--case_dir', type=str, required=True, help="Path to the subject/timepoint folder with data_set.xml")
    parser.add_argument('--side', type=str, choices=['Left', 'Right'], required=True, help="Hippocampus side: Left or Right")
    parser.add_argument('--model_xml', type=str, default=None, help="Path to model.xml")
    parser.add_argument('--opt_param', type=str, default='optimization_parameters.xml', help="Path to optimization_parameters.xml")
    args = parser.parse_args()

    # 设置默认的 model_xml（如果用户没有显式指定）
    if args.model_xml is None:
        args.model_xml = f"model_{args.side}.xml"

    # 将 cache_dir 设置为当前工作目录
    cache_dir = os.getcwd()

    run_regression(args.case_dir, args.model_xml, args.opt_param, cache_dir)
