import os
import argparse

from helper_files.utils import filename_suffixed, open_spreadsheet, get_label
from helper_files.convert import flatten_tiered_spreadsheet

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-s", "--spreadsheet", type=str, required=True, help="Filename of the tier 1 spreadsheet file.")
    parser.add_argument("-d", "--spreadsheet_dir", type=str, default='.',
                        help="Directory for summary files inside <project_dir>/metadata/<spreadsheet_dir>.")
    return parser

def main(file_name, input_dir):
    label = get_label(file_name)
    print(f"Processing file {file_name}", end=' ')
    file_path = os.path.join(f'{input_dir}/{file_name}')
    df = open_spreadsheet(file_path)
    if 'Tier 1 Dataset Metadata' not in df:
        raise KeyError('Tab name `Tier 1 Dataset Metadata` not found in spreadsheet. Is it Tier 1?')
    if 'Tier 1 Celltype Metadata' in df:
        del df['Tier 1 Celltype Metadata']
    csv = flatten_tiered_spreadsheet(df)
    csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex', 'age_range': 'age'}, axis=1, inplace=True)
    output_filename = filename_suffixed(input_dir, label, 'metadata')
    csv.to_csv(output_filename, index=False)
    print(f"Flat metadata saved as {output_filename}")
    return label

if '__main__' == __name__:
    args = define_parser().parse_args()
    main(args.spreadsheet, args.spreadsheet_dir)
