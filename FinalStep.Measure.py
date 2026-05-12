import os
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import vtk
from vtk.util import numpy_support
import scipy.io

def build_skeleton_order(point_order):
    """
    Build skeletonPt_order according to MATLAB logic (17x31, 0-based indexing)
    
    Parameters:
        point_order: numpy array, shape (9, 65) or larger, storing 1-based point indices
    
    Returns:
        skeletonPt_order: numpy array, shape (17, 31), dtype=int, 0-based indices
    """
    # Extract SkelLat (columns 0:32)
    SkelLat = point_order[:, 0:32]  # shape (9, 32)
    
    # Extract SkelVen (columns 33:65)
    SkelVen = point_order[:, 33:65]  # shape (9, 32)
    
    # Flip upside down (flipud)
    Ranged_SkelVen = np.flip(SkelVen, axis=0)  # shape (9, 32)
    # Flip left to right (fliplr)
    Ranged_SkelVen = np.flip(Ranged_SkelVen, axis=1)  # shape (9, 32)
    
    # Vertical concatenation
    SkelOrder = np.vstack([Ranged_SkelVen, SkelLat])  # shape (18, 32)
    
    # Delete row 8 (MATLAB row 9)
    SkelOrder = np.delete(SkelOrder, 8, axis=0)  # shape (17, 32)
    
    # Delete column 0 (MATLAB column 1)
    SkelOrder = np.delete(SkelOrder, 0, axis=1)  # shape (17, 31)
    
    # Convert to 0-based indexing if values start from 1
    if np.min(SkelOrder) == 1:
        SkelOrder = SkelOrder - 1
    
    return SkelOrder

def read_vtk_points(vtk_file):
    """
    Read point coordinates from a VTK file
    """
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(vtk_file)
    reader.Update()
    polydata = reader.GetOutput()
    points = polydata.GetPoints()
    points_np = numpy_support.vtk_to_numpy(points.GetData())
    
    # Replace NaN values with zero
    points_np = np.nan_to_num(points_np)

    return points_np

def compute_thickness(pt_points, ps_points):
    """
    Compute subfield thickness using Euclidean distance
    """
    return cdist(pt_points, ps_points, 'euclidean')

