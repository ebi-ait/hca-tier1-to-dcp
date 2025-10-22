import os
import re
import argparse
from os.path import isfile, getsize
from pathlib import Path

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
    parser.add_argument("-a", "--auto-download-all", action="store_true",
                        dest="auto_download_all", required=False,
                        help="Automatically download all datasets without user input")
    parser.add_argument("-o", "--output-dir", action="store",
                        dest="output_dir", type=str, default="h5ads", required=False,
                        help="Output directory for downloaded files (default: h5ads)")
    return parser

def ensure_output_dir(output_dir):
    """Create output directory if it doesn't exist."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return output_dir

def selection_of_collections(collection_ids):
    valid_input_value(collection_ids)
    if collection_ids == ['all']:
        print("Fetching all CELLxGENE collections...")
        response = requests.get("https://api.cellxgene.cziscience.com/curation/v1/collections", timeout=30)
        collection_ids = []
        for col in response.json():
            collection_ids.append(col['collection_id'])
        print(f"Number of collection uuids found: {len(collection_ids)}")
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

def selection_of_dataset(collection, auto_download_all=False):
    """Select dataset from collection, with option for auto-downloading all."""
    dataset_df = pd.DataFrame(collection['datasets'])[
        ['dataset_id', 'cell_count', 'title']]

    # Auto-download all datasets if flag is set
    if auto_download_all:
        print(f"{BOLD_START}AUTO-DOWNLOADING ALL {len(dataset_df)} DATASETS:{BOLD_END}")
        return 'all'
    
    print(f"{BOLD_START}SELECT DATASET:{BOLD_END}")
    print(dataset_df)
    
    if len(dataset_df.index) == 1:
        print("Selected unique dataset in collection.")
        return dataset_df.loc[0, 'dataset_id']
    
    while True:
        dataset_ix = input("Please select the index of the dataset to be converted (or download 'all' or 'skip'):\n")
        if dataset_ix.lower() == 'all':
            return 'all'
        if dataset_ix.lower() == 'skip':
            return 'skip'
        if dataset_ix.isdigit() and int(dataset_ix) in dataset_df.index:
            return dataset_df.loc[int(dataset_ix), "dataset_id"]
        print("invalid index")

def download_h5ad_file(h5ad_url, output_file):
    """Downloads the H5AD file if not already present or if size differs."""
    print(f"{BOLD_START}DOWNLOAD ANNDATA:{BOLD_END}")
    
    try:
        with requests.get(h5ad_url, stream=True, timeout=30) as res:
            res.raise_for_status()
            filesize = int(res.headers.get('Content-Length', 0))
            
            # Check if file exists and has correct size
            if isfile(output_file) and getsize(output_file) == filesize:
                print(f"File {output_file} already exists with correct size.")
                return True
            
            # Download file
            with open(output_file, 'wb') as df:
                total_bytes_received = 0
                for chunk in res.iter_content(chunk_size=DEFAULT_CHUNK):
                    if chunk:  # filter out keep-alive chunks
                        df.write(chunk)
                        total_bytes_received += len(chunk)
                        
                        if filesize > 0:
                            percent = (total_bytes_received / filesize) * 100
                            print(
                                f'\033[1m\033[38;5;10m{percent:.1f}% downloaded {output_file}\033[0m\r', 
                                end='', flush=True
                            )
                
                print()  # New line after progress
                return True
                
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        # Remove partially downloaded file
        if isfile(output_file):
            os.remove(output_file)
        return False

def get_h5ad_from_collection(collection_id, output_dir="h5ads", auto_download_all=False):
    """Get H5AD file(s) for a specific collection and dataset(s)."""
    try:
        collection = get_collection_data(collection_id)
        
        if not collection.get('datasets'):
            print(f"No datasets found in collection {collection_id}")
            return 0
        
        selected_dataset = selection_of_dataset(collection, auto_download_all)
        
        downloaded_count = 0
        
        if selected_dataset == 'skip':
            print(f"Skipped all {len(collection['datasets'])} datasets from collection {collection_id}")
            return downloaded_count
        # Download all datasets in the collection
        for i, dataset in enumerate(collection['datasets']):
            dataset_id = dataset['dataset_id']
            if dataset_id not in selected_dataset and selected_dataset != 'all':
                continue
            h5ad_url = None
            for asset in dataset['assets']:
                if asset['filetype'] == 'H5AD':
                    h5ad_url = asset['url']
                    break
            
            if h5ad_url:
                output_file = f'{output_dir}/{collection_id}_{dataset_id}.h5ad'
                print(f"\n{BOLD_START}Downloading dataset: {dataset['title']}{BOLD_END}\t{i+1}/{len(collection['datasets'])}")
                print(f"Dataset ID: {dataset_id}")
                print(f"Cell count: {dataset.get('cell_count', 'N/A')}")
                
                if download_h5ad_file(h5ad_url, output_file):
                    downloaded_count += 1
            else:
                print(f"H5AD URL not found for dataset {dataset_id}")
        
        print(f"Downloaded {downloaded_count}/{len(collection['datasets'])} datasets from collection {collection_id}")
        return downloaded_count
            
    except Exception as e:
        print(f"Error processing collection {collection_id}: {e}")
        return 0

def main(collection_ids, auto_download_all=False, output_dir="h5ads"):
    """Main function to handle the download process."""
    
    # Create output directory
    output_dir = ensure_output_dir(output_dir)
    
    # Get collection IDs
    if not collection_ids:
        collection_ids = user_input_collection()
    
    collection_ids = selection_of_collections(collection_ids)
    
    print(f"Processing {len(collection_ids)} collection(s)...")
    if auto_download_all:
        print(f"{BOLD_START}AUTO-DOWNLOAD MODE: Downloading all datasets from each collection{BOLD_END}")
    
    total_downloaded = 0
    successful_collections = 0
    
    for i, collection_id in enumerate(collection_ids, 1):
        print(f"\n{BOLD_START}Processing collection {i}/{len(collection_ids)}: {collection_id}{BOLD_END}")
        
        try:
            downloaded_count = get_h5ad_from_collection(collection_id, output_dir, auto_download_all)
            total_downloaded += downloaded_count
            if downloaded_count > 0:
                successful_collections += 1
        except Exception as e:
            print(f"Error processing collection {collection_id}: {e}")
            continue
    
    print(f"\n{BOLD_START}Download completed:{BOLD_END}")
    print(f"  - Successfully processed {successful_collections}/{len(collection_ids)} collections")
    print(f"  - Downloaded {total_downloaded} total datasets")
    print(f"  - Files saved to: {output_dir}")

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(args.collection_ids, args.auto_download_all, args.output_dir)