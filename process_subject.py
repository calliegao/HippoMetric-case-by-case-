#!/usr/bin/env python
from __future__ import print_function
import numpy as np
import math
import vtk
from vtk.util.numpy_support import vtk_to_numpy
# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle
# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonCore import (
    mutable,
    vtkPoints
)
from vtkmodules.vtkCommonDataModel import vtkPolygon
import os
import subprocess
import sys
import argparse
import re
import random
import pandas as pd
import scipy.io
from vtk.util.numpy_support import numpy_to_vtk
import logging

# 设置日志记录
log_file_path = os.path.join(os.getcwd(), "refine_spoke_length.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

def extract_random_rows(array, num_rows):
    random_indices = random.sample(range(len(array)), num_rows)
    random_rows = [array[i] for i in random_indices]
    return random_indices, random_rows


def IsInsideCheck(pX, pY, pZ, mesh):
    select = vtk.vtkSelectEnclosedPoints()
    select.SetSurfaceData(mesh)
    select.SetTolerance(1e-4)

    pts = vtk.vtkPoints()
    pts.InsertNextPoint((pX), (pY), (pZ))
    pts_pd = vtk.vtkPolyData()
    pts_pd.SetPoints(pts)
    select.SetInputData(pts_pd)
    select.Update()
    return select.IsInside(0)

def numpy_to_vtk_polydata(points):
    vtk_points = vtk.vtkPoints()
    vtk_array = numpy_to_vtk(points, deep=True, array_type=vtk.VTK_FLOAT)
    vtk_points.SetData(vtk_array)

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtk_points)
    return polydata    

def CalculateNormalVectorofIntersection(pt, surf_vtk):
    # Calculate normal vectors of the surface
    normFilter = vtk.vtkPolyDataNormals()
    normFilter.SetInputData(surf_vtk)
    normFilter.SetComputePointNormals(1)
    normFilter.SetComputeCellNormals(0)
    normFilter.SetAutoOrientNormals(1)
    normFilter.SetSplitting(0)
    normFilter.Update()
    NormalVector = normFilter.GetOutput()  # 已经是VTK文件
    all_Normals = np.array(NormalVector.GetPointData().GetNormals())
    
    # Calculate the closest point of pt on the boundary surface
    cell_locator = vtk.vtkCellLocator()
    cell_locator.SetDataSet(surf_vtk)
    cell_locator.BuildLocator()
    
    c = [0.0, 0.0, 0.0]
    cellId = vtk.reference(0)
    subId = vtk.reference(0)
    d = vtk.reference(0.0)
    
    # Find closest point using locator
    cell_locator.FindClosestPoint(pt, c, cellId, subId, d)
    
    # Get points of the closest cell
    pt_ids = vtk.vtkIdList()
    surf_vtk.GetCellPoints(cellId, pt_ids)
    
    num_cell = pt_ids.GetNumberOfIds()
    if num_cell == 0:
        return None, None  # If no points in the cell, return None
    
    # Initialize vectors
    vector_array = np.zeros((num_cell, 3))
    p_closestPoints = np.zeros((num_cell, 3))
    
    # Calculate normal vector for each point
    for i in range(num_cell):
        pt_id = pt_ids.GetId(i)
        p_closestPoints[i, :] = np.array(surf_vtk.GetPoint(pt_id))
        vector_array[i, :] = all_Normals[pt_id, :]

    # Calculate the mean normal vector
    mean_vector = np.mean(vector_array, axis=0)
    normalVector = mean_vector / np.linalg.norm(mean_vector)
    
    # Return closest point and normalized normal vector
    return p_closestPoints[0, :], normalVector


