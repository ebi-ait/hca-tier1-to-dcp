import os
import shutil
import pandas as pd
import convert_to_dcp

def to_uuid(filename):
    return '-'.join([filename[0:8], filename[8:12], filename[12:16], filename[16:20], filename[20:32]])

def clean_string(filename):
    return filename.replace("HCA_Tier 1 metadata_ORCF.xlsx","").replace(" ","").replace(".","").replace("_","")

def gen_uuid(filename):
    newf = clean_string(filename)
    newf = ("0" * (32 - len(newf)) + newf) if len(newf) < 32 else newf[:32]
    return to_uuid(newf)

def main(summary_dir: str):
    for file in os.listdir(f'metadata/{summary_dir}'):
        if not file.endswith('_HCA_tier_1_metadata.xlsx') :
            continue
        print(f"Processing file: {file}")
        file_uuid = gen_uuid(file)
        df = pd.read_excel(f'metadata/{summary_dir}/{file}', sheet_name=None)
        df = {sheet: df[sheet][4:] for sheet in df if sheet != 'Tier 1 Celltype Metadata'}
        for dataset_id in df['Tier 1 Dataset Metadata']['dataset_id'].unique():
            dataset_uuid = gen_uuid(dataset_id)
            if os.path.exists(f'metadata/{file_uuid}_{dataset_uuid}_dcp.xlsx'):
                print(f"Skipping existing DCP file for dataset {dataset_id}")
                continue
            print(f"Processing dataset: {dataset_id}")
            dataset_metadata = df['Tier 1 Dataset Metadata'][df['Tier 1 Dataset Metadata']['dataset_id'] == dataset_id]
            donor_metadata = df['Tier 1 Donor Metadata'][df['Tier 1 Donor Metadata']['dataset_id'] == dataset_id]
            sample_metadata = df['Tier 1 Sample Metadata'][df['Tier 1 Sample Metadata']['dataset_id'] == dataset_id].drop(columns=['dataset_id'])
            csv = pd.merge(sample_metadata, donor_metadata, on='donor_id', how='inner').merge(dataset_metadata, on='dataset_id', how='inner')
            csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex'}, axis=1, inplace=True)
            csv.to_csv(f'metadata/{file_uuid}_{dataset_uuid}_metadata.csv', index=False)
            convert_to_dcp.main(collection_id=file_uuid,
                                dataset_id=dataset_uuid)
            if df['Tier 1 Dataset Metadata']['dataset_id'].unique().size == 1:
                shutil.copy(f'metadata/{file_uuid}_{dataset_uuid}_dcp.xlsx', f'metadata/{summary_dir}/{file}_dcp.xlsx')
            else:
                shutil.copy(f'metadata/{file_uuid}_{dataset_uuid}_dcp.xlsx', f'metadata/{summary_dir}/{file}_{dataset_id}_dcp.xlsx')
        

if '__main__' == __name__:
    main('adipose_tier1')