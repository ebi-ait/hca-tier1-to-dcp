import argparse
import pandas as pd

import collect_cellxgene_metadata
import convert_to_dcp
import compare_with_dcp

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--input_spreadsheet_path", "-i", action="store",
                        dest="input_spreadsheet_path", type=str, required=True, 
                        help="Path of spreadsheet with collection_ids, dataset_ids, wrangled_paths, token, local_template")
    return parser

def read_input_spreadsheet(input_path):
    df = pd.read_csv(input_path, sep='\t')
    columns = ['collection_id', 'dataset_id', 'wrangled_path']
    if not all([col in columns for col in df.columns]):
        print(f"input tsv file should have the following column names: {'; '.join(columns)}. Found the following: {'; '.join(df.columns)}")
    if 'ingest_token' in df and df['ingest_token'].any():
        df['ingest_token'] = df.loc[df['ingest_token'].notna(), 'ingest_token'][0] # assume all tokens are identical
    if 'local_template' in df and df['local_template'].any():
        df['local_template'] = df.loc[df['local_template'].notna(), 'local_template'][0] # assume all paths are identical
    return df.drop_duplicates()

def main(input_spreadsheet_path):
    input_spreadsheet = read_input_spreadsheet(input_spreadsheet_path)
    for index, row in input_spreadsheet.iterrows():
        if pd.isnull(row['collection_id']):
            print(f"Collection_id not provided for index {index}")
            continue
        collect_cellxgene_metadata.main(collection_id=row['collection_id'],
                                        dataset_id=row['dataset_id'],
                                        token=None)
        convert_to_dcp.main(collection_id=row['collection_id'],
                            dataset_id=row['dataset_id'],
                            local_template=None)
        if pd.isnull(row['wrangled_path']):
            print(f"DCP Spreadsheet path not provided for collection {row['collection_id']}. Skipping comparisson.")
            continue
        compare_with_dcp.main(collection_id=row['collection_id'],
                              dataset_id=row['dataset_id'],
                              wrangled_path=row['wrangled_path'])
        
BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

if __name__ == "__main__":
    args = define_parser().parse_args()
    main(args.input_spreadsheet_path)