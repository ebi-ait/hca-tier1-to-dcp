import argparse
import os
import sys

import pandas as pd

# Open cellxgene spreadsheet
# Open DCP spreadsheet
    # provide file locally
    # if DOI, if unique ingest project/ submission, pull with api
# Compare number of tabs, use union
# Open each common tab 
    # compare number of entites per tab
    # compare ids per tab, for union
        # search for Tier 1 ID in DCP name, description, accession
    # compare values of common IDs

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--collection", "-c", action="store",
                        dest="collection_id", type=str, required=True, help="Collection ID")
    parser.add_argument("--dataset", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    parser.add_argument("--pre-wrangled-path", "-w", action="store", 
                        dest="wrangled_path", type=str, required=False, help="Path of previously wrangled project spreadsheet")
    parser.add_argument("--ingest-token", '-t', action="store",
                        dest='token', type=str, required=False,
                        help="Ingest token to query for existing projects with same DOI")
    return parser

def main():
    args = define_parser().parse_args()
    collection_id = args.collection_id

    # Open cellxgene spreadsheet
    if args.dataset_id is not None:
        dataset_id = args.dataset_id
    else:
        dataset_ids = {file.split("_")[1] for file in os.listdir('metadata') if file.startswith(collection_id)}
        if len(dataset_ids) == 1:
            dataset_id = list(dataset_ids)[0]
        else:
            print("Please specify the dataset_id. There are available files for:")
            print('\n'.join(dataset_ids))
            sys.exit()
            
    try:
        tier1_spreadsheet_path = f"metadata/{collection_id}_{dataset_id}_dcp.xlsx"
        tier1_spreadsheet = pd.read_excel(tier1_spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"File not found: {tier1_spreadsheet_path}")
        sys.exit()

    # Open DCP spreadsheet
    # TODO add more options
    wranged_spreadsheet_path = args.wrangled_path
    try:
        wranged_spreadsheet = pd.read_excel(wranged_spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"File not found: {wranged_spreadsheet_path}")

    # Compare number of tabs, use union
    if len(tier1_spreadsheet) == len(wranged_spreadsheet):
        print("All good on number of tabs side.")
    elif len(tier1_spreadsheet) > len(wranged_spreadsheet):
        print("More tabs in Tier 1.")
    else:
        print("More tabs in DCP.")

if __name__ == "__main__":
    main()
