import argparse
import pandas as pd

from collect_cellxgene_metadata import selection_of_dataset, get_collection_data
import collect_cellxgene_metadata
import convert_to_dcp
import compare_with_dcp

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--input_spreadsheet_path", "-i", action="store", default='input_spreadsheet.tsv',
                        dest="input_spreadsheet_path", type=str, required=False,
                        help="Path of spreadsheet with collection_ids, dataset_ids, wrangled_paths, token, local_template")
    parser.add_argument("--collection_id", "-c", action="store",
                        dest="collection_id", type=str, required=False, help="Collection id")
    parser.add_argument("--dataset_id", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    parser.add_argument("--ingest_token", '-t', action="store",
                        dest='token', type=str, required=False,
                        help="Ingest token to query for existing projects with same DOI")
    parser.add_argument("--local_template", "-l", action="store",
                        dest="local_template", type=str, required=False, help="Local path of the HCA template")
    parser.add_argument("--wrangled_path", "-w", action="store", 
                        dest="wrangled_path", type=str, required=False, help="Path of previously wrangled project spreadsheet")
    return parser

def read_input_spreadsheet(input_path):
    df = pd.read_csv(input_path, sep='\t')
    columns = ['collection_id', 'dataset_id', 'wrangled_path']
    if not all(col in df.columns for col in columns):
        print(f"input tsv file should have the following column names: {'; '.join(columns)}. Found the following: {'; '.join(df.columns)}")
    if 'ingest_token' in df and df['ingest_token'].any():
        df['ingest_token'] = df.loc[df['ingest_token'].notna(), 'ingest_token'][0] # assume all tokens are identical
    if 'local_template' in df and df['local_template'].any():
        df['local_template'] = df.loc[df['local_template'].notna(), 'local_template'][0] # assume all paths are identical
    return df.drop_duplicates()

def run_three_scripts(collection_id, dataset_id, wrangled_path, token, local_template):
    print(f"{BOLD_START}===C: {collection_id} D: {dataset_id}===={BOLD_END}")
    collection = get_collection_data(collection_id)
    dataset_id = selection_of_dataset(collection, dataset_id)
    collect_cellxgene_metadata.main(collection_id=collection_id,
                                    dataset_id=dataset_id,
                                    token=token)
    convert_to_dcp.main(collection_id=collection_id,
                        dataset_id=dataset_id,
                        local_template=local_template)
    if not wrangled_path:
        print(f"DCP Spreadsheet path not provided for collection {collection_id}. Skipping comparisson.")
        return
    compare_with_dcp.main(collection_id=collection_id,
                            dataset_id=dataset_id,
                            wrangled_path=wrangled_path,
                            unequal_comparisson=True)


def main(input_spreadsheet_path='input_spreadsheet.tsv', collection_id=None, 
         dataset_id=None, wrangled_path=None, ingest_token=None, local_template=None):
    if collection_id:
        run_three_scripts(collection_id, dataset_id, wrangled_path, ingest_token, local_template)
        return
    input_spreadsheet = read_input_spreadsheet(input_spreadsheet_path)
    for index, row in input_spreadsheet.iterrows():
        if pd.isnull(row['collection_id']):
            print(f"Collection_id not provided for index {index}")
            continue
        run_three_scripts(row['collection_id'], row['dataset_id'], row['wrangled_path'], 
                          row['ingest_token'], row['local_template'])


BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(args.input_spreadsheet_path, args.collection_id, args.dataset_id, 
         args.wrangled_path, args.token, args.local_template)
