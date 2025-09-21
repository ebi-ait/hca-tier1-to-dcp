import os
import argparse
import pandas as pd

from helper_files.constants.file_mapping import FILE_MANIFEST_MAPPING, TIER_1_MAPPING, FASTQ_STANDARD_FIELDS
from helper_files.merge import (
    open_spreadsheet,
    flatten_tiered_spreadsheet,
    merge_file_manifest,
    add_standard_fields,
    add_tier1_fields,
    perform_checks
)

def define_parse():
    parser = argparse.ArgumentParser(description="Merge Tier 2 metadata into DCP format.")
    parser.add_argument("--file_manifest", "-f", type=str, required=True, help="Path to the File manifest excel file.")
    parser.add_argument("--wrangled_spreadsheet", "-w", type=str, required=True, help="Path to the wrangled spreadsheet excel file.")
    parser.add_argument("--tier1_spreadsheet", "-t1", type=str, required=True, help="Path to the Tier 1 metadata excel file.")
    parser.add_argument("--output_path", "-o", type=str, default="metadata", help="Path to save the merged output excel file.")
    return parser

def main():
    parser = define_parse()
    args = parser.parse_args()

    file_manifest = open_spreadsheet(spreadsheet_path=args.file_manifest, tab_name="File_manifest")
    wrangled_spreadsheet = open_spreadsheet(args.wrangled_spreadsheet)
    if 'Sequence file' in wrangled_spreadsheet:
        del wrangled_spreadsheet['Sequence file']
    tier1_spreadsheet = open_spreadsheet(args.tier1_spreadsheet)
    tier1_spreadsheet = flatten_tiered_spreadsheet(tier1_spreadsheet)

    wrangled_spreadsheet = merge_file_manifest(wrangled_spreadsheet, file_manifest, FILE_MANIFEST_MAPPING)
    wrangled_spreadsheet = add_standard_fields(wrangled_spreadsheet, FASTQ_STANDARD_FIELDS)
    wrangled_spreadsheet = add_tier1_fields(wrangled_spreadsheet, tier1_spreadsheet, TIER_1_MAPPING)
    perform_checks(wrangled_spreadsheet)

    output_filename = os.path.basename(args.wrangled_spreadsheet).replace(".xlsx", "_fastqed.xlsx")
    with pd.ExcelWriter(os.path.join(args.output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in wrangled_spreadsheet.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)

    print(f"File metadata has been added to {os.path.join(args.output_path, output_filename)}.")

if __name__ == "__main__":
    main()