import os
import argparse
import pandas as pd

from helper_files.constants.file_mapping import (
    FILE_MANIFEST_MAPPING,
    TIER_1_MAPPING,
    FASTQ_STANDARD_FIELDS
)
from helper_files.merge import (
    merge_overlap,
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
    parser.add_argument("-dt", "--dcp_tier1_spreadsheet", action="store",
                        dest="dt_spreadsheet", type=str, required=True,
                        help="DCP formeted tier 1 spreadsheet path")
    parser.add_argument("-t1", "--tier1_spreadsheet", action="store",
                        dest="tier1_spreadsheet", type=str, required=True,
                        help="Submitted tier 1 spreadsheet file path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/fm/',
                        help="Directory for the output files")
    return parser

def main(file_manifest, dt_spreadsheet, tier1_spreadsheet, output_dir):

    file_manifest = open_spreadsheet(spreadsheet_path=file_manifest, tab_name="File_manifest")
    dt_df = open_spreadsheet(dt_spreadsheet)
    # if 'Sequence file' in dt_df:
    #     del dt_df['Sequence file']
    tier1_spreadsheet = open_spreadsheet(tier1_spreadsheet)
    tier1_spreadsheet = flatten_tiered_spreadsheet(tier1_spreadsheet)

    file_manifest = file_manifest.rename(columns=FILE_MANIFEST_MAPPING)
    dt_df['Sequence file'] = merge_overlap(dt_df['Sequence file'], file_manifest, list(file_manifest.columns), key='sequence_file.file_core.file_name', suffix='fm')
    dt_df['Sequence file'] = add_standard_fields(dt_df['Sequence file'], FASTQ_STANDARD_FIELDS)
    dt_df['Sequence file'] = add_tier1_fields(dt_df, tier1_spreadsheet, TIER_1_MAPPING)
    perform_checks(dt_df)

    output_filename = os.path.basename(dt_spreadsheet).replace(".xlsx", "_fastqed.xlsx")
    with pd.ExcelWriter(os.path.join(output_dir, output_filename), engine='openpyxl') as writer:
        for tab_name, df in dt_df.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)

    print(f"File metadata has been added to {os.path.join(output_dir, output_filename)}.")

if __name__ == "__main__":
    args = define_parse().parse_args()
    main(file_manifest=args.file_manifest, dt_spreadsheet=args.dt_spreadsheet,
         tier1_spreadsheet=args.tier1_spreadsheet, output_dir=args.output_dir)