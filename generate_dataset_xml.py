import os
import xml.etree.ElementTree as ET

def change_one_xml(xml_path, xml_dw, update_content):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    element = root.find(xml_dw)
    if element is not None:
        element.text = update_content
        tree.write(xml_path)
    else:
        print(f"Warning: 找不到路径 {xml_dw} in {xml_path}")
        
def update_model_xml(xml_path, new_template_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    filename_element = root.find('.//template/object/filename')
    if filename_element is not None:
        filename_element.text = new_template_path
        tree.write(xml_path)
        print(f"已更新模型文件: {xml_path}")
    else:
        print(f"Warning: 未找到 template 中的 filename 节点 in {xml_path}")

def generate_dataset_xml(work_folder, side, subject_id=None):
    """
    遍历 Baseline 中每个扫描子文件夹，拷贝并修改 data_set.xml。
    如果传入 subject_id，只处理该被试。

    参数:
        work_folder: 主工作路径，如 /home/nagao/test_case
        side: 'Left' 或 'Right'
        subject_id: 可选，指定某个被试ID，默认 None 表示处理所有被试
    """
    baseline_folder = os.path.join(work_folder, "output", "Baseline", side)
    template_file = os.path.join(work_folder, f"data/source_{side}.vtk")
    source_xml = os.path.join(work_folder, "data_set.xml")

    if not os.path.isfile(source_xml):
        raise FileNotFoundError(f"未找到模板 XML 文件: {source_xml}")

    for group_name in os.listdir(baseline_folder):
        group_dir = os.path.join(baseline_folder, group_name)
        if not os.path.isdir(group_dir):
            continue

        # 只处理指定被试或全部
        subject_ids = [subject_id] if subject_id else os.listdir(group_dir)

        for sid in subject_ids:
            subject_dir = os.path.join(group_dir, sid)
            if not os.path.isdir(subject_dir):
                print(f"Subject folder 不存在或不是目录: {subject_dir}")
                continue

            for scan in os.listdir(subject_dir):
                scan_dir = os.path.join(subject_dir, scan)
                if not os.path.isdir(scan_dir):
                    continue

                dest_xml = os.path.join(scan_dir, "data_set.xml")
                os.system(f"cp {source_xml} {dest_xml}")

                # 修改 XML 中的两条路径
                xml_dw_0 = './/subject[@id="sub_test"]/visit[@id="hippo_t0"]/filename[@object_id="hippo"]'
                xml_dw_1 = './/subject[@id="sub_test"]/visit[@id="hippo_t1"]/filename[@object_id="hippo"]'

                update_path_0 = template_file
                update_path_1 = os.path.join(scan_dir, "Remesh_combined_label_transformed.vtk")

                change_one_xml(dest_xml, xml_dw_0, update_path_0)
                change_one_xml(dest_xml, xml_dw_1, update_path_1)

                print(f"处理完成: {dest_xml}")
    
    # 额外更新 model_Left.xml / model_Right.xml 中的路径
    model_path = os.path.join(work_folder, f"model_{side}.xml")
    new_template_path = os.path.join(work_folder, f"data/template_{side}.vtk")
    if os.path.exists(model_path):
        update_model_xml(model_path, new_template_path)
    else:
        print(f"Warning: 模型文件不存在: {model_path}")
