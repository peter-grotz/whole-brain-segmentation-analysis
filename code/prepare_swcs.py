import os
import sys
import shutil

def copy_files_flat(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".swc"):
                if "-CA.swc" in file:
                    continue
                file_fixed = file.replace("_", "-").upper().replace(".SWC", ".swc")
                shutil.copy(os.path.join(root, file), os.path.join(output_dir, file_fixed))

if __name__ == "__main__":
    args = sys.argv
    input_dir = args[1]  
    output_dir = args[2]  
    
    copy_files_flat(input_dir, output_dir)
    print(f"All files copied from {input_dir} to {output_dir}")
