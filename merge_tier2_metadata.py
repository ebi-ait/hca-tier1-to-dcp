import os
import argparse

import pandas as pd

from helper_files.constants.tier2_mapping import TIER2_TO_DCP, TIER2_TO_DCP_UPDATE
from helper_files.utils import open_spreadsheet
from helper_files.convert import (
    fill_ontologies,
    flatten_tiered_spreadsheet
)
from helper_files.merge import (
    manual_fixes,
    rename_tier2_columns,
    merge_tier2_with_dcp,
    add_protocol_targets,
    check_dcp_required_fields
)

def define_parse():
    parser = argparse.ArgumentParser(description="Merge Tier 2 metadata into DCP format.")
    parser.add_argument('-t2', '--tier2_spreadsheet', action="store",
                        dest="tier2_spreadsheet", type=str, required=True,
                        help="Submitted tier 2 spreadsheet file path")
    parser.add_argument("-dt", "--dt_spreadsheet", action="store",
                        dest="dt_spreadsheet", type=str, required=True,
                        help="DCP formeted tier 1 spreadsheet path")
    parser.add_argument("-o", "--output_dir", action="store",
                        dest="output_dir", type=str, required=False, default='metadata/t2/',
                        help="Directory for the output files")
    return parser

def main(tier2_spreadsheet, dt_spreadsheet, output_dir='metadata'):
    
    all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}

    tier2_df = open_spreadsheet(tier2_spreadsheet)
    dt_df = open_spreadsheet(dt_spreadsheet)

    tier2_flat = flatten_tiered_spreadsheet(tier2_df, merge_type='outer')
    tier2_flat = manual_fixes(tier2_flat)
    tier2_flat = rename_tier2_columns(tier2_flat, all_tier2)
    tier2_flat = fill_ontologies(tier2_flat)
    
    merged_df = merge_tier2_with_dcp(tier2_flat, dt_df)
    merged_df = add_protocol_targets(tier2_flat, merged_df)
    check_dcp_required_fields(merged_df)

    output_filename = os.path.basename(dt_spreadsheet).replace(".xlsx", "_Tier2.xlsx")
    with pd.ExcelWriter(os.path.join(output_dir, output_filename), engine='openpyxl') as writer:
        for tab_name, df in merged_df.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)
    print(f"Tier 2 metadata has been added to {os.path.join(output_dir, output_filename)}.")

if __name__ == "__main__":
    args = define_parse().parse_args()
    main(tier2_spreadsheet=args.tier2_spreadsheet, dt_spreadsheet=args.dt_spreadsheet, output_dir=args.output_dir)