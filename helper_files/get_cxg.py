import re
import argparse
from os.path import isfile, getsize

import requests
import pandas as pd

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

CXG_API = 'https://api.cellxgene.cziscience.com/curation/v1'
DEFAULT_CHUNK = 1024 * 1024
UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

def list_of_strings(arg):
    return arg.split(',')

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-c", "--collection_ids", action="store",
                        dest="collection_ids", type=list_of_strings, required=False,
                        help="List of collection IDs. Use value 'all' or ID(s) separated by comma.")
    parser.add_argument("-d", "--dataset_id", action="store",
                        dest="dataset_id", type=str, required=False,
                        help="Dataset id (uuid) of the file to download")
    return parser

def selection_of_collections(collection_ids):
    valid_input_value(collection_ids)
    if collection_ids == ['all']:
        print("Fetching all CELLxGENE collections...")
        response = requests.get("https://api.cellxgene.cziscience.com/curation/v1/collections", timeout=30)
        collection_ids = []
        for col in response.json():
            collection_ids.append(col['collection_id'])
        print(f"Number of uuids found: {len(collection_ids)}")
        return collection_ids
    return [collection_ids] if isinstance(collection_ids, str) else collection_ids

def user_input_collection():
    collection_ids = input("Please provide the collection IDs to fetch. ('all', <uuid>, <list of uuids> separated by comma):\n")
    collection_ids = collection_ids.strip().split(',')
    collection_ids = [c for c in collection_ids if c != '']
    if not collection_ids:
        raise ValueError("Empty string provided")
    valid_input_value(collection_ids)
    return collection_ids

def valid_input_value(value):
    if not isinstance(value, list):
        raise ValueError()
    if len(value) == 1:
        value_0 = value[0]
        if value_0.lower() in ['all', 'a']:
            return
        if re.search(UUID_REGEX, value_0):
            return
    if all(re.search(UUID_REGEX, v) for v in value):
        return
    raise ValueError(f"collection_ids argument should be 'all', <uuid> or <list of uuids>. {value}")

def get_collection_data(collection_id):
    """Queries the CELLxGENE API for collection metadata and returns it."""
    headers = {'Content-Type': 'application/json'}
    url = f'{CXG_API}/collections/{collection_id}'
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()

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

def get_h5ad_from_collection(collection_id, dataset_id=None):
    collection = get_collection_data(collection_id)
    dataset_id = selection_of_dataset(collection, dataset_id) if not dataset_id else dataset_id
    mx_file = f'h5ads/{collection_id}_{dataset_id}.h5ad'
    h5ad_url = None
    for dataset in collection['datasets']:
        if dataset['dataset_id'] == dataset_id:
            h5ad_url = [asset['url'] for asset in dataset['assets']
                        if asset['filetype'] == 'H5AD'][0]
            break
    if h5ad_url:
        download_h5ad_file(h5ad_url, mx_file)
    else:
        print("H5AD URL not found for the selected dataset.")

def main(collection_ids, dataset_id=None):
    if not collection_ids:
        collection_ids = user_input_collection()
    collection_ids = selection_of_collections(collection_ids)
    for collection_id in collection_ids:
        get_h5ad_from_collection(collection_id, dataset_id)

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(args.collection_ids)