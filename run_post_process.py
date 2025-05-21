# run_post_process.py
import subprocess
import logging

# 配置日志
logging.basicConfig(
    filename='subject_post_process_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

def run_post_process_for_subject(subject_id: str, group_name: str, baseline_path: str, followup_path: str, subfield_file_path: str):
    """
    对指定被试和组别运行 post-process（左右侧分别调用 process_subject.py）
    """
    sides = ["Left", "Right"]
    for side in sides:
        try:
            logging.info(f"Starting post-process for subject: {subject_id}, side: {side}, group: {group_name}")
            
            command = [
                "python", "process_subject.py",
                subject_id,
                side,
                group_name,
                "--baseline_path", baseline_path,
                "--followup_path", followup_path,
                "--subfield_file", subfield_file_path
            ]

            subprocess.run(command, check=True)
            
            logging.info(f"Finished post-process for subject: {subject_id}, side: {side}, group: {group_name}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error for subject: {subject_id}, side: {side}, group: {group_name}")
            logging.error(f"Command: {e.cmd}")
            logging.error(f"Exit status: {e.returncode}")
