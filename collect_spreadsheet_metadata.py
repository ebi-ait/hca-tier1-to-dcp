import os
import re
import shutil
import argparse
import pandas as pd
from pathlib import Path

from helper_files.file_io import filename_suffixed, open_spreadsheet

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-s", "--spreadsheet", type=str, required=True, help="Filename of the tier 1 spreadsheet file.")
    parser.add_argument("-d", "--spreadsheet_dir", type=str, default='.',
                        help="Directory for summary files inside <project_dir>/metadata/<spreadsheet_dir>.")
    return parser

def get_label(filename: str) -> str:
    label = Path(filename).stem  # strip extension

    # Remove case-insensitive 'HCA Tier 1 metadata' or variants
    label = re.sub(r'hca[_\s-]*tier[_\s-]*1[_\s-]*metadata', '', label, flags=re.I)

    # Remove 'metadata' if followed by date or nothing
    label = re.sub(r'[_\s-]*metadata([_\s-]*\d{1,2}[_\s-]*\d{1,2}[_\s-]*\d{2,4})?$', '', label, flags=re.I)

    # Collapse multiple underscores or dashes
    label = re.sub(r'[_\s-]+', '_', label)

    # Strip leading/trailing underscores
    return label.strip('_')

def flatten_tier1(df):
    if 'Tier 1 Dataset Metadata' not in df:
        raise KeyError('Tab name `Tier 1 Dataset Metadata` not found in spreadsheet. Is it Tier 1?')
    dataset_metadata = df['Tier 1 Dataset Metadata']
    donor_metadata = df['Tier 1 Donor Metadata']
    sample_metadata = df['Tier 1 Sample Metadata']
    if 'dataset_id' in sample_metadata:
        donor_metadata = donor_metadata.drop(columns=['dataset_id'])
    return pd.merge(sample_metadata, donor_metadata, on='donor_id', how='inner').merge(dataset_metadata, on='dataset_id', how='inner')

def main(file_name, input_dir):
    label = get_label(file_name)
    print(f"Processing file {file_name}", end=' ')
    file_path = os.path.join(f'{input_dir}/{file_name}')
    df = open_spreadsheet(file_path)
    if 'Tier 1 Celltype Metadata' in df:
        del df['Tier 1 Celltype Metadata']
    csv = flatten_tier1(df)
    csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex', 'age_range': 'age'}, axis=1, inplace=True)
    output_filename = filename_suffixed(None, None, 'metadata', label, input_dir)
    csv.to_csv(output_filename, index=False)
    print(f"Flat metadata saved as {output_filename}")
    return label

if '__main__' == __name__:
    args = define_parser().parse_args()
    main(args.spreadsheet, args.spreadsheet_dir)