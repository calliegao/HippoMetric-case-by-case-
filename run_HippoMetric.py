import os
from pathlib import Path
from step1_segmentHA import process_subject_scans
from hippo2surflabel import run_subject_processing
from surf_remesh import remesh_subject_stl
from registration_module import process_subject
from split_baseline_followups import copy_files_to_baseline_and_followups
from generate_dataset_xml import generate_dataset_xml
from transform_single_subject import run_regression
from SeperateSpokes import extract_spokes
from run_post_process import run_post_process_for_subject
from merge_baseline_followups import merge_subject_scans


def run_pipeline(
    base_dir, subject_id, group_name,
    run_step1=True,
    run_step2=True,
    run_step3=True,
    run_step4=True,
    run_step5=True,
    run_step6=True,
    run_step7=True,
    run_step8=True,
    run_step9=True,
    run_step10=True
):
    """
    Run the full processing pipeline for a single subject.

    Parameters:
        base_dir (str): 原始数据所在的目录（如 Baseline_AV1451_PET_ABETA_MRI）
        subject_id (str): 被试文件夹名，如 '002-S-1280'
        group_name (str): 分组名，如 'PET_ABETA_CSF_PTAU_MRI'
        run_stepX (bool): 控制是否执行第X步
    """

    base_dir = Path(base_dir)
    subject_folder = base_dir / subject_id

    sides = ["Left", "Right"]

    # Step 1
    if run_step1:
        print("==> 第一步：segmentHA")
        process_subject_scans(str(subject_folder), subject_id)
    else:
        print("跳过第一步：segmentHA")

    # Step 2
    if run_step2:
        print("==> 第二步：Label2Mesh")
        label_dir = work_dir / "output" / "Label"
        surf_dir = work_dir / "output" / "Surf"
        run_subject_processing(
            subject_dir=str(subject_folder),
            group_name=group_name,
            label_output_dir=str(label_dir),
            surf_output_dir=str(surf_dir)
        )
    else:
        print("跳过第二步：Label2Mesh")

    # Step 3
    if run_step3:
        print("==> 第三步：Surf网格简化")
        refined_surf_dir = work_dir / "output" / "RefinedSurf"
        surf_dir = work_dir / "output" / "Surf"
        for side in sides:
            input_side_dir = surf_dir / side / group_name / subject_id
            output_side_dir = refined_surf_dir / side / group_name / subject_id

            if not input_side_dir.exists():
                print(f"Warning: 输入目录不存在：{input_side_dir}")
                continue

            for scan_folder in input_side_dir.iterdir():
                if scan_folder.is_dir():
                    input_stl_dir = scan_folder
                    output_stl_dir = output_side_dir / scan_folder.name
                    os.makedirs(output_stl_dir, exist_ok=True)
                    remesh_subject_stl(input_stl_dir, output_stl_dir)
    else:
        print("跳过第三步：Surf网格简化")

    # Step 4
    if run_step4:
        print("==> 第四步：刚性配准")
        reged_refined_dir = work_dir / "output" / "RegedRefinedSurf"
        refined_surf_dir = work_dir / "output" / "RefinedSurf"
        template_files = {
            "Left": work_dir / "template" / "left_hippo.vtk",
            "Right": work_dir / "template" / "right_hippo.vtk",
        }

        for side in sides:
            input_reg_side_dir = refined_surf_dir / side / group_name / subject_id
            output_reg_side_dir = reged_refined_dir

            if not input_reg_side_dir.exists():
                print(f"Warning: 输入目录不存在：{input_reg_side_dir}")
                continue

            process_subject(
                subject_folder=str(input_reg_side_dir),
                template_file=str(template_files[side]),
                output_folder=str(output_reg_side_dir),
                side=side,
                study=group_name
            )
    else:
        print("跳过第四步：刚性配准")

    # Step 5
    if run_step5:
        print("==> 第五步：拆分 Baseline 和 FollowUps")
        reged_refined_dir = work_dir / "output" / "RegedRefinedSurf"
        baseline_dir = work_dir / "output" / "Baseline"
        followups_dir = work_dir / "output" / "FollowUps"
        copy_files_to_baseline_and_followups(
            input_folder=str(reged_refined_dir),
            baseline_folder=str(baseline_dir),
            followups_folder=str(followups_dir),
            subject_id=subject_id
        )
    else:
        print("跳过第五步：拆分 Baseline 和 FollowUps")

    # Step 6
    if run_step6:
        print("==> 第六步：生成和更新 data_set.xml")
        for side in sides:
            generate_dataset_xml(str(work_dir), side, subject_id=subject_id)
    else:
        print("跳过第六步：生成和更新 data_set.xml")

    # Step 7
    if run_step7:
        print("==> 第七步：运行 deformetrica regression")
        model_xml_path = work_dir / f"model_{{side}}.xml"
        opt_param_path = work_dir / "optimization_parameters.xml"
        for side in sides:
            print(f"[INFO] 正在处理 {side} 側")
            baseline_folder = work_dir / "output" / "Baseline" / side
            for group in baseline_folder.iterdir():
                subject_dir = group / subject_id
                if not subject_dir.exists():
                    continue
                for scan in subject_dir.iterdir():
                    if not scan.is_dir():
                        continue
                    print(f"[INFO] 正在变换配准: {scan}")
                    run_regression(
                        case_dir=str(scan),
                        model_xml_path=str(model_xml_path).format(side=side),
                        opt_param_xml_path=str(opt_param_path),
                        cache_dir=str(scan)
                    )
    else:
        print("跳过第七步：deformetrica regression")
    
    # Step 8
    print("==> 第八步：提取 spokes 点并保存为 vtk")
    subfield_list_path = work_dir / "subfield_list_00.xlsx"
    for side in sides:
        print(f"[INFO] 正在处理 {side} 側")
        baseline_folder = work_dir / "output" / "Baseline" / side
        for group in baseline_folder.iterdir():
            subject_dir = group / subject_id
            if not subject_dir.exists():
                continue
            for scan in subject_dir.iterdir():
                if not scan.is_dir():
                    continue
                print(f"[INFO] 正在提取 spokes 点: {scan}")
                extract_spokes(str(scan), subfield_list_path)
    
    # Step 9
    if run_step9:
        print("==> 第九步：运行后处理脚本（process_subject.py）, Refine spokes")
        baseline_path = work_dir / "output" / "Baseline"
        followup_path = work_dir / "output" / "FollowUps"
        subfield_file_path = work_dir / "subfield_list_python.xlsx"
        run_post_process_for_subject(subject_id, group_name, baseline_path, followup_path, subfield_file_path)
        
    # Step 10
    if run_step10:
        print("==> 第十步：合并 Baseline 和 FollowUps 中的扫描")
        baseline_path = str(work_dir / "output" / "Baseline")
        followups_path = str(work_dir / "output" / "FollowUps")
        merge_subject_scans(baseline_path, followups_path, subject_id)
    else:
        print("跳过第十步：合并扫描")    


if __name__ == "__main__":
    work_dir = Path("/home/nagao/test_case")
    base_dir = "/home/nagao/test_case/adni/group1"
    subject_id = "002_S_0413"
    group_name = "group1"

    run_pipeline(
        base_dir,
        subject_id,
        group_name,
        run_step1=False,
        run_step2=False,
        run_step3=False,
        run_step4=False,
        run_step5=False,
        run_step6=False,
        run_step7=False,
        run_step8=False,
        run_step9=False,
        run_step10=True
    )
