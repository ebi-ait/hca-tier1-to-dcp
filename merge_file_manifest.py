import os
import re
import argparse
from collections import defaultdict

import pandas as pd

from helper_files.file_mapping import FILE_MANIFEST_MAPPING, TIER_1_MAPPING, FASTQ_STANDARD_FIELDS


def define_parse():
    parser = argparse.ArgumentParser(
        description="Merge Tier 2 metadata into DCP format."
    )
    parser.add_argument(
        "--file_manifest",
        "-f",
        type=str,
        required=True,
        help="Path to the File manifest excel file.",
    )
    parser.add_argument(
        "--wrangled_spreadsheet",
        "-w",
        type=str,
        required=True,
        help="Path to the wrangled spreadsheet excel file.",
    )
    parser.add_argument(
        "--tier1_spreadsheet",
        "-t1",
        type=str,
        required=True,
        help="Path to the Tier 1 metadata excel file."
    )
    parser.add_argument(
        "--output_path",
        "-o",
        type=str,
        default="metadata",
        help="Path to save the merged output excel file.",
    )
    return parser


def open_dcp_spreadsheet(spreadsheet_path, tab_name=None):
    if not os.path.exists(spreadsheet_path):
        raise FileNotFoundError(f"File not found at {spreadsheet_path}")
    try:
        return pd.read_excel(spreadsheet_path, sheet_name=tab_name, skiprows=[0, 1, 2, 4])
    except Exception as e:
        raise ValueError(
            f"Error reading spreadsheet file: {e} for {spreadsheet_path}"
        ) from e


def merge_file_manifest(wrangled_spreadsheet, file_manifest, file_mapping_dictionary):
    """Merge file manifest tab into wrangled spreadsheet and return wrangled_spreadsheet"""
    # TODO
    return wrangled_spreadsheet


def add_standard_fields(wrangled_spreadsheet, standard_values_dictionary):
    """Add standard fields like content description which for fastqs will always be DNA sequence"""
    # TODO
    return wrangled_spreadsheet


def add_tier1_fields(wrangled_spreadsheet, tier1_spreadsheet, tier1_to_file_dictionary):
    """Add info from tier1 into seq file tab."""
    # TODO
    tier1_spreadsheet = get_dcp_id_entities(tier1_spreadsheet, wrangled_spreadsheet)
    return wrangled_spreadsheet


def get_dcp_id_entities(tier1_spreadsheet, wrangled_spreadsheet):
    """Add protocol ids based on assay or sequencer type provided in tier 1.Raise error if not singular match is found."""
    # TODO
    return tier1_spreadsheet

def perform_checks(wrangled_spreadsheet):
    """Check validity of spreadsheet with basic checks"""
    if wrangled_spreadsheet['Lib Prep'] == '10x' and 'read1' not in wrangled_spreadsheet['read_index']:
        raise ValueError("10x fastqs should include at least 2 read files per read")
    if wrangled_spreadsheet['fastq']['biomaterials'] not in wrangled_spreadsheet['biomaterials']['id']:
        raise KeyError("IDs in sequence file tab, are not listed in biomaterial tab")

# add fields
fields_to_add = [
    "sequence_file.file_core.content_description.text",
    "sequence_file.read_length",
    "sequence_file.library_prep_id",
    "sequence_file.insdc_run_accessions",
    "library_preparation_protocol.protocol_core.protocol_id",
    "sequencing_protocol.protocol_core.protocol_id",
]


def main():
    parser = define_parse()
    args = parser.parse_args()

    file_manifest = open_dcp_spreadsheet(spreadsheet_path=args.file_manifest, tab_name="File_manifest")
    wrangled_spreadsheet = open_dcp_spreadsheet(args.wrangled_spreadsheet)
    if 'Sequence file' in wrangled_spreadsheet:
        del wrangled_spreadsheet['Sequence file']
    tier1_spreadsheet = open_dcp_spreadsheet(args.tier1_spreadsheet)

    wrangled_spreadsheet = merge_file_manifest(wrangled_spreadsheet, file_manifest, FILE_MANIFEST_MAPPING)
    wrangled_spreadsheet = add_standard_fields(wrangled_spreadsheet, FASTQ_STANDARD_FIELDS)
    wrangled_spreadsheet = add_tier1_fields(wrangled_spreadsheet, tier1_spreadsheet, TIER_1_MAPPING)
    perform_checks(wrangled_spreadsheet)

    output_filename = os.path.basename(args.wrangled_spreadsheet).replace(".xlsx", "_fastqed.xlsx")
    with pd.ExcelWriter(os.path.join(args.output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in wrangled_spreadsheet.items():
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)
    print(f"File metadata has been added to {os.path.join(args.output_path, output_filename)}.")

if __name__ == "__main__":
    main()