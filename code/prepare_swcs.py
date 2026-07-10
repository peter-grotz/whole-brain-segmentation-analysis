import os
import sys
import shutil

# neuron_tracing_utils.analysis.get_error_intensities.group_swcs splits the SWC
# filename on "-" and reads parts[0..3] = (neuron, sample, tracer, compartment),
# i.e. it REQUIRES 4 hyphen-separated fields (e.g. N001-794495-JT-AXON). Some GT
# sets (e.g. the refined final-voxel reconstructions) name files with only 3
# fields (N001-794495-JT), which makes parts[3] raise IndexError. Append this
# compartment token to any 3-field name so the flattened names match the expected
# 4-field form. (Purely a naming fix to satisfy the downstream parser; the token
# does not change the traced data.)
COMPARTMENT = "AXON"

def copy_files_flat(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".swc"):
                if "-CA.swc" in file:
                    continue
                file_fixed = file.replace("_", "-").upper().replace(".SWC", ".swc")
                stem = file_fixed[:-len(".swc")]
                if stem.count("-") < 3:  # fewer than 4 hyphen fields -> add compartment
                    file_fixed = f"{stem}-{COMPARTMENT}.swc"
                shutil.copy(os.path.join(root, file), os.path.join(output_dir, file_fixed))

if __name__ == "__main__":
    args = sys.argv
    input_dir = args[1]  
    output_dir = args[2]  
    
    copy_files_flat(input_dir, output_dir)
    print(f"All files copied from {input_dir} to {output_dir}")