def IntersectionNumber(pt, ps, surf_vtk):
    # Compute intersection number of spoke and surface
    lamda = 0.05
    spoke = pt - ps
    spoke_length = np.linalg.norm(spoke)

    # Handle the case where the initial spoke length is zero
    if spoke_length < 1e-6:
        return 0

    spoke_dir = spoke / spoke_length
    spoke_dir_new = spoke_dir
    spoke_length_new = spoke_length
    status = 0
    cycle_num = 0
    Last_IsInside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)

    while np.dot(spoke_dir_new, spoke_dir) > 0:
        cycle_num += 1

        # Update the spoke length and check if it's near zero
        spoke = pt - ps
        spoke_length = np.linalg.norm(spoke)
        if spoke_length < 1e-3:
            break

        spoke_dir = spoke / spoke_length

        # Update the point along the direction
        pt = pt - lamda * spoke_dir

        # Update new spoke length and direction
        spoke = pt - ps
        spoke_length_new = np.linalg.norm(spoke)
        if spoke_length_new < 1e-3:
            break

        spoke_dir_new = spoke / spoke_length_new

        # Check if the point is inside or outside the surface
        IsInside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)

        # Detect crossing of surface boundary
        if IsInside != Last_IsInside:
            status += 1

        Last_IsInside = IsInside

    return status



def IntersectionNumber1(pt, ps, surf_vtk):
    import numpy as np

    # Compute intersection number of spoke and surface
    lamda = 0.05
    spoke = pt - ps
    spoke_length = np.linalg.norm(spoke)

    # Handle the case where initial spoke length is zero
    if spoke_length < 1e-3:
        return [], 0

    spoke_dir = spoke / spoke_length
    status = 0
    intersections = []
    Last_IsInside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)

    while spoke_length > 1e-3:  # Add a threshold for spoke length to stop the loop
        # Update the point along the direction
        pt -= lamda * spoke_dir

        # Update the spoke vector, length, and direction
        spoke = pt - ps
        spoke_length = np.linalg.norm(spoke)

        if spoke_length < 1e-3:  # Handle near-zero spoke length
            break

        spoke_dir = spoke / spoke_length

        # Check if the point is inside or outside the surface
        IsInside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)

        # Detect crossing of surface boundary
        if IsInside != Last_IsInside:
            status += 1
            intersections.append(pt.copy())  # Record the crossing point
        
        Last_IsInside = IsInside

        # Early exit if too many intersections are detected
        if status > 2:
            break

    # Return the intersections based on status
    if status > 2:
        return intersections[-2:], status
    else:
        return intersections, status


