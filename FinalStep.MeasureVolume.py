import os
import nibabel as nib
import pandas as pd

# 数据路径
data_path = "/home/nagao/adni_data/Label"

# 输出表格路径
output_table1 = "/home/nagao/adni_data/Volum_PET_ABETA_CSF_PTAU_MRI.xlsx"
output_table2 = "/home/nagao/adni_data/Volum_AV1451_PET_ABETA_MRI.xlsx"

# 定义 Group 名和输出表格对应的文件夹
groups_table1 = ["PET_ABETA_CSF_PTAU_MRI", "Baseline_PET_ABETA_CSF_PTAU_MRI"]
groups_table2 = ["AV1451_PET_ABETA_MRI", "Baseline_AV1451_PET_ABETA_MRI"]

# 海马亚区名称
subfield_names = [
    "combined_label", "CA1", "CA3", "CA4", "fimbria", "fissure", "GC_DG", 
    "HATA", "mole_layer", "para_sub", "pre_sub", "sub", "tail"
]

# 定义函数：计算每个分割文件的体积
def calculate_volume(nii_file_path):
    """
    计算分割标签的体积
    :param nii_file_path: .nii.gz 文件路径
    :return: 每个亚区的体积字典
    """
    try:
        img = nib.load(nii_file_path)
        data = img.get_fdata()
        voxel_volume = abs(img.header.get_zooms()[0] * img.header.get_zooms()[1] * img.header.get_zooms()[2])
        subfield_volumes = {}
        
        # 提取文件名并将其对应到亚区
        file_name = os.path.basename(nii_file_path)  # 获取文件名
        subfield_name = file_name.split(".")[0]  # 去掉后缀，得到亚区名

        if subfield_name in subfield_names:
            subfield_voxel_count = (data != 0).sum()  # 计算体素数量
            subfield_volumes[subfield_name] = subfield_voxel_count * voxel_volume

        return subfield_volumes
    except Exception as e:
        print(f"错误: 无法处理文件 {nii_file_path}, 错误信息: {e}")
        return {name: None for name in subfield_names}

# 定义函数：遍历并统计体积
def collect_volumes(side_folder, side, groups):
    records = []
    for group in groups:
        group_path = os.path.join(side_folder, group)
        if not os.path.exists(group_path):
            print(f"警告: 文件夹 {group_path} 不存在，跳过")
            continue
        for subject_id in sorted(os.listdir(group_path)):  # 按照字母顺序遍历被试
            subject_path = os.path.join(group_path, subject_id)
            if not os.path.isdir(subject_path):
                continue
            scan_ids = sorted(os.listdir(subject_path))  # 获取扫描ID
            for scan_id in scan_ids:
                scan_path = os.path.join(subject_path, scan_id)
                if not os.path.isdir(scan_path):
                    continue
                # 搜索扫描文件夹中的 .nii.gz 文件
                nii_files = [file for file in os.listdir(scan_path) if file.endswith(".nii.gz")]
                if not nii_files:
                    continue
                # 初始化记录
                record = {
                    "Subject_ID": subject_id,
                    "Scan_ID": scan_id,  # 这里使用扫描文件夹名作为 Scan_ID
                    "Group": group,
                    "Side": side
                }
                # 遍历每个 nii 文件并计算体积
                for file in nii_files:
                    nii_file_path = os.path.join(scan_path, file)
                    # 打印当前处理信息
                    print(f"正在处理文件: 被试 {subject_id}, 组别 {group}, 扫描 ID {scan_id}, 文件名 {file}")
                    subfield_volumes = calculate_volume(nii_file_path)
                    record.update(subfield_volumes)  # 将亚区体积添加到记录中
                
                # 打印当前计算的 record（只打印当前文件的结果）
                print(record)  # 这里会打印当前亚区文件的对应 record
                
                records.append(record)
    return records

# 分别处理左侧和右侧
print("正在处理左侧数据...")
left_folder = os.path.join(data_path, "Left")
left_volumes_table1 = collect_volumes(left_folder, "Left", groups_table1)
left_volumes_table2 = collect_volumes(left_folder, "Left", groups_table2)

print("正在处理右侧数据...")
right_folder = os.path.join(data_path, "Right")
right_volumes_table1 = collect_volumes(right_folder, "Right", groups_table1)
right_volumes_table2 = collect_volumes(right_folder, "Right", groups_table2)

# 合并左右侧数据
print("正在生成表格...")
table1_data = left_volumes_table1 + right_volumes_table1
table2_data = left_volumes_table2 + right_volumes_table2

# 转换为 DataFrame 并导出为 Excel
df_table1 = pd.DataFrame(table1_data)
df_table1.to_excel(output_table1, index=False)
print(f"表格 1 已保存至 {output_table1}")

df_table2 = pd.DataFrame(table2_data)
df_table2.to_excel(output_table2, index=False)
print(f"表格 2 已保存至 {output_table2}")

print("统计完成！")
