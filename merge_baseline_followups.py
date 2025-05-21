import os
import shutil
from pathlib import Path

def merge_subject_scans(baseline_path, followups_path, subject_id):
    """
    将 baseline_path 中指定 subject 的扫描数据合并到 followups_path 中对应位置。
    支持多个 group、多个 side（左右海马）。

    Parameters:
        baseline_path (str): Baseline 根目录
        followups_path (str): FollowUps 根目录
        subject_id (str): 被试编号（如 002-S-1280）
    """

    sides = ["Left", "Right"]

    baseline_path = Path(baseline_path)
    for side in sides:
        baseline_folder = baseline_path / side
        for group_path in baseline_folder.iterdir():
            group = group_path.name
            baseline_group_path = os.path.join(baseline_path, side, group)
            followups_group_path = os.path.join(followups_path, side, group)

            baseline_subject_path = os.path.join(baseline_group_path, subject_id)
            followups_subject_path = os.path.join(followups_group_path, subject_id)

            # 如果 FollowUps 中存在该被试目录
            if os.path.exists(followups_subject_path):
                # 如果 Baseline 中也有该被试，进行合并
                if os.path.exists(baseline_subject_path):
                    for scan_folder in os.listdir(baseline_subject_path):
                        src_path = os.path.join(baseline_subject_path, scan_folder)
                        dst_path = os.path.join(followups_subject_path, scan_folder)
                        if os.path.isdir(src_path):
                            if not os.path.exists(dst_path):
                                shutil.copytree(src_path, dst_path)
                                print(f"[INFO] 已复制：{src_path} -> {dst_path}")
                            else:
                                print(f"[SKIP] 目标已存在：{dst_path}")
                print(f"[DONE] 被试 {subject_id} 在组 {group}, {side} 合并完成")
            else:
                print(f"[WARN] 跳过：FollowUps 中缺少被试 {subject_id} @ {group}, {side}")

    print(f"[SUCCESS] 所有合并完成 for 被试 {subject_id}")
