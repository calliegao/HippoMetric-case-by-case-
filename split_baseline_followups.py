import os
import shutil

def copy_files_to_baseline_and_followups(input_folder, baseline_folder, followups_folder, subject_id=None):
    """将每个被试的最小扫描时间点复制到Baseline，其余时间点复制到FollowUps。

    如果传入 subject_id，则只处理该被试；否则处理所有被试。
    """
    os.makedirs(baseline_folder, exist_ok=True)
    os.makedirs(followups_folder, exist_ok=True)

    for side in ['Left', 'Right']:
        side_folder = os.path.join(input_folder, side)
        if not os.path.isdir(side_folder):
            print(f"Side folder not found: {side_folder}")
            continue

        for study_folder in os.listdir(side_folder):
            study_path = os.path.join(side_folder, study_folder)
            if not os.path.isdir(study_path):
                continue

            # 只处理指定subject_id，或者处理所有
            subject_folders = [subject_id] if subject_id else os.listdir(study_path)

            for subject_folder in subject_folders:
                subject_path = os.path.join(study_path, subject_folder)
                if not os.path.isdir(subject_path):
                    print(f"Subject folder not found or not a directory: {subject_path}")
                    continue

                scan_folders = [
                    f for f in os.listdir(subject_path)
                    if os.path.isdir(os.path.join(subject_path, f)) and f.startswith('Scan')
                ]

                scan_folders.sort(key=lambda x: int(x.replace('Scan', '')))

                if not scan_folders:
                    print(f"No scan folders found in {subject_path}. Skipping.")
                    continue

                # baseline
                baseline_subject_path = os.path.join(baseline_folder, side, study_folder, subject_folder)
                os.makedirs(baseline_subject_path, exist_ok=True)
                first_scan_folder = scan_folders[0]
                first_scan_path = os.path.join(subject_path, first_scan_folder)
                shutil.copytree(
                    first_scan_path,
                    os.path.join(baseline_subject_path, first_scan_folder),
                    dirs_exist_ok=True
                )
                print(f"Copied {first_scan_path} to {os.path.join(baseline_subject_path, first_scan_folder)}")

                # followups
                followups_subject_path = os.path.join(followups_folder, side, study_folder, subject_folder)
                os.makedirs(followups_subject_path, exist_ok=True)
                for followup_scan_folder in scan_folders[1:]:
                    followup_scan_path = os.path.join(subject_path, followup_scan_folder)
                    shutil.copytree(
                        followup_scan_path,
                        os.path.join(followups_subject_path, followup_scan_folder),
                        dirs_exist_ok=True
                    )
                    print(f"Copied {followup_scan_path} to {os.path.join(followups_subject_path, followup_scan_folder)}")
