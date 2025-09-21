import os
import argparse

import pandas as pd

from helper_files.constants.tier2_mapping import TIER2_TO_DCP, TIER2_TO_DCP_UPDATE
from helper_files.utils import open_spreadsheet
from helper_files.convert import (
    fill_missing_ontology_ids,
    fill_ontology_labels,
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
                        dest="output_dir", type=str, required=False, default='metadata',
                        help="Directory for the output files")
    return parser

def main():
    parser = define_parse()
    args = parser.parse_args()

    tier2_spreadsheet_path = args.tier2_spreadsheet
    dt_spreadsheet_path = args.dt_spreadsheet
    output_path = args.output_path

    all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}

    tier2_excel = open_spreadsheet(tier2_spreadsheet_path)
    dt_spreadsheet = open_spreadsheet(dt_spreadsheet_path)

    tier2_df = flatten_tiered_spreadsheet(tier2_excel, merge_type='outer')
    tier2_df = manual_fixes(tier2_df)
    tier2_df = rename_tier2_columns(tier2_df, all_tier2)
    print('\nPull ontology ids from fields:')
    tier2_df = fill_missing_ontology_ids(tier2_df)
    print('\nPull ontology labels from fields:')
    tier2_df = fill_ontology_labels(tier2_df)

    merged_df = merge_tier2_with_dcp(tier2_df, dt_spreadsheet)
    merged_df = add_protocol_targets(tier2_df, merged_df)
    check_dcp_required_fields(merged_df)

    output_filename = os.path.basename(dt_spreadsheet_path).replace(".xlsx", "_Tier2.xlsx")
    with pd.ExcelWriter(os.path.join(output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in merged_df.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)
    print(f"Tier 2 metadata has been added to {os.path.join(output_path, output_filename)}.")

if __name__ == "__main__":
    main()