def compute_width(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    Compute the width of a subfield.
    
    Parameters:
    - SkelPt: skeleton points, usually from `{subfield}_ps_refined.vtk`.
    - skeletonPt_order: skeleton point order generated from point_order.
    - crest_spoke_length: crest spoke lengths, calculated from BdryPt and SkelPt.

    Returns:
    - width1: first width value
    - width2: second width value
    """
    width1 = np.zeros(31)
    width2 = np.zeros(31)

    for width_n in range(31):
        sum_segment1 = 0
        for sn in range(9):
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment1 += each_segment

        sum_segment2 = 0
        for sn in range(8, 16):
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment2 += each_segment

        # Add crest spoke lengths
        crest1 = crest_spoke_length[width_n+1]
        crest2 = crest_spoke_length[63 - width_n]
        width1[width_n] = sum_segment1 + crest1
        width2[width_n] = sum_segment2 + crest2

    return width1, width2

def compute_length(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    Compute the length of a subfield.
    
    Parameters:
    - SkelPt: skeleton points, usually from `{subfield}_ps_refined.vtk`.
    - skeletonPt_order: skeleton point order generated from point_order.
    - crest_spoke_length: crest spoke lengths, calculated from BdryPt and SkelPt.

    Returns:
    - Sub_length1: first length value
    - Sub_length2: second length value
    """
    sum_segment3 = 0
    for sn in range(16):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment3 += each_segment2

    sum_segment4 = 0
    for sn in range(15, 30):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment4 += each_segment2

    Sub_length1 = sum_segment3 + crest_spoke_length[0]
    Sub_length2 = sum_segment4 + crest_spoke_length[32]

    return Sub_length1, Sub_length2

def load_point_order(mat_file_path):
    """
    Load 'point_order' from a .mat file
    """
    mat_data = scipy.io.loadmat(mat_file_path)
    return mat_data['point_order']

def compute_subfield_measures(scan_folder_path, subfield, point_order_mat):
    """
    Compute subfield measurements: thickness, width, length
    """
    point_order = load_point_order(point_order_mat)
    
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    SkelPt = read_vtk_points(ps_file)
    BdryPt = read_vtk_points(pt_file)
    
    refined_spokes = BdryPt - SkelPt
    crest_spoke_length = np.linalg.norm(refined_spokes[1098:1162], axis=1)
    
    skeletonPt_order = build_skeleton_order(point_order) - 1
    
    width1, width2 = compute_width(SkelPt, skeletonPt_order, crest_spoke_length)
    Sub_length1, Sub_length2 = compute_length(SkelPt, skeletonPt_order, crest_spoke_length)
    
    total_width = width1 + width2
    total_length = Sub_length1 + Sub_length2
    
    thickness = compute_thickness(BdryPt, SkelPt)
    thickness_bilateral = np.diagonal(thickness)
    inf_thickness = thickness_bilateral[:len(thickness_bilateral)//2]
    sup_thickness = thickness_bilateral[len(thickness_bilateral)//2:]
    
    return inf_thickness, sup_thickness, width1, width2, total_width, Sub_length1, Sub_length2, total_length

def compute_subfield_thickness(scan_folder_path, subfield):
    """
    Compute subfield thickness only
    """
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    if os.path.exists(pt_file) and os.path.exists(ps_file):
        pt_points = read_vtk_points(pt_file)
        ps_points = read_vtk_points(ps_file)
        
        thickness = compute_thickness(pt_points, ps_points)
        thickness_bilateral = np.diagonal(thickness)
        mid_index = len(thickness_bilateral) // 2
        subfield_thickness = thickness_bilateral[:mid_index] + thickness_bilateral[mid_index:]
        
        return subfield_thickness
    else:
        print(f"Error: VTK files for subfield {subfield} not found!")
        return None

def process_followups(followups_path, output_path, point_order_mat):
    """
    Process all subjects and scans to compute hippocampal subfield measures
    and save the results into an Excel file
    """
    subfield_df = pd.read_excel('/home/guolab/HippMetric/subfield_list_00.xlsx', header=None)
    subfield_list = subfield_df.iloc[:, 0].tolist()
    print(f"All Subfields: {subfield_list}")

    N_vector = subfield_df.iloc[:, 3].values
    all_thickness = []
    subfield_lengths = {}

    for side in ['Left', 'Right']:
        for group in ["group"]:
            group_path = os.path.join(followups_path, side, group)

            for subject in os.listdir(group_path):
                subject_path = os.path.join(group_path, subject)
                if os.path.isdir(subject_path):
                    scan_folders = [scan_folder for scan_folder in os.listdir(subject_path) if scan_folder.startswith('Scan')]
                    scan_folders = sorted(scan_folders, key=lambda x: int(x[4:]))
                    processed_scans = set()

                    for scan_folder in scan_folders:
                        if scan_folder in processed_scans:
                            continue

                        scan_folder_path = os.path.join(subject_path, scan_folder)
                        if os.path.exists(scan_folder_path) and os.path.isdir(scan_folder_path):
                            processed_scans.add(scan_folder)
                            scan_measures = [subject, scan_folder, side, group]

                            for i, subfield in enumerate(subfield_list):
                                N_points = N_vector[i]
                                if subfield == 'combined_label':
                                    inf_thickness, sup_thickness, width1, width2, total_width, Sub_length1, Sub_length2, total_length = compute_subfield_measures(scan_folder_path, subfield, point_order_mat)
                                    scan_measures.extend(inf_thickness)
                                    scan_measures.extend(sup_thickness)
                                    scan_measures.extend(width1)
                                    scan_measures.extend(width2)
                                    scan_measures.extend(total_width)
                                    scan_measures.append(Sub_length1)
                                    scan_measures.append(Sub_length2)
                                    scan_measures.append(total_length)
                                    subfield_lengths[subfield] = {
                                        'InfThickness': len(inf_thickness),
                                        'SupThickness': len(sup_thickness),
                                        'LatWidth': len(width1),
                                        'VenWidth': len(width2),
                                        'Width': len(total_width),
                                    }
                                else:
                                    subfield_thickness = compute_subfield_thickness(scan_folder_path, subfield)
                                    scan_measures.extend(subfield_thickness)
                                    subfield_lengths[subfield] = {'Thickness': len(subfield_thickness)}

                            all_thickness.append(scan_measures)
                            print(f"Completed Side {side}, Group {group}, Subject {subject}, Scan {scan_folder}")

    columns = ["Subject ID", "Scan ID", "Side", "Group"]
    for subfield in subfield_list:
        if subfield == 'combined_label':
            lengths = subfield_lengths.get(subfield, {})
            columns += [f'{subfield} InfThickness {i}' for i in range(1, lengths.get('InfThickness', 0) + 1)]
            columns += [f'{subfield} SupThickness {i}' for i in range(1, lengths.get('SupThickness', 0) + 1)]
            columns += [f'{subfield} LatWidth {i}' for i in range(1, lengths.get('LatWidth', 0) + 1)]
            columns += [f'{subfield} VenWidth {i}' for i in range(1, lengths.get('VenWidth', 0) + 1)]
            columns += [f'{subfield} Width {i}' for i in range(1, lengths.get('Width', 0) + 1)]
            columns += [f'{subfield} PostLength']
            columns += [f'{subfield} AntLength']
            columns += [f'{subfield} Length']
        else:
            lengths = subfield_lengths.get(subfield, {})
            columns += [f'{subfield} Thickness {i}' for i in range(1, lengths.get('Thickness', 0) + 1)]

    thickness_df = pd.DataFrame(all_thickness, columns=columns)
    thickness_df.to_excel(output_path, index=False)

if __name__ == '__main__':
    output_path = "/Data/ADNI/Hippocampus/test/Measures.xlsx"
    followups_path = '/Data/ADNI/Hippocampus/test/FollowUps'
    point_order_mat = '/home/guolab/HippMetric/point_order_skeleton.mat'

    process_followups(followups_path, output_path, point_order_mat)
