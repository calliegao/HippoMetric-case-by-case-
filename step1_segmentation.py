# step1_segmentHA.py
import os
import glob
import subprocess

def process_scan(subject_folder, scan_folder, base_dir):
    """
    Process a single scan folder using the segmentHA_T1.sh script.
    """
    try:
        full_subject_path = os.path.join(base_dir, subject_folder)
        os.environ["SUBJECTS_DIR"] = full_subject_path
        full_scan_path = os.path.join(full_subject_path, scan_folder)

        # Remove potential lock file
        lock_file = os.path.join(full_scan_path, "scripts", "IsRunningHPsubT1.lh+rh")
        if os.path.isfile(lock_file):
            print(f"Lock file found for {full_scan_path}. Removing lock file.")
            os.remove(lock_file)

        # Execute FreeSurfer segmentation
        command = ["segmentHA_T1.sh", scan_folder]
        print(f"Processing: {scan_folder} in {subject_folder}")
        subprocess.run(command, check=True, cwd=full_subject_path)
    except subprocess.CalledProcessError as e:
        print(f"Error processing {scan_folder}: {e}")

def process_subject_scans(base_dir, subject_id):
    """
    Process all scan folders for a specific subject in a base directory.
    """
    subject_path = os.path.join(base_dir, subject_id)
    scan_folders = glob.glob(os.path.join(subject_path, "Scan*"))
    for scan_path in scan_folders:
        scan_name = os.path.basename(scan_path)
        process_scan(subject_id, scan_name, base_dir)
