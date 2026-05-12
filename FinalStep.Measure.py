import os
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import vtk
from vtk.util import numpy_support
import scipy.io

# Read point data from a VTK file
def read_vtk_points(vtk_file):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(vtk_file)
    reader.Update()
    polydata = reader.GetOutput()
    points = polydata.GetPoints()
    points_np = numpy_support.vtk_to_numpy(points.GetData())
    
    # Handle NaN values
    points_np = np.nan_to_num(points_np)

    return points_np

# Compute subfield thickness
def compute_thickness(pt_points, ps_points):
    return cdist(pt_points, ps_points, 'euclidean')

def compute_width(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    Compute the width of a subfield.
    
    Parameters:
    - SkelPt: Skeleton point data, typically read from `{subfield}_ps_refined.vtk`.
    - skeletonPt_order: Order of skeleton points, usually generated from `point_order` data.
    - crest_spoke_length: Length of crest spokes, calculated from BdryPt and SkelPt.

    Returns:
    - width1: First width value, combined from skeleton points.
    - width2: Second width value, combined from skeleton points.
    """
    width1 = np.zeros(31)  # Compute length for each cross-section
    width2 = np.zeros(31)  # Compute length for each cross-section

    for width_n in range(31):  # range(31) corresponds to MATLAB 1:31
        sum_segment1 = 0
        # MATLAB sn = 1:9, Python range(9)
        for sn in range(9):  # Compute first cross-section width
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment1 += each_segment

        sum_segment2 = 0
        # MATLAB sn = 9:16, Python range(8,16)
        for sn in range(8, 16):  # Compute second cross-section width
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment2 += each_segment

        # Add crest point spoke length, exclude spokes 1 and 33
        crest1 = crest_spoke_length[width_n]  # MATLAB width_n+1 -> Python width_n
        crest2 = crest_spoke_length[63 - width_n]  # MATLAB 65-width_n -> Python 64-width_n
        width1[width_n] = sum_segment2 + crest1
        width2[width_n] = sum_segment2 + crest2

    return width1, width2

def compute_length(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    Compute the length of a subfield.
    
    Parameters:
    - SkelPt: Skeleton point data, typically read from `{subfield}_ps_refined.vtk`.
    - skeletonPt_order: Order of skeleton points, usually generated from `point_order` data.
    - crest_spoke_length: Length of crest spokes, calculated from BdryPt and SkelPt.

    Returns:
    - Sub_length1: First length value, combined from skeleton points.
    - Sub_length2: Second length value, combined from skeleton points.
    """
    sum_segment3 = 0
    # MATLAB sn = 1:16, Python sn = 0:15
    for sn in range(16):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment3 += each_segment2

    sum_segment4 = 0
    # MATLAB sn = 16:30, Python sn = 15:30
    for sn in range(15, 30):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment4 += each_segment2

    # Compute length1 and length2
    Sub_length1 = sum_segment3 + crest_spoke_length[0]  # MATLAB crest_spoke_length(1) -> Python crest_spoke_length[0]
    Sub_length2 = sum_segment4 + crest_spoke_length[32]  # MATLAB crest_spoke_length(33) -> Python crest_spoke_length[32]

    return Sub_length1, Sub_length2
    
def load_point_order(mat_file_path):
    """
    Load .mat file and return 'point_order' data
    """
    mat_data = scipy.io.loadmat(mat_file_path)
    
    # Uncomment to check keys in the .mat file if needed
    # print("Keys in the loaded .mat file:", mat_data.keys())
    
    return mat_data['point_order']

# Compute subfield measurements (thickness, width, length)
def compute_subfield_measures(scan_folder_path, subfield, point_order_mat):
    """
    Compute subfield measures including thickness, width, and length
    """
    # Load point_order data
    point_order = load_point_order(point_order_mat)
    
    # Construct VTK file paths
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    # Read points from scan files (SkelPt and BdryPt)
    SkelPt = read_vtk_points(ps_file)  # Read SkelPt from ps_refined.vtk
    BdryPt = read_vtk_points(pt_file)  # Read BdryPt from pt_refined.vtk
    
    # Compute refined_spokes and crest_spoke_length
    refined_spokes = BdryPt - SkelPt
    crest_spoke_length = np.linalg.norm(refined_spokes[1098:1162], axis=1)
    
    # Compute skeletonPt_order
    skeletonPt_order = np.zeros((17, 31), dtype=int)
    skeletonPt_order[8:17, :] = point_order[:, 1:32]
    for k in range(31):
        skeletonPt_order[0:8, k] = point_order[1:9, 64-k]
    
    # Compute width
    width1, width2 = compute_width(SkelPt, skeletonPt_order, crest_spoke_length)
    
    # Compute length
    Sub_length1, Sub_length2 = compute_length(SkelPt, skeletonPt_order, crest_spoke_length)
    
    # Total width and length
    total_width = width1 + width2
    total_length = Sub_length1 + Sub_length2
    
    # Compute thickness
    thickness = compute_thickness(BdryPt, SkelPt)
    thickness_bilateral = np.diagonal(thickness)  # Extract diagonal as subfield thickness
    inf_thickness = thickness_bilateral[:len(thickness_bilateral)//2]  # Inferior thickness
    sup_thickness = thickness_bilateral[len(thickness_bilateral)//2:]  # Superior thickness
    
    return inf_thickness, sup_thickness, width1, width2, total_width, Sub_length1, Sub_length2, total_length

def compute_subfield_thickness(scan_folder_path, subfield):
    
    # Construct VTK file paths
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    if os.path.exists(pt_file) and os.path.exists(ps_file):  # Ensure files exist
        # Read VTK point data
        pt_points = read_vtk_points(pt_file)
        ps_points = read_vtk_points(ps_file)
        
        # Compute subfield thickness
        thickness = compute_thickness(pt_points, ps_points)
        thickness_bilateral = np.diagonal(thickness)  # Extract diagonal as subfield thickness
        
        # Merge superior and inferior thickness
        mid_index = len(thickness_bilateral) // 2
        subfield_thickness = thickness_bilateral[:mid_index] + thickness_bilateral[mid_index:]
        
        return subfield_thickness
    else:
        print(f"Error: VTK files for subfield {subfield} not found!")
        return None

# Main function
def process_followups(followups_path, output_path, point_order_mat):
    # Read subfield_list_00.xlsx to get subfield names and number of points
    subfield_df = pd.read_excel('/home/nagao/subfield_list_00.xlsx', header=None)
    subfield_list = subfield_df.iloc[:, 0].tolist()  # Subfield names
    print(f"All Subfields: {subfield_list}")

    N_vector = subfield_df.iloc[:, 3].values  # Number of points

    all_thickness = []  # Store all thickness data
    subfield_lengths = {}  # Store lengths of measurements for each subfield

    # Iterate through each side and group
    for side in ['Left', 'Right']:
        for group in ["AV1451_PET_ABETA_MRI","Baseline_AV1451_PET_ABETA_MRI"]:
            group_path = os.path.join(followups_path, side, group)

            # Iterate through each subject folder
            for subject in os.listdir(group_path):
                subject_path = os.path.join(group_path, subject)

                if os.path.isdir(subject_path):
                    # Get all scan folders starting with 'Scan'
                    scan_folders = [scan_folder for scan_folder in os.listdir(subject_path) if scan_folder.startswith('Scan')]

                    # Sort scan folders by number in folder name (ScanXX)
                    scan_folders = sorted(scan_folders, key=lambda x: int(x[4:]))

                    processed_scans = set()  # Track processed scans
                    for scan_folder in scan_folders:
                        if scan_folder in processed_scans:
                            continue

                        scan_folder_path = os.path.join(subject_path, scan_folder)
                        if os.path.exists(scan_folder_path) and os.path.isdir(scan_folder_path):
                            processed_scans.add(scan_folder)

                            scan_measures = [subject, scan_folder, side, group]  # Initialize scan data with Side and Group

                            # Iterate through subfields and compute measurements
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

    # Add 'Side' and 'Group' to column headers
    columns = ["Subject ID", "Scan ID", "Side", "Group"]

    # Construct headers for each subfield
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

    # Convert to DataFrame
    thickness_df = pd.DataFrame(all_thickness, columns=columns)

    # Save to Excel
    thickness_df.to_excel(output_path, index=False) 

if __name__ == '__main__':

    output_path = "/home/nagao/adni_data/Measures2_AV1451_PET_ABETA_MRI.xlsx"
    followups_path = '/home/nagao/adni_data/FollowUps2'
    point_order_mat = '/home/nagao/point_order_skeleton.mat'

    process_followups(followups_path, output_path, point_order_mat)