def RefineSpokeLength(surf_vtk, pt_vtk, ps_vtk, eps_s, pt_path):

    # 将 VTK 点数据转换为 NumPy 数组
    pt_points = vtk_to_numpy(pt_vtk.GetPoints().GetData())
    ps_points = vtk_to_numpy(ps_vtk.GetPoints().GetData())

    num_pt = pt_points.shape[0]  # 获取点的数量
    pt_array = np.zeros_like(pt_points)  # 创建与 pt_points 相同形状的空数组

    # 最大迭代次数
    max_iter = 1000
    
    pt_dir = pt_path

    # 处理每个点
    for i in range(num_pt):
        pt = pt_points[i, :]
        ps = ps_points[i, :]
        displacement = pt - ps  # 缓存位移
        spoke_length = np.linalg.norm(displacement)

        if spoke_length != 0:
            spoke_dir = displacement / spoke_length
            intersect_num = IntersectionNumber(pt, ps, surf_vtk)
            is_inside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)

            iter_count = 0

            if intersect_num == 0:
                while is_inside:
                    pt += spoke_dir * eps_s
                    is_inside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break

            elif intersect_num == 1:
                while not is_inside:
                    pt -= spoke_dir * eps_s
                    is_inside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break

            elif intersect_num == 2:
                while intersect_num == 1:
                    pt -= spoke_dir * eps_s
                    intersect_num = IntersectionNumber(pt, ps, surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break
                while not is_inside:
                    pt -= spoke_dir * eps_s
                    is_inside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break

            elif intersect_num == 3:
                while intersect_num == 2:
                    pt -= spoke_dir * eps_s
                    intersect_num = IntersectionNumber(pt, ps, surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break
                while intersect_num == 1:
                    pt -= spoke_dir * eps_s
                    intersect_num = IntersectionNumber(pt, ps, surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break
                while not is_inside:
                    pt -= spoke_dir * eps_s
                    is_inside = IsInsideCheck(pt[0], pt[1], pt[2], surf_vtk)
                    iter_count += 1
                    if iter_count > max_iter:
                        logging.warning(
                            f"Max iterations reached in pt_path: {pt_dir}"
                        )
                        break

        pt_array[i, :] = pt

    # 使用 numpy_to_vtk_polydata 来创建 vtkPolyData 对象
    pt_vtk_LengthRefined = numpy_to_vtk_polydata(pt_array)
    
    return pt_vtk_LengthRefined



def RefineSpokeDirection(surf_vtk, pt_vtk, ps_vtk, eps_d, pt_path):
    # 将 VTK 点数据转换为 NumPy 数组
    pt_points = vtk_to_numpy(pt_vtk.GetPoints().GetData())
    ps_points = vtk_to_numpy(ps_vtk.GetPoints().GetData())

    num_pt = pt_points.shape[0]  # 获取点的数量
    pt_array = np.zeros_like(pt_points)  # 创建与 pt_points 相同形状的空数组

    alpha = 0.5  # alpha 越大越接近 normalvector

    for i in range(num_pt):
        pt = pt_points[i, :]
        ps = ps_points[i, :]
        if np.linalg.norm(pt - ps) != 0:
            spoke = pt - ps
            spoke_length = np.linalg.norm(spoke)
            spoke_dir = spoke / spoke_length
            cos_angle = 0
            circle_num = 0

            while (1 - cos_angle) > eps_d and circle_num < 50:
                circle_num += 1

                # Calculate normal vector
                p_closestPoint, nomalVector = CalculateNormalVectorofIntersection(pt, surf_vtk)

                # Update spoke direction
                medial_vector = (alpha * spoke_dir + (1 - alpha) * nomalVector)
                mv = medial_vector / np.linalg.norm(medial_vector)
                pt = ps + spoke_length * mv

                spoke = pt - ps
                spoke_length = np.linalg.norm(spoke)
                spoke_dir = spoke / spoke_length
                cos_angle = np.dot(spoke_dir, nomalVector)

                # Logging
                #logging.info(f"Point {i}, Iter {circle_num}: cos_angle={cos_angle}, spoke_length={spoke_length}")

            if circle_num >= 100:
                logging.warning(f"Max iterations reached for RefineSpokeDirection in pt_path: {pt_path}")

        pt_array[i, :] = pt

    pt_vtk_DirectionRefined = numpy_to_vtk_polydata(pt_array)
    return pt_vtk_DirectionRefined


def EqualSpokeLength(pt_vtk, ps_vtk, eps_e):  # tips points, skeleton points, error
    num_pt = pt_vtk.GetNumberOfPoints()
    pt_array = np.zeros((num_pt, 3))
    num_ps = ps_vtk.GetNumberOfPoints()
    ps_array = np.zeros((num_ps, 3))
    InnerSpokeLength = np.zeros((549, 2))  # ((549, 2))
    finished_points = 0
    for i in range(num_pt):
        pt_array[i, :] = np.array(pt_vtk.GetPoint(i))
        ps_array[i, :] = np.array(ps_vtk.GetPoint(i))
        pt = pt_array[i, :]
        ps = ps_array[i, :]
        if np.linalg.norm(pt - ps) != 0:
            spoke = pt - ps
            spoke_length = np.linalg.norm(spoke)
        else:
            spoke_length = 0
        if i < 549:  # 549:
            InnerSpokeLength[i, 0] = spoke_length
        elif i >= 549 and i < 1098:
            InnerSpokeLength[i - 549, 1] = spoke_length  # InnerSpokeLength[i-549,1] = spoke_length
        # print(InnerSpokeLength)
        # print(pt_array)
    for i in range(549):
        finished_points += 1
        lengthDiff = InnerSpokeLength[i, 0] - InnerSpokeLength[i, 1]
        # print(lengthDiff)
        if abs(lengthDiff) > eps_e:
            if InnerSpokeLength[i, 0] > InnerSpokeLength[i, 1]:
                pt = pt_array[i, :]
                ps = ps_array[i, :]
                if np.linalg.norm(pt_array[i + 549, :] - ps_array[i + 549, :]) != 0:
                    spoke = pt - ps
                    spoke_dir = spoke / InnerSpokeLength[i, 1]
                    pt = ps + InnerSpokeLength[i, 1] * spoke_dir
                else:
                    pt = ps
                InnerSpokeLength[i, 0] = np.linalg.norm(pt - ps)
                pt_array[i, :] = pt
            elif InnerSpokeLength[i, 0] < InnerSpokeLength[i, 1]:
                pt = pt_array[i + 549, :]  # [i+549,:]
                ps = ps_array[i + 549, :]  # [i+549,:]
                if np.linalg.norm(pt_array[i - 549, :] - ps_array[i - 549, :]) != 0:
                    spoke = pt - ps
                    spoke_dir = spoke / InnerSpokeLength[i, 1]
                    pt = ps + InnerSpokeLength[i, 0] * spoke_dir
                else:
                    pt = ps
                InnerSpokeLength[i, 1] = np.linalg.norm(pt - ps)
                pt_array[i + 549, :] = pt  # pt_array[i+549, :] = pt
        # print('Equalize Spoke Length Finished Points: %s of Total 549' % str(finished_points))
    # print(InnerSpokeLength)
    # print(pt_array)
    # 使用 numpy_to_vtk_polydata 来创建 vtkPolyData 对象
    pt_vtk_EualizedLength = numpy_to_vtk_polydata(pt_array)
    return pt_vtk_EualizedLength


def ClosestSurfPoint(ps, surf_vtk):
    # Set up the cell locator
    cell_locator = vtk.vtkCellLocator()
    cell_locator.SetDataSet(surf_vtk)
    cell_locator.BuildLocator()

    # Variables for closest point search
    c = [0.0, 0.0, 0.0]
    cell_locator.FindClosestPoint(ps, c, vtk.reference(0), vtk.reference(0), vtk.reference(0.0))

    # Get the closest point coordinates directly
    p_closestPoint = np.array(c)

    return p_closestPoint


def RepairSkeleton(surf_vtk, pt_vtk, ps_vtk):
    # 将 VTK 点数据转换为 NumPy 数组
    pt_points = vtk_to_numpy(pt_vtk.GetPoints().GetData())
    ps_points = vtk_to_numpy(ps_vtk.GetPoints().GetData())

    num_pt = pt_points.shape[0]  # 获取点的数量
    pt_array = np.zeros_like(pt_points)  # 创建与 pt_points 相同形状的空数组
    ps_array = np.zeros_like(ps_points)  # 创建与 ps_points 相同形状的空数组

    finished_points = 0
    invalid_num = 0

    for i in range(num_pt):
        finished_points += 1
        pt = pt_points[i, :]
        ps = ps_points[i, :]
        IsInside = IsInsideCheck(ps[0], ps[1], ps[2], surf_vtk)
        if IsInside == 0:
            # print('Point %s is inside surface'% str(i))
            # 替换该点为最临近的曲面点
            ps = ClosestSurfPoint(ps, surf_vtk)
            pt = ps
        pt_array[i, :] = pt
        ps_array[i, :] = ps
        # print('Repair Skeleton Finished Points: %s' % str(finished_points))
    # 使用 numpy_to_vtk_polydata 来创建 vtkPolyData 对象
    RepairTips = numpy_to_vtk_polydata(pt_array)
    RepairSkeleton = numpy_to_vtk_polydata(ps_array)
    return RepairSkeleton, RepairTips

def GenerateOutside_pts(surf_vtk, pt_vtk, ps_vtk):
    num_pt = pt_vtk.GetNumberOfPoints()
    pt_array = np.zeros((num_pt, 3))
    num_ps = ps_vtk.GetNumberOfPoints()
    ps_array = np.zeros((num_ps, 3))
    finished_points = 0
    invaild_num = 0
    for i in range(num_ps):
        finished_points += 1
        pt_array[i, :] = np.array(pt_vtk.GetPoint(i))
        ps_array[i, :] = np.array(ps_vtk.GetPoint(i))
        pt = pt_array[i, :]
        ps = ps_array[i, :]
        if np.array_equal(pt, ps):
            #print("Point ps is the same as point pt.")
            pt_array[i, :] = pt
            ps_array[i, :] = ps
        else:
            # print(pt)
            # print(ps)
            spoke = pt - ps
            # print(spoke)
            length = np.linalg.norm(spoke)
            # print(length)
            spoke /= length
            spoke *= 10.0
            pt = ps+spoke
            intersect_point, q = IntersectionNumber1(pt,ps,surf_vtk)
            if q>=2:
                #print('Spoke %s direction available,calculate intersection points'%str(i))
                pt_array[i, :] = intersect_point[0]
                ps_array[i, :] = intersect_point[1]
                # print(pt_array[i, :])
                # print(ps_array[i, :])
            else:
                #print('Spoke'  + str(i) + ' has ' + str(q) + ' points, direction unavailable,set pt equal ps' )
                pt_array[i, :] = ps
                ps_array[i, :] = ps
                invaild_num += 1
                # print(pt_array[i, :])
                # print(ps_array[i, :])
        #print('Repair Skeleton Finished Points: %s' % str(finished_points))
    #print('invalid points num is ' + str(invaild_num))
    # 使用 numpy_to_vtk_polydata 来创建 vtkPolyData 对象
    RepairTips = numpy_to_vtk_polydata(pt_array)
    RepairSkeleton = numpy_to_vtk_polydata(ps_array)
    return RepairSkeleton, RepairTips


def list2array(ps, pt, indices):
    ps_array = np.array(ps)
    pt_array = np.array(pt)
    index_array = np.array(indices)
    num_row = index_array.shape[0]
    ps = vtk.vtkPoints()
    pt = vtk.vtkPoints()
    for j in range(num_row):
        ps.InsertNextPoint((ps_array[j, 0]), (ps_array[j, 1]), (ps_array[j, 2]))
        pt.InsertNextPoint((pt_array[j, 0]), (pt_array[j, 1]), (pt_array[j, 2]))
    ps_poly = vtk.vtkPolyData()
    pt_poly = vtk.vtkPolyData()
    ps_poly.SetPoints(ps)
    pt_poly.SetPoints(pt)
    return ps_poly, pt_poly, index_array


def classify_points(ps_vtk, pt_vtk, surf_vtk,):
    num_ps = ps_vtk.GetNumberOfPoints()
    ps_inside_indices = []
    ps_outside_indices = []
    ps_inside = []
    pt_inside = []
    ps_outside = []
    pt_outside = []
    finished_points = 0

    for i in range(num_ps):
        finished_points += 1
        ps_array = np.array(ps_vtk.GetPoint(i))
        pt_array = np.array(pt_vtk.GetPoint(i))
        if IsInsideCheck(ps_array[0], ps_array[1], ps_array[2], surf_vtk) == 1:
            #print('Point %s is inside surface' % str(i))
            ps_inside.append(ps_array)
            ps_inside_indices.append(i)
            pt_inside.append(pt_array)
        else:
            #print('Point %s is outside surface' % str(i))
            ps_outside.append(ps_array)
            ps_outside_indices.append(i)
            pt_outside.append(pt_array)

    ps_inside_vtk, pt_inside_vtk, inside_indices = list2array(ps_inside, pt_inside, ps_inside_indices)
    ps_outside_vtk, pt_outside_vtk, outside_indices = list2array(ps_outside, pt_outside, ps_outside_indices)

    return ps_inside_vtk, pt_inside_vtk, ps_outside_vtk, pt_outside_vtk, inside_indices, outside_indices, num_ps

def merge_vtk(ps_i, pt_i, i_index, ps_o, pt_o, o_index):
    # 获取两个数据集的行数
    row_inside = i_index.shape[0]
    row_outside = o_index.shape[0]
    num = row_inside + row_outside
    
    # 创建vtk点集
    pts = vtk.vtkPoints()
    pss = vtk.vtkPoints()

    # 处理内部索引
    for i in range(row_inside):
        index_in = i_index[i]
        pts.InsertNextPoint(pt_i.GetPoint(i))
        pss.InsertNextPoint(ps_i.GetPoint(i))

    # 处理外部索引
    for z in range(row_outside):
        index_out = o_index[z]
        pts.InsertNextPoint(pt_o.GetPoint(z))
        pss.InsertNextPoint(ps_o.GetPoint(z))

    # 创建PolyData对象
    RepairSkeleton = vtk.vtkPolyData()
    RepairTips = vtk.vtkPolyData()

    # 设置点数据
    RepairSkeleton.SetPoints(pss)
    RepairTips.SetPoints(pts)

    return RepairSkeleton, RepairTips


def check_vtk_has_cells(vtk_data, vtk_file_path):
    """
    检查vtk数据是否包含cell，如果没有，则抛出错误并提示路径。
    """
    if vtk_data.GetNumberOfCells() == 0:
        raise ValueError(f"Error: VTK file '{vtk_file_path}' has no cells to build.")

def Generate_final_pts(pt_path, ps_path, surf_path, output_path1, output_path2):
    eps_s = 0.1
    eps_d = 0.1
    eps_e = 0.1

    output_dir1 = output_path1
    output_dir2 = output_path2

    # 读取 pt VTK 文件
    pt = pt_path
    pt_reader = vtk.vtkPolyDataReader()
    pt_reader.SetFileName(pt)
    pt_reader.Update()
    pt_vtk = pt_reader.GetOutput()

    # 检查 pt 数据是否有效
    #check_vtk_has_cells(pt_vtk, pt)

    # 读取 ps VTK 文件
    ps = ps_path
    ps_reader = vtk.vtkPolyDataReader()
    ps_reader.SetFileName(ps)
    ps_reader.Update()
    ps_vtk = ps_reader.GetOutput()

    # 检查 ps 数据是否有效
    #check_vtk_has_cells(ps_vtk, ps)

    # 读取 surf VTK 文件
    surf = surf_path
    surf_reader = vtk.vtkPolyDataReader()
    surf_reader.SetFileName(surf)
    surf_reader.Update()
    surf_vtk = surf_reader.GetOutput()

    # 检查 surf 数据是否有效
    #check_vtk_has_cells(surf_vtk, surf)

    # 分割点（inside 和 outside）
    ps_inside_vtk, pt_inside_vtk, ps_outside_vtk, pt_outside_vtk, inside_indices, outside_indices, num_all = classify_points(ps_vtk, pt_vtk, surf_vtk)
    print("Finish classify_points!")
    
    pt_vtk_EualizedLength = pt_inside_vtk
    pt_vtk_RefinedDircetion = pt_inside_vtk
    # refine inside spoke directions
    pt_vtk_RefinedDircetion = RefineSpokeDirection(surf_vtk, pt_vtk_EualizedLength, ps_inside_vtk, eps_d, pt)
    print("Finish RefineSpokeDirection!")
    
    # refine spoke length
    pt_vtk_RefinedLength = RefineSpokeLength(surf_vtk, pt_vtk_RefinedDircetion, ps_inside_vtk, eps_s, pt)
    print("Finish RefineSpokeLength!")
 
    # 修复outside points
    ps_outside_vtk_repair, pt_outside_vtk_repair = GenerateOutside_pts(surf_vtk, pt_outside_vtk, ps_outside_vtk)
    print("Finish GenerateOutside_pts!")

    # 合并 points
    ps_final, pt_final = merge_vtk(ps_inside_vtk, pt_vtk_RefinedLength, inside_indices, ps_outside_vtk_repair, pt_outside_vtk_repair, outside_indices)
    print("Finish merge_vtk!")

    # 写入输出文件
    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(output_dir1)
    writer.SetInputData(pt_final)
    writer.Update()

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(output_dir2)
    writer.SetInputData(ps_final)
    writer.Update()
    # print(f"Finished processing: {pt_path}, {ps_path}, {surf_path}")

def load_mat_file(mat_filename):
    # 使用 scipy.io.loadmat 读取 .mat 文件
    mat_data = scipy.io.loadmat(mat_filename)
    
    # 输出所有键值，查看文件中包含的变量名
    # print("Keys in the loaded .mat file:", mat_data.keys())
    
    # 获取 'point_order' 数据
    point_order = mat_data['point_order']
    
    # 提取 crest_order 和 crest_neighbor
    # 在 MATLAB 中是从 9 和 6 行取数据，因此在 Python 中取索引 8 和 5
    crest_order = point_order[8, :64]  # 9 行对应 Python 索引 8
    crest_neighbor = point_order[5, :64]  # 6 行对应 Python 索引 5
    # print(f"crest_order: {crest_order}",f"crest_neighbor: {crest_neighbor}")
    return {'crest_order': crest_order, 'crest_neighbor': crest_neighbor}

def Add_CrestSpoke(pt_vtk_RefinedDircetion, ps_repaired_vtk, crest_order, crest_neighbor, lamda=1):
    # 将 vtkPolyData 转换为 NumPy 数组
    pt_points = vtk_to_numpy(pt_vtk_RefinedDircetion.GetPoints().GetData())
    ps_points = vtk_to_numpy(ps_repaired_vtk.GetPoints().GetData())

    # 计算 crest spoke
    CrestSkelPt = ps_points[crest_order.astype(int)-1]
    CrestSkelPtNeighbor = ps_points[crest_neighbor.astype(int)-1]
    crest_spokes = lamda * (CrestSkelPt - CrestSkelPtNeighbor)
    CrestBdryPt = CrestSkelPt + crest_spokes;
    BdryPt_new = np.vstack([pt_points, CrestBdryPt])
    SkelPt_new = np.vstack([ps_points, CrestSkelPt])

    # 将 NumPy 数组转换回 vtkPolyData 格式
    pt_vtk_addCrest = numpy_to_vtk_polydata(BdryPt_new)
    ps_vtk_addCrest = numpy_to_vtk_polydata(SkelPt_new)

    return pt_vtk_addCrest, ps_vtk_addCrest        
   
def Generate_final_hippo_pts(pt_path, ps_path, surf_path, output_path1, output_path2, is_followup=False):
    eps_s = 0.1
    eps_d = 0.1
    eps_e = 0.1
    
    ptod_name = "/home/nagao/point_order_skeleton.mat"  # 假设文件名为 point_order_skeleton.mat
    point_order = load_mat_file(ptod_name)

    output_dir1 = output_path1
    output_dir2 = output_path2

    # 读取 pt VTK 文件
    pt = pt_path
    pt_reader = vtk.vtkPolyDataReader()
    pt_reader.SetFileName(pt)
    pt_reader.Update()
    pt_vtk = pt_reader.GetOutput()

    # 读取 ps VTK 文件
    ps = ps_path
    ps_reader = vtk.vtkPolyDataReader()
    ps_reader.SetFileName(ps)
    ps_reader.Update()
    ps_vtk = ps_reader.GetOutput()

    # 读取 surf VTK 文件
    surf = surf_path
    surf_reader = vtk.vtkPolyDataReader()
    surf_reader.SetFileName(surf)
    surf_reader.Update()
    surf_vtk = surf_reader.GetOutput()
    
    # 修正骨架点露到外边的
    ps_repaired_vtk, pt_repaired_vtk = RepairSkeleton(surf_vtk, pt_vtk, ps_vtk)
    
    # refine inside spoke directions
    pt_vtk_RefinedDircetion = RefineSpokeDirection(surf_vtk, pt_vtk, ps_repaired_vtk, eps_d, pt)
    print("Finish RefineSpokeDirection!")
    
    if not is_followup:  # 只有在处理基线数据时才需要装上crest spokes
        # 装上crest spokes
        pt_vtk_addCrest, ps_vtk_addCrest = Add_CrestSpoke(pt_vtk_RefinedDircetion, ps_repaired_vtk, point_order['crest_order'], point_order['crest_neighbor'], lamda=1)
    else:
        # 如果是随访数据，不进行 crest spokes 的装配
        pt_vtk_addCrest, ps_vtk_addCrest = pt_vtk_RefinedDircetion, ps_repaired_vtk
    
    # refine spoke length
    pt_vtk_RefinedLength = RefineSpokeLength(surf_vtk, pt_vtk_addCrest, ps_vtk_addCrest, eps_s, pt)
    print("Finish RefineSpokeLength!")
    
    # 写入输出文件
    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(output_dir1)
    writer.SetInputData(pt_vtk_RefinedLength)
    writer.Update()

    writer = vtk.vtkPolyDataWriter()
    writer.SetFileName(output_dir2)
    writer.SetInputData(ps_vtk_addCrest)
    writer.Update()

def process_single_subject(
    baseline_path,         # 跟 args.baseline_path 对应
    followup_path,         # 跟 args.followup_path 对应
    subfield_list,         # 从表格中读出
    subject,               # 跟 args.subject 对应
    side,                  # 跟 args.side 对应
    group,                 # 跟 args.group 对应
    subfield_file          # 表格原始对象（可能用于原始信息）
):
    """
    处理单个被试的所有数据，包括基线和多个扫描时间点。
    """
    # 处理基线数据
    raw_dir = os.path.join(baseline_path, side)  # 对应侧面的文件夹
    print(f"Processing Side: {side}, Subject: {subject}, Group: {group}")

    # 组文件夹在侧面文件夹下，进入组文件夹
    raw_Inputdir = os.path.join(raw_dir, group, subject)  # 进入对应被试的文件夹
    if os.path.exists(raw_Inputdir):
        for timepoint in os.listdir(raw_Inputdir):  # 遍历每个扫描时间点
            sub_dir = os.path.join(raw_Inputdir, timepoint)

            for subfield_name in subfield_list:  # 遍历每个亚区
                pt_path = os.path.join(sub_dir, f"{subfield_name}_pt.vtk")
                ps_path = os.path.join(sub_dir, f"{subfield_name}_ps.vtk")
                surf_path = os.path.join(sub_dir, f"Remesh_{subfield_name}_transformed.vtk")
                output_path1 = os.path.join(sub_dir, f"{subfield_name}_pt_refined.vtk")
                output_path2 = os.path.join(sub_dir, f"{subfield_name}_ps_refined.vtk")

                # 日志并调用处理函数
                print(f"Processing Subject: {subject}, Timepoint: {timepoint}, Subfield: {subfield_name}")
                if subfield_name == "combined_label":
                    # 针对 combined_label 调用专用函数
                    Generate_final_hippo_pts(pt_path, ps_path, surf_path, output_path1, output_path2, is_followup=False)
                else:
                    # 其他 subfield 使用通用函数
                    Generate_final_pts(pt_path, ps_path, surf_path, output_path1, output_path2)

        # 处理Follow-ups
        followup_dir = os.path.join(followup_path, side)  # 对应侧面文件夹
        print(f"Processing Follow-ups for Subject: {subject}, Group: {group}")

        followup_subject_dir = os.path.join(followup_dir, group, subject)  # 进入随访数据对应被试文件夹
        if os.path.exists(followup_subject_dir):
            for timepoints in os.listdir(followup_subject_dir):  # 遍历随访扫描时间点
                fl_sub_dir = os.path.join(followup_subject_dir, timepoints)
                for subfield_name in subfield_list:  # 遍历每个亚区
                    pt_path = os.path.join(sub_dir, f"{subfield_name}_pt_refined.vtk")
                    ps_path = os.path.join(sub_dir, f"{subfield_name}_ps_refined.vtk")
                    surf_path = os.path.join(fl_sub_dir, f"Remesh_{subfield_name}_transformed.vtk")
                    output_path1 = os.path.join(fl_sub_dir, f"{subfield_name}_pt_refined.vtk")
                    output_path2 = os.path.join(fl_sub_dir, f"{subfield_name}_ps_refined.vtk")

                    # 日志并调用处理函数
                    print(f"Processing Follow-up for Subject: {subject}, Timepoint: {timepoints}, Subfield: {subfield_name}")
                    if subfield_name == "combined_label":
                        # 针对 combined_label 调用专用函数
                        Generate_final_hippo_pts(pt_path, ps_path, surf_path, output_path1, output_path2, is_followup=True)
                    else:
                        # 其他 subfield 使用通用函数
                        Generate_final_pts(pt_path, ps_path, surf_path, output_path1, output_path2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process a single subject's data.")
    parser.add_argument('subject', type=str, help="The subject ID to process")
    parser.add_argument('side', type=str, choices=['Left', 'Right'], help="The side (Left or Right)")
    parser.add_argument('group', type=str, help="The group to process")
    parser.add_argument('--baseline_path', type=str, required=True, help="Path to baseline data")
    parser.add_argument('--followup_path', type=str, required=True, help="Path to followup data")
    parser.add_argument('--subfield_file', type=str, required=True, help="Path to subfield list file (.xlsx)")

    args = parser.parse_args()

    # 读取 subfield 表格
    subfield_file = pd.read_excel(args.subfield_file)
    subfield_list = subfield_file['Subfield']

    # 调用处理函数
    process_single_subject(
        baseline_path=args.baseline_path,
        followup_path=args.followup_path,
        subfield_list=subfield_list,
        subject=args.subject,
        side=args.side,
        group=args.group,
        subfield_file=subfield_file
    )
