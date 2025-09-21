import argparse
import os

import pandas as pd
import anndata

from helper_files.collect import (
    get_collection_data,
    generate_collection_report,
    selection_of_dataset,
    download_h5ad_file,
    extract_and_save_metadata,
    doi_search_ingest
)
from helper_files.utils import filename_suffixed

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-c", "--collection_id", action="store",
                        dest="collection_id", type=str, required=True,
                        help="Collection id (uuid) of the collection to download file from")
    parser.add_argument("-d", "--dataset_id", action="store",
                        dest="dataset_id", type=str, required=False,
                        help="Dataset id (uuid) of the file to download")
    parser.add_argument("-l", "--dataset-label", action="store",
                        dest="label", type=str, required=False,
                        help="Label to use instead of collection/ dataset ids")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata',
                        help="Directory for the output files")
    parser.add_argument("-t", "--ingest_token", action="store",
                        dest='token', type=str, required=False,
                        help="Ingest token to query for existing projects with same DOI")
    return parser

def main(collection_id, dataset_id=None, label=None, output_dir="metadata", token=None):

    # Query collection data
    collection = get_collection_data(collection_id)
    collection['protocols'] = [link['link_url']
                               for link in collection['links'] if link['link_type'] == 'PROTOCOL']

    # Generate and save collection report
    coll_report = generate_collection_report(collection)
    
    dataset_id = selection_of_dataset(collection, dataset_id) if not dataset_id else dataset_id
    os.makedirs(output_dir, exist_ok=True)
    pd.DataFrame(coll_report, index=[0]).transpose()\
        .rename({'name': 'title', 'contact_name': 'study_pi'})\
        .to_csv(filename_suffixed(output_dir, f"{collection_id}_{dataset_id}" if not label else label, 'study_metadata'), header=None)
        
    # Download the H5AD file
    mx_file = f'h5ads/{collection_id}_{dataset_id}.h5ad'
    os.makedirs('h5ads', exist_ok=True)

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

    # Extract metadata from the AnnData file
    adata = anndata.read_h5ad(mx_file, backed='r')
    extract_and_save_metadata(adata, collection_id, dataset_id, label, output_dir)

    print(f"{BOLD_START}ADDITIONAL INFO:{BOLD_END}")
    # Check if doi exists in ingest
    if token is not None:
        doi_search_ingest(coll_report['doi'], token)

    if 'sequencing_platform' not in adata.obs:
        if 'doi' in coll_report:
            print(f"No sequencer info. See doi.org/{coll_report['doi']} for more.")
        else:
            print(f"No sequencer info. See {collection['collection_url']} for more.")

    print(f'Output {filename_suffixed(output_dir, f"{collection_id}_{dataset_id}" if not label else label, suffix=None,ext=None)}')

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(collection_id=args.collection_id, dataset_id=args.dataset_id, label=args.label, output_dir=args.output_dir, token=args.token)
