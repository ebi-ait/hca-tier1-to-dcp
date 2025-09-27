import argparse

from helper_files.utils import filename_suffixed, open_spreadsheet, get_label
from helper_files.convert import flatten_tiered_spreadsheet

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("-t1", "--tier1_spreadsheet", action="store",
                        dest="tier1_spreadsheet", type=str, required=True,
                        help="Submitted tier 1 spreadsheet file path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/t1/',
                        help="Directory for the output files")
    return parser

def main(tier1_spreadsheet, output_dir):
    label = get_label(tier1_spreadsheet)
    print(f"Processing file {tier1_spreadsheet}", end=' ')
    tier1_df = open_spreadsheet(tier1_spreadsheet)
    if 'Tier 1 Dataset Metadata' not in tier1_df:
        raise KeyError('Tab name `Tier 1 Dataset Metadata` not found in spreadsheet. Is it Tier 1?')
    if 'Tier 1 Celltype Metadata' in tier1_df:
        del tier1_df['Tier 1 Celltype Metadata']
    csv = flatten_tiered_spreadsheet(tier1_df)
    csv.rename({'assay_ontology_term': 'assay', 'tissue_ontology_term': 'tissue', 'sex_ontology_term': 'sex', 'age_range': 'age'}, axis=1, inplace=True)
    output_filename = filename_suffixed(output_dir, label, 'metadata')
    csv.to_csv(output_filename, index=False)
    print(f"Flat metadata saved as {output_filename}")
    return label

if '__main__' == __name__:
    args = define_parser().parse_args()
    main(args.tier1_spreadsheet, args.output_dir)
