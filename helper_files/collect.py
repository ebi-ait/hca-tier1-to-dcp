from os.path import isfile, getsize

import requests
import pandas as pd

from helper_files.constants.tier1_mapping import tier1, tier1_list
from helper_files.utils import filename_suffixed, BOLD_START, BOLD_END

CXG_API = 'https://api.cellxgene.cziscience.com/curation/v1'
DEFAULT_CHUNK = 1024 * 1024

def get_collection_data(collection_id):
    """Queries the CELLxGENE API for collection metadata and returns it."""
    headers = {'Content-Type': 'application/json'}
    url = f'{CXG_API}/collections/{collection_id}'
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()

def generate_collection_report(collection):
    """Generates a report from collection metadata."""
    collection_schema = [
        'name', 'collection_url', 'visibility', 'doi',
        'consortia', 'contact_name', 'contact_email', 'protocols', 'doi'
    ]
    coll_report = {}
    for field in collection_schema:
        value = collection.get(field)
        if isinstance(value, list):
            value = ','.join(value)
        coll_report[field] = value
    return coll_report

def selection_of_dataset(collection, dataset_id):
    dataset_df = pd.DataFrame(collection['datasets'])[
        ['dataset_id', 'cell_count', 'title']]

    if dataset_id is not None and dataset_id in dataset_df['dataset_id'].values:
        print(f"Pre-selected dataset: {dataset_df[dataset_df['dataset_id'] == dataset_id]}")
        return dataset_id
    print(f"{BOLD_START}SELECT DATASET:{BOLD_END}")
    print(dataset_df)
    
    if len(dataset_df.index) == 1:
        print("Selected unique dataset in collection.")
        return dataset_df.loc[0, 'dataset_id']
    while True:
        dataset_ix = input("Please select the index of the dataset to be converted:\n")
        if dataset_ix.isdigit() and int(dataset_ix) in dataset_df.index:
            return dataset_df.loc[int(dataset_ix), "dataset_id"]
        print("invalid index")

def download_h5ad_file(h5ad_url, output_file):
    """Downloads the H5AD file if not already present or if size differs."""
    print(f"{BOLD_START}DOWNLOAD ANNDATA:{BOLD_END}")
    with requests.get(h5ad_url, stream=True, timeout=10) as res:
        res.raise_for_status()
        filesize = int(res.headers['Content-Length'])
        if not isfile(output_file):
            with open(output_file, 'wb') as df:
                total_bytes_received = 0
                for chunk in res.iter_content(chunk_size=DEFAULT_CHUNK):
                    df.write(chunk)
                    total_bytes_received += len(chunk)
                    percent_of_total_upload = float('{:.1f}'.format(
                        total_bytes_received / filesize * 100))
                    print(
                        f'\033[1m\033[38;5;10m{percent_of_total_upload}% downloaded {output_file}\033[0m\r', end='')
        elif getsize(output_file) != filesize:
            print("Local " + output_file + " and remote file has different size.")
            print("Please check if the local file is corrupted, rename it, and retry.")
        else:
            print("Local " + output_file + " and remote file, has same size.")


def extract_and_save_metadata(adata, collection_id, dataset_id, label=None, output_dir='metadata'):
    """Extracts and saves metadata from the AnnData object."""
    print(f"{BOLD_START}EXTRACT METADATA:{BOLD_END}")
    tier1_in_object = [key for key in adata.obs.keys() if key in tier1_list]
    
    # Save essential metadata
    if 'library_id' in adata.obs:
        pd.DataFrame(adata.obs[tier1_in_object].drop_duplicates()).set_index('library_id')\
            .to_csv(filename_suffixed(output_dir, f"{collection_id}_{dataset_id}" if not label else label, 'metadata'))
    else:
        print("No library_id information. Saving tier 1 with donor_id index.\n")
        pd.DataFrame(adata.obs[tier1_in_object].drop_duplicates()).set_index('donor_id')\
            .to_csv(filename_suffixed(output_dir, f"{collection_id}_{dataset_id}" if not label else label, 'metadata'))
    # Save full cell observations
    pd.DataFrame(adata.obs).to_csv(filename_suffixed(output_dir, f"{collection_id}_{dataset_id}" if not label else label, 'cell_obs'))

    # Check for missing fields
    missing_must_fields = [must for must in tier1['obs']
                           ['MUST'] if must not in adata.obs.keys()]
    missing_recom_fields = [rec for rec in tier1['obs']
                            ['RECOMMENDED'] if rec not in adata.obs.keys()]

    if missing_must_fields:
        print(f"The following REQUIRED fields are NOT present in the anndata obs: {','.join(missing_must_fields)}")
    if missing_recom_fields:
        print(f"The following OPTIONAL fields are NOT present in the anndata obs: {','.join(missing_recom_fields)}")

def doi_search_ingest(doi, token):
    query = [{
        "field": "content.publications.doi",
        "operator": "IS",
        "value": doi
    }]
    headers = {
        'Content-Type': 'application/json',
        'Authorization': "Bearer " + token
    }
    response = requests.request("POST", 'https://api.ingest.archive.data.humancellatlas.org/projects/query?operator=AND',
                                headers=headers, json=query, timeout=10)
    response.raise_for_status()
    projects = response.json()
    if '_embedded' in projects:
        links = {proj['uuid']['uuid']: {'access': proj['data_use_restriction'] if 'data_use_restriction' in proj else 'NRES', 
                                        'ingest': proj['_links']['self']['href'], 
                                        'DCP': uuid_search_azul(proj['uuid']['uuid'])}
                for proj in projects['_embedded']['projects']}
        links_df = pd.DataFrame(links)
        pd.set_option('display.max_colwidth', None)
        print(f'Project(s) in ingest with doi {doi}:\n{links_df}')
        pd.reset_option('display.max_colwidth')
        ma_uuid = links_df.T[links_df.T['access'] != 'NRES'].index.tolist()
        if any(ma_uuid):
            print(f"{BOLD_START}WARNING:{BOLD_END}\n\tProject(s) {', '.join(ma_uuid)} are managed access.")
    else:
        print(f'DOI: {doi} was not found in ingest')
    return

def uuid_search_azul(uuid):
    azul_api = 'https://service.azul.data.humancellatlas.org/index/projects/'
    response = requests.get(azul_api + uuid)
    if response.ok:
        return 'https://explore.data.humancellatlas/projects/' + uuid
    return response.json()['Message']
