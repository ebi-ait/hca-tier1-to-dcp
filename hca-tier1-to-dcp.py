import os
import argparse
import pandas as pd

import collect_cellxgene_metadata
import collect_spreadsheet_metadata
import convert_to_dcp
import compare_with_dcp
import merge_tier2_metadata
import merge_file_manifest
from helper_files.collect import selection_of_dataset, get_collection_data
from helper_files.utils import filename_suffixed, get_label, BOLD_START, BOLD_END

TEMP_DIR = 'metadata'
os.makedirs(TEMP_DIR, exist_ok=True)


def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-i", "--input_spreadsheet", action="store", default='input_spreadsheet.tsv',
                        dest="input_spreadsheet", type=str, required=False,
                        help="Path of spreadsheet with collection_ids, dataset_ids, wrangled_paths, token, local_template")
    parser.add_argument("-c", "--collection_id", action="store",
                        dest="collection_id", type=str, required=False,
                        help="Collection id (uuid) of the collection to download file from")
    parser.add_argument("-d", "--dataset_id", action="store",
                        dest="dataset_id", type=str, required=False,
                        help="Dataset id (uuid) of the file to download")
    parser.add_argument("-l", "--dataset-label", action="store",
                        dest="label", type=str, required=False,
                        help="Label to use instead of collection/ dataset ids")
    parser.add_argument("-t1", "--tier1_spreadsheet", action="store",
                        dest="tier1_spreadsheet", type=str, required=False,
                        help="Submitted tier 1 spreadsheet file path")
    parser.add_argument("-fm", "--file_manifest", action='store',
                        dest="file_manifest", type=str, required=False,
                        help="File manifest path")
    parser.add_argument("-t2", "--tier2_spreadsheet", action="store",
                        dest="tier2_spreadsheet", type=str, required=False,
                        help="Submitted tier 2 spreadsheet file path")
    parser.add_argument("-w", "--wrangled_spreadsheet", action="store",
                        dest="wrangled_spreadsheet", type=str, required=False,
                        help="Previously wrangled project spreadsheet path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata',
                        help="Directory for the output files")
    parser.add_argument("-t", "--ingest_token", action="store",
                        dest="token", type=str, required=False,
                        help="Ingest token to query for existing projects with same DOI")
    parser.add_argument("-lt", "--local_template", action="store",
                        dest="local_template", type=str, required=False,
                        help="Local path of the HCA spreadsheet template")
    parser.add_argument("-u", "--unequal_comparisson", action="store_false",
                        dest="unequal_comparisson",
                        help="Comparing even if biomaterials are not equal")
    return parser


def read_input_spreadsheet(input_path):
    df = pd.read_csv(input_path, sep='\t')
    columns = ['collection_id', 'dataset_id', 'wrangled_path']
    if not all(col in df.columns for col in columns):
        print(
            f"input tsv file should have the following column names: {'; '.join(columns)}. Found the following: {'; '.join(df.columns)}")
    if 'ingest_token' in df and df['ingest_token'].any():
        # assume all tokens are identical
        df['ingest_token'] = df.loc[df['ingest_token'].notna(), 'ingest_token'][0]
    if 'local_template' in df and df['local_template'].any():
        df['local_template'] = df.loc[df['local_template'].notna(
        ), 'local_template'][0]  # assume all paths are identical
    return df.drop_duplicates()


def run_all_scripts(collection_id, dataset_id, label,
                    tier1_spreadsheet, tier2_spreadsheet,
                    file_manifest, wrangled_spreadsheet,
                    token, local_template, unequal_comparisson, output_dir):

    if collection_id and dataset_id:
        print(f"{BOLD_START}===C: {collection_id} D: {dataset_id}===={BOLD_END}")
        collection = get_collection_data(collection_id)
        dataset_id = selection_of_dataset(collection, dataset_id)
        label = collect_cellxgene_metadata.main(collection_id=collection_id,
                                                dataset_id=dataset_id,
                                                label=label,
                                                output_dir=TEMP_DIR,
                                                token=token)
    elif tier1_spreadsheet:
        label = get_label(tier1_spreadsheet)
        print(f"{BOLD_START}===L: {label}===={BOLD_END}")
        label = collect_spreadsheet_metadata.main(
            tier1_spreadsheet=tier1_spreadsheet,
            output_dir=TEMP_DIR)
    flat_tier1_spreadsheet = filename_suffixed(TEMP_DIR, label, 'metadata')
    convert_to_dcp.main(flat_tier1_spreadsheet,
                        output_dir=TEMP_DIR,
                        local_template=local_template)
    dcp_tier1_spreadsheet = filename_suffixed(
        TEMP_DIR, label, "dcp", ext="xlsx")
    if wrangled_spreadsheet:
        compare_with_dcp.main(tier1_spreadsheet=dcp_tier1_spreadsheet,
                              wrangled_spreadsheet=wrangled_spreadsheet,
                              unequal_comparisson=unequal_comparisson)
    else:
        print(
            f"Previously wrangled file not provided for dataset {label}. Skipping comparisson.")
    if tier2_spreadsheet:
        merge_tier2_metadata.main(tier2_spreadsheet=tier2_spreadsheet,
                                  dt_spreadsheet=dcp_tier1_spreadsheet,
                                  output_dir=output_dir)
    else:
        print(
            f"Tier 2 metadata file not provided for dataset {label}. Skipping Tier 2 merging.")
    if file_manifest:
        merge_file_manifest.main(file_manifest=file_manifest,
                                 dt_spreadsheet=dcp_tier1_spreadsheet,
                                 tier1_spreadsheet=tier1_spreadsheet,
                                 output_dir=output_dir)
    else:
        print(
            f"File manifest not provided for dataset {label}. Skipping file manifest merging.")


def main(input_spreadsheet, collection_id, dataset_id, label,
         tier1_spreadsheet, tier2_spreadsheet, file_manifest, wrangled_spreadsheet,
         local_template, output_dir, token, unequal_comparisson):
    if collection_id or tier1_spreadsheet:
        run_all_scripts(collection_id, dataset_id, label, tier1_spreadsheet,
                        tier2_spreadsheet, file_manifest, wrangled_spreadsheet,
                        token, local_template, unequal_comparisson, output_dir)
        return
    input_df = read_input_spreadsheet(input_spreadsheet)
    for index, row in input_df.iterrows():
        if pd.isnull(row['collection_id']):
            print(f"Collection_id not provided for index {index}")
            continue
        run_all_scripts(row['collection_id'], row['dataset_id'], row['label'],
                        row['tier1_spreadsheet'], row['tier2_spreadsheet'],
                        row['file_manifest'], row['wrangled_spreadsheet'],
                        row['token'], row['local_template'],
                        row['unequal_comparisson'], row['output_dir'])


if __name__ == "__main__":
    args = define_parser().parse_args()
    main(args.input_spreadsheet, args.collection_id, args.dataset_id, args.label,
         args.tier1_spreadsheet, args.tier2_spreadsheet, args.file_manifest,
         args.wrangled_spreadsheet, args.local_template, args.output_dir,
         args.token, args.unequal_comparisson)
