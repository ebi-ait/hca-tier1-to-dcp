import os
import re
import shutil
import argparse
import requests
import pandas as pd
from hca_ingest.api.ingestapi import IngestApi
from hca_ingest.downloader.workbook import WorkbookDownloader

import compare_with_dcp
import convert_to_dcp

INGEST_API_URL = "https://api.ingest.archive.data.humancellatlas.org/"
PROJ_UUID = {"Hinte (2024) Nature": "8913bc18-966d-4507-9259-1a7c9f6bef1c","AlZaim (2024) bioRxiv": "f67ed416-874e-411d-b34e-aff672377cf2","Emont (2022) Nature": "fc2a0b4e-1e4a-447b-a097-47b398402f37","Wang (2024) Cell Metabolism": "cb95ee6e-4041-4dd9-9666-62e14709e04b","Strieder-Barboza (2022) bioRxiv": "3294cc9d-07ce-4a18-8e5f-a8afac5c882e","Massier (2023) Nature Communications": "57916660-af5a-44d5-a7a9-2e84b65f8a68","Sun (2020) Nature": "86cff72e-1ec9-416f-bd1b-f245a116d0b2","Reinisch (2025) Cell Metabolism": "241aa8c9-188c-4f21-acf7-b76de2956149"}

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--overwrite", "-o", action="store_true",
                        dest="overwrite", help="Overwrite existing files")
    parser.add_argument("-t", "--token", type=str, help="Bearer token for HCA ingest API.")
    return parser

def to_uuid(filename):
    return '-'.join([filename[0:8], filename[8:12], filename[12:16], filename[16:20], filename[20:32]])

def clean_string(filename):
    return filename.replace("HCA_tier_1_metadata","").replace(".xlsx","").replace(" ","").replace(".","").replace("_","")

def gen_uuid(filename):
    newf = clean_string(filename)
    newf = ("0" * (32 - len(newf)) + newf) if len(newf) < 32 else newf[:32]
    return to_uuid(newf)

def get_valid_api(token:str=None):
    api = IngestApi(INGEST_API_URL)
    api.set_token(f"Bearer {token}")
    response = requests.get(f"{INGEST_API_URL}/submissionEnvelopes/", headers=api.get_headers(), timeout=5)
    while response.status_code != 200:
        print("Invalid token.")
        token = input("Please provide a valid token:").strip()
        api.set_token(f"Bearer {token}")
        response = requests.get(f"{INGEST_API_URL}/submissionEnvelopes/", headers=api.get_headers(), timeout=5)
    return api

def get_submission_uuid(api: IngestApi, project_uuid: str):
    project = api.get(f"{INGEST_API_URL}/projects/search/findByUuid?uuid=" + project_uuid).json()
    submissions = api.get(project['_links']['submissionEnvelopes']['href']).json()
    if submissions['page']['totalElements'] == 0:
        print(f"No submission found for project {project_uuid}.")
        return None
    if submissions['page']['totalElements'] > 1:
        print(f"Multiple submissions found for project {project_uuid}. Selected first one.")
        print([submission['uuid']['uuid'] for submission in submissions['_embedded']['submissionEnvelopes']])
        return submissions['_embedded']['submissionEnvelopes'][0]['uuid']['uuid']
    return submissions['_embedded']['submissionEnvelopes'][0]['uuid']['uuid']

def get_spreadsheet_uuids(proj_uuid):
    spread_uuid = {}
    for key in proj_uuid.keys():
        title = re.search('[\\w-]+ \\(\\d+\\)', key)
        new_title = title.group(0).replace(' ','').replace('(', '_').replace(')','_') + 'HCA_tier_1_metadata.xlsx'
        spread_uuid[new_title] = proj_uuid[key]
    return spread_uuid

def get_workbook(api: IngestApi, subm_uuid: str):
    print("Downloading workbook...", flush=True, end=' ')
    wd = WorkbookDownloader(api)
    print("done!", flush=True)
    return wd.get_workbook_from_submission(subm_uuid)

def main(summary_dir: str):
    args = define_parser().parse_args()
    api = get_valid_api(args.token)
    spread_uuid = get_spreadsheet_uuids(PROJ_UUID)
    for file in os.listdir(f'metadata/{summary_dir}'):
        if not '_HCA_tier_1_metadata' in file or 'dcp.xlsx' in file or not file.endswith('.xlsx'):
            continue
        print(f"Processing file: {file}")
        file_uuid = gen_uuid(file)
        df = pd.read_excel(f'metadata/{summary_dir}/{file}', sheet_name=None)
        df = {sheet: df[sheet][4:] for sheet in df if sheet != 'Tier 1 Celltype Metadata'}
        if os.path.exists(f'metadata/{file_uuid}_{file_uuid}_dcp.xlsx') and not args.overwrite:
            print(f"Skipping existing DCP file for dataset {file_uuid}.")
            continue
        dataset_metadata = df['Tier 1 Dataset Metadata']
        donor_metadata = df['Tier 1 Donor Metadata'].drop(columns=['dataset_id'])
        sample_metadata = df['Tier 1 Sample Metadata']
        csv = pd.merge(sample_metadata, donor_metadata, on='donor_id', how='inner').merge(dataset_metadata, on='dataset_id', how='inner')
        csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex'}, axis=1, inplace=True)
        csv.to_csv(f'metadata/{file_uuid}_{file_uuid}_metadata.csv', index=False)
        convert_to_dcp.main(collection_id=file_uuid,
                            dataset_id=file_uuid)
        shutil.copy(f'metadata/{file_uuid}_{file_uuid}_dcp.xlsx', f'metadata/{summary_dir}/{file.replace(".xlsx","_dcp.xlsx")}')
        if file not in spread_uuid:
            print(f"Skipping file {file} that's not in ingest.")
            continue
        print(f"Getting DCP metadata for file {file}", flush=True)
        subm_uuid = get_submission_uuid(api, project_uuid=spread_uuid[file])
        if not subm_uuid:
            print(f"Skipping file {file} due to missing submission UUID.")
            continue
        print(f"Done! Submission is {subm_uuid}. Downloading spreadsheet...", flush=True,  end=' ')
        wb = get_workbook(api, subm_uuid=subm_uuid)
        wrangled_path = f'metadata/{summary_dir}/{file}_ingest.xlsx'
        wb.save(wrangled_path)
        compare_with_dcp.main(collection_id=file_uuid,
                              dataset_id=file_uuid,
                              wrangled_path=wrangled_path,
                              unequal_comparisson=True)


if '__main__' == __name__:
    main('adipose_tier1')