import os
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import vtk
from vtk.util import numpy_support
import scipy.io

# 读取vtk文件中的点数据
def read_vtk_points(vtk_file):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(vtk_file)
    reader.Update()
    polydata = reader.GetOutput()
    points = polydata.GetPoints()
    points_np = numpy_support.vtk_to_numpy(points.GetData())
    
    # 处理nan值
    points_np = np.nan_to_num(points_np)

    return points_np

# 计算亚区厚度
def compute_thickness(pt_points, ps_points):
    return cdist(pt_points, ps_points, 'euclidean')

def compute_width(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    计算亚区的宽度。
    
    参数：
    - SkelPt: 骨架点数据，通常从 `{subfield}_ps_refined.vtk` 文件中读取。
    - skeletonPt_order: 骨架点的顺序，通常由 `point_order` 数据生成。
    - crest_spoke_length: 脊点的长度，计算时从 BdryPt 和 SkelPt 得到。

    返回：
    - width1: 第一个宽度值，结合了骨架点的计算。
    - width2: 第二个宽度值，结合了骨架点的计算。
    """
    width1 = np.zeros(31)  # 计算每一条横轴的长度
    width2 = np.zeros(31)  # 计算每一条横轴的长度

    for width_n in range(31):  # Python 中的 range(31) 对应 MATLAB 中的 1:31
        sum_segment1 = 0
        # MATLAB 中的 sn = 1:9，Python 中的 range(9)
        for sn in range(9):  # 计算第一个横轴的宽度
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment1 += each_segment

        sum_segment2 = 0
        # MATLAB 中的 sn = 9:16，Python 中的 range(8, 16)
        for sn in range(8, 16):  # 计算第二个横轴的宽度
            each_segment = np.linalg.norm(SkelPt[skeletonPt_order[sn, width_n], :] - SkelPt[skeletonPt_order[sn+1, width_n], :])
            sum_segment2 += each_segment

        # 宽度还要再加上 crest point 对应的 spoke 长度，spoke 编号是 1:64，应该去掉 1 和 33
        crest1 = crest_spoke_length[width_n]  # MATLAB 中的 width_n+1 对应 Python 中的 width_n
        crest2 = crest_spoke_length[63 - width_n]  # MATLAB 中的 65 - width_n 对应 Python 中的 64 - width_n
        width1[width_n] = sum_segment2 + crest1
        width2[width_n] = sum_segment2 + crest2

    return width1, width2

def compute_length(SkelPt, skeletonPt_order, crest_spoke_length):
    """
    计算亚区的长度。
    
    参数：
    - SkelPt: 骨架点数据，通常从 `{subfield}_ps_refined.vtk` 文件中读取。
    - skeletonPt_order: 骨架点的顺序，通常由 `point_order` 数据生成。
    - crest_spoke_length: 脊点的长度，计算时从 BdryPt 和 SkelPt 得到。

    返回：
    - Sub_length1: 第一个长度值，结合了骨架点的计算。
    - Sub_length2: 第二个长度值，结合了骨架点的计算。
    """
    sum_segment3 = 0
    # MATLAB 中 sn = 1:16，Python 中 sn = 0:15
    for sn in range(16):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment3 += each_segment2

    sum_segment4 = 0
    # MATLAB 中 sn = 16:30，Python 中 sn = 15:30
    for sn in range(15, 30):
        each_segment2 = np.linalg.norm(SkelPt[skeletonPt_order[8, sn], :] - SkelPt[skeletonPt_order[8, sn+1], :])
        sum_segment4 += each_segment2

    # 计算长度1和长度2
    Sub_length1 = sum_segment3 + crest_spoke_length[0]  # MATLAB 中的 crest_spoke_length(1)，Python 中为 crest_spoke_length[0]
    Sub_length2 = sum_segment4 + crest_spoke_length[32]  # MATLAB 中的 crest_spoke_length(33)，Python 中为 crest_spoke_length[32]

    return Sub_length1, Sub_length2
    
def load_point_order(mat_file_path):
    """
    读取 .mat 文件并返回 'point_order' 数据
    """
    # 使用 scipy.io.loadmat 读取 .mat 文件
    mat_data = scipy.io.loadmat(mat_file_path)
    
    # 输出所有键值，查看文件中包含的变量名（可以根据需要删除）
    # print("Keys in the loaded .mat file:", mat_data.keys())
    
    # 获取 'point_order' 数据并返回
    return mat_data['point_order']

# 计算亚区的测量指标（厚度、宽度、长度）
def compute_subfield_measures(scan_folder_path, subfield, point_order_mat):
    """
    计算亚区的测量值，包括厚度、宽度、长度等
    """
    # 加载point_order数据
    point_order = load_point_order(point_order_mat)
    
    # 构建vtk文件路径
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    # 读取扫描文件中的点（SkelPt和BdryPt）
    SkelPt = read_vtk_points(ps_file)  # 从ps_refine.vtk文件读取SkelPt
    BdryPt = read_vtk_points(pt_file)  # 从pt_refine.vtk文件读取BdryPt
    print(f"SkelPt shape: {SkelPt.shape}")
    print(f"BdryPt shape: {BdryPt.shape}")
    
    # 计算refined_spokes和crest_spoke_length
    refined_spokes = BdryPt - SkelPt
    crest_spoke_length = np.linalg.norm(refined_spokes[1098:1162], axis=1)
    
    # 计算skeletonPt_order
    skeletonPt_order = np.zeros((17, 31), dtype=int)
    skeletonPt_order[8:17, :] = point_order[:, 1:32]
    for k in range(31):
        skeletonPt_order[0:8, k] = point_order[1:9, 64-k]
    
    # 计算宽度
    width1, width2 = compute_width(SkelPt, skeletonPt_order, crest_spoke_length)
    
    # 计算长度
    Sub_length1, Sub_length2 = compute_length(SkelPt, skeletonPt_order, crest_spoke_length)
    
    # 总宽度和长度
    total_width = width1 + width2
    total_length = Sub_length1 + Sub_length2
    
    # 计算厚度（使用compute_subfield_thickness）
    thickness = compute_thickness(BdryPt, SkelPt)
    print(f"thickness shape: {thickness.shape}")  # 打印thickness的形状
    thickness_bilateral = np.diagonal(thickness)  # 提取对角线，表示亚区厚度
    print(f"thickness_bilateral shape: {thickness_bilateral.shape}")
    inf_thickness = thickness_bilateral[:len(thickness_bilateral)//2]  # 上厚度
    sup_thickness = thickness_bilateral[len(thickness_bilateral)//2:]  # 下厚度
    
    return inf_thickness, sup_thickness, width1, width2, total_width, Sub_length1, Sub_length2, total_length

def compute_subfield_thickness(scan_folder_path, subfield):
    
    # 构建vtk文件路径
    pt_file = os.path.join(scan_folder_path, f'{subfield}_pt_refined.vtk')
    ps_file = os.path.join(scan_folder_path, f'{subfield}_ps_refined.vtk')
    
    if os.path.exists(pt_file) and os.path.exists(ps_file):  # 确保文件存在
        # 读取vtk文件数据
        pt_points = read_vtk_points(pt_file)
        ps_points = read_vtk_points(ps_file)
        
        # 计算亚区厚度
        thickness = compute_thickness(pt_points, ps_points)
        thickness_bilateral = np.diagonal(thickness)  # 提取对角线，表示亚区厚度
        
        # 上下厚度合并
        mid_index = len(thickness_bilateral) // 2
        subfield_thickness = thickness_bilateral[:mid_index] + thickness_bilateral[mid_index:]
        
        return subfield_thickness
    else:
        print(f"Error: VTK files for subfield {subfield} not found!")
        return None

# 主函数
def process_followups(followups_path, output_path, point_order_mat):
    # 读取subfield_list_00.xlsx，获取亚区名称和点数
    subfield_df = pd.read_excel('/home/nagao/subfield_list_00.xlsx', header=None)
    subfield_list = subfield_df.iloc[:, 0].tolist()  # 亚区名称
    print(f"All Subfields: {subfield_list}")

    N_vector = subfield_df.iloc[:, 3].values  # 点数

    all_thickness = []  # 用于存储所有的厚度数据
    subfield_lengths = {}  # 用于记录每个亚区的长度

    # 遍历每个侧面和组别
    for side in ['Left', 'Right']:
        for group in ["AV1451_PET_ABETA_MRI","Baseline_AV1451_PET_ABETA_MRI"]:  # "PET_ABETA_CSF_PTAU_MRI",
            group_path = os.path.join(followups_path, side, group)

            # 获取每个被试文件夹
            for subject in os.listdir(group_path):
                subject_path = os.path.join(group_path, subject)

                if os.path.isdir(subject_path):  # 如果是文件夹
                    # 获取所有以 'Scan' 开头的扫描文件夹
                    scan_folders = [scan_folder for scan_folder in os.listdir(subject_path) if scan_folder.startswith('Scan')]

                    # 按扫描文件夹中的数字部分（XX）进行排序
                    scan_folders = sorted(scan_folders, key=lambda x: int(x[4:]))  # 提取 "ScanXX" 中的数字部分并排序

                    # 遍历每个扫描文件夹
                    processed_scans = set()  # 用于记录已处理过的扫描文件夹
                    for scan_folder in scan_folders:
                        if scan_folder in processed_scans:  # 跳过已处理的扫描文件夹
                            continue

                        scan_folder_path = os.path.join(subject_path, scan_folder)
                        if os.path.exists(scan_folder_path) and os.path.isdir(scan_folder_path):  # 如果是扫描文件夹
                            processed_scans.add(scan_folder)  # 记录该扫描文件夹为已处理

                            scan_measures = [subject, scan_folder, side, group]  # 添加Side和Group列，初始化扫描数据，包含被试、扫描ID、Side和Group

                            # 遍历亚区并计算测量指标
                            for i, subfield in enumerate(subfield_list):
                                # 获取每个亚区的点数
                                N_points = N_vector[i]

                                # 计算测量指标
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

                                    # 记录每种测量值的长度
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

                                    # 记录亚区厚度长度
                                    subfield_lengths[subfield] = {'Thickness': len(subfield_thickness)}

                            all_thickness.append(scan_measures)
                            print(f"已完成Side {side}, 分组 {group},被试 {subject}, 扫描 {scan_folder}")

    # 在列头中添加 'Side' 和 'Group'
    columns = ["Subject ID", "Scan ID", "Side", "Group"]

    # 遍历每个亚区并构建表头
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

    # 转换为 DataFrame
    thickness_df = pd.DataFrame(all_thickness, columns=columns)

    # 保存到Excel文件
    thickness_df.to_excel(output_path, index=False) 

if __name__ == '__main__':

    output_path = "/home/nagao/adni_data/Measures2_AV1451_PET_ABETA_MRI.xlsx"
    followups_path = '/home/nagao/adni_data/FollowUps2'
    point_order_mat = '/home/nagao/point_order_skeleton.mat'

    process_followups(followups_path, output_path, point_order_mat)
