import re
import shutil
import argparse
import pandas as pd

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-s", "--spreadsheet", type=str, required=True, help="Filename of the tier 1 spreadsheet file.")
    parser.add_argument("-d", "--spreadsheet_dir", type=str, default='.',
                        help="Directory for summary files inside <project_dir>/metadata/<spreadsheet_dir>.")
    return parser

def to_uuid(filename):
    return '-'.join([filename[0:8], filename[8:12], filename[12:16], filename[16:20], filename[20:32]])

def clean_string(filename):
    return filename.replace("HCA_tier_1_metadata","").replace(".xlsx","").replace(" ","").replace(".","").replace("_","")

def gen_uuid(filename):
    newf = clean_string(filename)
    newf = ("0" * (32 - len(newf)) + newf) if len(newf) < 32 else newf[:32]
    return to_uuid(newf)

def get_spreadsheet_uuids(proj_uuid):
    spread_uuid = {}
    for key in proj_uuid.keys():
        title = re.search('[\\w-]+ \\(\\d+\\)', key)
        new_title = title.group(0).replace(' ','').replace('(', '_').replace(')','_') + 'HCA_tier_1_metadata.xlsx'
        spread_uuid[new_title] = proj_uuid[key]
    return spread_uuid

def main():
    args = define_parser().parse_args()
    file = args.spreadsheet
    s_dir = args.spreadsheet_dir
    print(f"Processing file {file}", end=' ', flush=True)
    file_uuid = gen_uuid(file)
    print(f"as {file_uuid}")
    df = pd.read_excel(f'metadata/{s_dir}/{file}', sheet_name=None)
    df = {sheet: df[sheet][4:] for sheet in df if sheet != 'Tier 1 Celltype Metadata'}
    dataset_metadata = df['Tier 1 Dataset Metadata']
    donor_metadata = df['Tier 1 Donor Metadata'].drop(columns=['dataset_id'])
    sample_metadata = df['Tier 1 Sample Metadata']
    csv = pd.merge(sample_metadata, donor_metadata, on='donor_id', how='inner').merge(dataset_metadata, on='dataset_id', how='inner')
    csv = csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex', 'age_range': 'age'}, axis=1)
    csv = csv.dropna(axis=1, how='all')
    csv.to_csv(f'metadata/{file_uuid}_{file_uuid}_metadata.csv', index=False)
    print(f"Flat metadata saved as metadata/{file_uuid}_{file_uuid}_metadata.csv.")
    print(f"Collection: {file_uuid}\nDataset: {file_uuid}")
    return file_uuid

if '__main__' == __name__:
    main()