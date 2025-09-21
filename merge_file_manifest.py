import os
import argparse
import pandas as pd

from helper_files.constants.file_mapping import (
    FILE_MANIFEST_MAPPING,
    TIER_1_MAPPING,
    FASTQ_STANDARD_FIELDS
)
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
    parser.add_argument("-fm", "--file_manifest", action='store', 
                        dest="file_manifest", type=str, required=True,
                        help="File manifest path")
    parser.add_argument("-tw", "--dcp_tier1_spreadsheet", action="store",
                        dest="dt_spreadsheet", type=str, required=True,
                        help="DCP formeted tier 1 spreadsheet path")
    parser.add_argument("-t1", "--tier1_spreadsheet", action="store",
                        dest="tier1_spreadsheet", type=str, required=True,
                        help="Submitted tier 1 spreadsheet file path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata',
                        help="Directory for the output files")
    return parser

def main(file_manifest, dt_spreadsheet, tier1_spreadsheet, output_path):

    file_manifest = open_spreadsheet(spreadsheet_path=file_manifest, tab_name="File_manifest")
    dt_spreadsheet = open_spreadsheet(dt_spreadsheet)
    if 'Sequence file' in dt_spreadsheet:
        del dt_spreadsheet['Sequence file']
    tier1_spreadsheet = open_spreadsheet(tier1_spreadsheet)
    tier1_spreadsheet = flatten_tiered_spreadsheet(tier1_spreadsheet)

    dt_spreadsheet = merge_file_manifest(dt_spreadsheet, file_manifest, FILE_MANIFEST_MAPPING)
    dt_spreadsheet = add_standard_fields(dt_spreadsheet, FASTQ_STANDARD_FIELDS)
    dt_spreadsheet = add_tier1_fields(dt_spreadsheet, tier1_spreadsheet, TIER_1_MAPPING)
    perform_checks(dt_spreadsheet)

    output_filename = os.path.basename(dt_spreadsheet).replace(".xlsx", "_fastqed.xlsx")
    with pd.ExcelWriter(os.path.join(output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in dt_spreadsheet.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)

    print(f"File metadata has been added to {os.path.join(output_path, output_filename)}.")

if __name__ == "__main__":
    args = define_parse().parse_args()
    main(file_manifest=args.file_manifest, dt_spreadsheet=args.dt_spreadsheet,
         tier1_spreadsheet=args.tier1_spreadsheet, output_path=args.output_path)