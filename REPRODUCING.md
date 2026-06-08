This [Code Ocean](https://codeocean.com) Compute Capsule will allow you to run and reproduce the results of [Whole-brain segmentation analysis](https://codeocean.allenneuraldynamics.org/capsule/9176479/tree) on your local machine<sup>1</sup>. Follow the instructions below, or consult [our knowledge base](https://docs.codeocean.com/user-guide/compute-capsule-basics/managing-capsules/exporting-capsules-to-your-local-machine) for more information. Don't hesitate to reach out to [Support](mailto:support@codeocean.com) if you have any questions.

<sup>1</sup> You may need access to additional hardware and/or software licenses.

# Prerequisites

- [Docker Community Edition (CE)](https://www.docker.com/community-edition)

# Instructions

## Download attached Data Assets

In order to fetch the Data Asset(s) this Capsule depends on, download them into the Capsule's `data` folder:
* [706301-merge-GT](https://codeocean.allenneuraldynamics.org/data-assets/fe4d746d-618d-425b-937a-418ae0de7e3e) should be downloaded to `data/706301-merge-GT`
* [LC_685221_refined](https://codeocean.allenneuraldynamics.org/data-assets/13ebf515-0256-4e17-ae0b-cf621fc14bdf) should be downloaded to `data/LC_685221_refined`
* [719654_complete_reconstructions_refined](https://codeocean.allenneuraldynamics.org/data-assets/ebbd899c-7690-4aae-bda6-5b43d6d1a66e) should be downloaded to `data/719654_complete_reconstructions_refined`
* [708369_voxel](https://codeocean.allenneuraldynamics.org/data-assets/12802eb7-6a01-496e-8767-5b2c3370cba1) should be downloaded to `data/708369_refined_09_25_24`
* [719654_voxel](https://codeocean.allenneuraldynamics.org/data-assets/01dd1738-6d4b-4de3-8fd8-82a7a4f051ec) should be downloaded to `data/719654_voxel`
* [730902_SNT_12_3_24](https://codeocean.allenneuraldynamics.org/data-assets/eb9df310-02d7-4b43-a954-7b330ac9d42d) should be downloaded to `data/730902_SNT_12_3_24`
* [719654_proj_refined](https://codeocean.allenneuraldynamics.org/data-assets/79382e4c-fc91-4999-a4d9-a652539cb6d2) should be downloaded to `data/719654_proj_refined`
* [685221_refined_voxel_2_11_2025](https://codeocean.allenneuraldynamics.org/data-assets/a54d8ee0-3ff4-4658-afd8-198458cca9d4) should be downloaded to `data/685221_refined_voxel_2_11_2025`
* [685221_refined_voxel_merged](https://codeocean.allenneuraldynamics.org/data-assets/f36bafc1-1a35-49cc-89e7-8dae728c3d03) should be downloaded to `data/685221_refined_voxel_merged`
* [751473_refined_voxel](https://codeocean.allenneuraldynamics.org/data-assets/0166d1b8-1f65-4de3-9d80-f1c8a2caf275) should be downloaded to `data/751473_refined_voxel`
* [754610_refined_voxel](https://codeocean.allenneuraldynamics.org/data-assets/52cc71cb-c639-4db1-b0c2-a9bba236e5ea) should be downloaded to `data/754610_refined_voxel`
* [754613_voxel_refined](https://codeocean.allenneuraldynamics.org/data-assets/32e7beb1-d456-489d-af76-b126e9e2e98f) should be downloaded to `data/754613_voxel_refined`
* [719654_refined_voxel_5_14_2025](https://codeocean.allenneuraldynamics.org/data-assets/e29ea1ca-bf9d-44f9-bf57-150bac97c985) should be downloaded to `data/719654_refined_voxel_5_14_2025`
* [730223_voxel_7_14_25](https://codeocean.allenneuraldynamics.org/data-assets/a6b352d0-8945-4a86-bd6c-dacdbb6829f5) should be downloaded to `data/730223_voxel_7_14_25`
* [754611_voxel_7_14_25](https://codeocean.allenneuraldynamics.org/data-assets/d1eee069-6b84-4d32-971d-94fa54dec3e9) should be downloaded to `data/754611_voxel_7_14_25`
* [754613_voxel_7_14_25](https://codeocean.allenneuraldynamics.org/data-assets/9e01a729-dbb9-4650-bc52-a190902c9adb) should be downloaded to `data/754613_voxel_7_14_25`
* [754612_voxel_7_14_25](https://codeocean.allenneuraldynamics.org/data-assets/84d0b6a1-5bea-49c6-8d74-6d619648a746) should be downloaded to `data/754612_voxel_7_14_25`
* [703070_voxel_7_14_25](https://codeocean.allenneuraldynamics.org/data-assets/5c511a69-9bb5-416f-9d4a-d6b0123a45dd) should be downloaded to `data/703070_voxel_7_14_25`
* [709221_refined](https://codeocean.allenneuraldynamics.org/data-assets/97e8aa86-8cfb-427d-abde-59cf52d911b1) should be downloaded to `data/709221_refined`
* [709221_refined](https://codeocean.allenneuraldynamics.org/data-assets/011d411c-58f8-44ac-99a3-689e4cbcc4e9) should be downloaded to `data/709221_refined_1`
* [709221_swcs_updated_cleaned](https://codeocean.allenneuraldynamics.org/data-assets/786ef159-ee43-47d5-b43f-6f3c617f3b2e) should be downloaded to `data/709221_swcs_updated_cleaned`
* [709221_voxel](https://codeocean.allenneuraldynamics.org/data-assets/aea052dc-dcde-402c-9d1b-eb5647026ba9) should be downloaded to `data/709221_voxel`
* [784896_voxel_10_07_25](https://codeocean.allenneuraldynamics.org/data-assets/f894d84a-e012-43c4-a54e-efa7885acd45) should be downloaded to `data/784896_voxel_10_07_25`
* [794493_refined](https://codeocean.allenneuraldynamics.org/data-assets/4663e277-d2b2-4247-8110-fb76fc648b9d) should be downloaded to `data/794493_refined`
* [794491_refined](https://codeocean.allenneuraldynamics.org/data-assets/6055f087-b28a-4340-95a5-c027c3a84d1f) should be downloaded to `data/794491_refined`
* [794491_refined_r2](https://codeocean.allenneuraldynamics.org/data-assets/66820449-21ac-4a70-b34b-6acf0a080e09) should be downloaded to `data/794493_refined_r2`
* [794491_refined_r2](https://codeocean.allenneuraldynamics.org/data-assets/82b4bdf4-47b3-4d20-9b1a-b238af35f68a) should be downloaded to `data/794491_refined_r2`
* [802449_refined_reconstructions](https://codeocean.allenneuraldynamics.org/data-assets/9900008b-43e7-4fb9-a969-8280fd5ded4b) should be downloaded to `data/802449_refined_reconstructions`
* [gcs_cred_1_15_2025](https://codeocean.allenneuraldynamics.org/data-assets/1d652ba9-fdb3-4172-b15d-0a405928c396) should be downloaded to `data/gcs_cred_1_15_2025`
* [exaSPIM_794492_for_GAS_analysis_refined_preliminary](https://codeocean.allenneuraldynamics.org/data-assets/81cd7308-b527-4a13-b17a-e8347b0daab6) should be downloaded to `data/exaSPIM_794492_for_GAS_analysis_refined_preliminary`
* [exaSPIM_802449_refined](https://codeocean.allenneuraldynamics.org/data-assets/4c0b7819-ddee-49d7-b329-226053e7ddcd) should be downloaded to `data/exaSPIM_802449_refined`
* [exaSPIM_794495_refined_preliminary](https://codeocean.allenneuraldynamics.org/data-assets/208ddec9-e0e7-4e34-b52c-c45f9506ccdc) should be downloaded to `data/exaSPIM_794495_refined_preliminary`
* [exaSPIM_794495_GAS_preliminary_voxel](https://codeocean.allenneuraldynamics.org/data-assets/9cfdd69d-6e6d-42c3-922e-94503415fcc5) should be downloaded to `data/exaSPIM_794495_GAS_preliminary_voxel`
* [exaSPIM_794492_GAS_preliminary_voxel](https://codeocean.allenneuraldynamics.org/data-assets/6a71e06d-5cb5-4cf1-a19a-5ee6c7e658f5) should be downloaded to `data/exaSPIM_794492_GAS_preliminary_voxel`
* [exaSPIM_802449_name_corrected](https://codeocean.allenneuraldynamics.org/data-assets/5f375884-3fc5-4ac8-a35c-7e2d8d9add0f) should be downloaded to `data/exaSPIM_802449_name_corrected`
* [exaSPIM_802449_full_set](https://codeocean.allenneuraldynamics.org/data-assets/2bb2cba9-b0d2-4b9a-8b40-d6d3a7a53891) should be downloaded to `data/exaSPIM_802449_full_set`
* [802449_refined_reconstructions_r2](https://codeocean.allenneuraldynamics.org/data-assets/97cfaf6c-ba0b-4419-89e7-e71d577c89a9) should be downloaded to `data/802449_refined_reconstructions_r2`
* [reconstructions_802449_reformatted_refined](https://codeocean.allenneuraldynamics.org/data-assets/99a828de-35c1-4ca5-9542-ce731ef50550) should be downloaded to `data/reconstructions_802449_reformatted_refined`
* [reconstructions_802449_reformatted_refined_all](https://codeocean.allenneuraldynamics.org/data-assets/dc4d9f6d-02d2-4c14-8023-acafcf260a2e) should be downloaded to `data/reconstructions_802449_reformatted_refined_all`
* [reconstructions_802449_reformatted_refined_all_voxel](https://codeocean.allenneuraldynamics.org/data-assets/28a564a5-d57e-443d-8ad1-2410b33621d7) should be downloaded to `data/reconstructions_802449_reformatted_refined_all_voxel`
* [795495_refined_voxel](https://codeocean.allenneuraldynamics.org/data-assets/87299122-1036-47f9-adfc-1cb4adaafec9) should be downloaded to `data/795495_refined_voxel`
* [794495_refined_voxel_fixed](https://codeocean.allenneuraldynamics.org/data-assets/014d3e7d-8532-4d48-8cb8-b9dcf37b77ac) should be downloaded to `data/794495_refined_voxel_fixed`
* [exaspim_794495_reconstructions_refined_2026_03_12](https://codeocean.allenneuraldynamics.org/data-assets/378766e3-5ae6-4f66-a383-ffc2aa5cdb80) should be downloaded to `data/exaspim_794495_reconstructions_refined_2026_03_12`
* [794495_voxel_fixed_2026_03_16](https://codeocean.allenneuraldynamics.org/data-assets/e31421dc-ef55-4a8e-9f56-4ef2cfbd3a67) should be downloaded to `data/794495_voxel_fixed_2026_03_16`
* [exaSPIM_789202_reconstructions_refined_2026_04_8](https://codeocean.allenneuraldynamics.org/data-assets/4d888f6e-ade2-4388-817a-1df90c588bf2) should be downloaded to `data/exaSPIM_789202_reconstructions_refined_2026_04_8`
* [789202_refined_voxel_fixed_2026_04_08](https://codeocean.allenneuraldynamics.org/data-assets/9d80e092-70b1-41ea-a53b-747a55178a4a) should be downloaded to `data/789202_refined_voxel_fixed_2026_04_08`

## Log in to the Docker registry

In your terminal, execute the following command, providing your password or API key when prompted for it:
```shell
docker login -u peter.grotz@alleninstitute.org registry.codeocean.allenneuraldynamics.org
```

## Run the Capsule to reproduce the results

In your terminal, navigate to the folder where you've extracted the Capsule and execute the following command, adjusting parameters as needed:
```shell
docker run --platform linux/amd64 --rm \
  --workdir /code \
  --volume "$PWD/code":/code \
  --volume "$PWD/data":/data \
  --volume "$PWD/results":/results \
  registry.codeocean.allenneuraldynamics.org/capsule/8dd5b576-36bd-4c09-8bc2-e97ead617265 \
  bash run '' '' '' 0.748,0.748,1.0 '' 0
```
