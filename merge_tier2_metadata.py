import os
import re
import argparse
from collections import defaultdict

import pandas as pd

from helper_files.tier2_mapping import TIER2_TO_DCP, TIER2_TO_DCP_UPDATE

def define_parse():
    parser = argparse.ArgumentParser(description="Merge Tier 2 metadata into DCP format.")
    parser.add_argument('--tier2_metadata', '-t2', type=str, required=True, help="Path to the Tier 2 metadata excel file.")
    parser.add_argument('--wrangled_spreadsheet', '-w', type=str, required=True, help="Path to the wrangled spreadsheet excel file.")
    parser.add_argument('--output_path', '-o', type=str, required=True, default='metadata', help="Path to save the merged output excel file.")
    return parser

def open_dcp_spreadsheet(spreadsheet_path):
    if not os.path.exists(spreadsheet_path):
        raise FileNotFoundError(f"File not found at {spreadsheet_path}")
    try:
        return pd.read_excel(spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except Exception as e:
        raise ValueError(f"Error reading spreadsheet file: {e} for {spreadsheet_path}") from e

def rename_tier2_columns(tier2_df, tier2_to_dcp):
    if any(col.lower() not in tier2_to_dcp.keys() for col in tier2_df.columns):
        raise ValueError(f"Tier 2 fields missing in mapping: {set(tier2_df.columns) - set(tier2_to_dcp.keys())}")
    return tier2_df.rename(columns=tier2_to_dcp)

def flatten_tier2_spreadsheet(tier2_excel, drop_na=True):
    key_cols = ['donor_id', 'sample_id', 'dataset_id', 'library_id']
    flat_t2_df = pd.DataFrame()
    for tab_name, tab_data in tier2_excel.items():
        tab_data.columns = [col.lower() for col in tab_data.columns]
        if flat_t2_df.empty:
            flat_t2_df = tab_data
            continue
        key_col = next((col for col in key_cols if col in tab_data.columns and col in flat_t2_df.columns), None)
        if key_col is None:
            raise ValueError(f"No common key column found for tab {tab_name} for merging among: {key_cols}")
        flat_t2_df = pd.merge(flat_t2_df, tab_data, how='outer', on=key_col)
    if drop_na:
        return flat_t2_df.dropna(axis=1, how='all')
    return flat_t2_df

def get_entity_type(field_name):
    return field_name.split('.')[0].replace('_', ' ').capitalize() if '.' in field_name else None

def get_tab_id(tab_name):
    if 'protocol' in tab_name.lower():
        entity_type = 'protocol'
    elif tab_name in ['Donor organism', 'Specimen from organism', 'Cell suspension', 'Organoid', 'Cell line', 'Imaged specimen']:
        entity_type = 'biomaterial'
    else: 
        raise ValueError(f"Unknown tab name: {tab_name}")
    return f"{tab_name.replace(' ', '_').lower()}.{entity_type}_core.{entity_type}_id"
    
def check_tab_in_spreadsheet(tab_name, spreadsheet):
        if tab_name not in spreadsheet:
            raise ValueError(f"Tab {tab_name} from Tier 2 metadata not found in spreadsheet.")

def check_field_already_in_spreadsheet(field_name, tab_name, spreadsheet):
    if re.search(r'[\w_]+\.\w+_core\.\w+_id', field_name):
        return
    if field_name in spreadsheet[tab_name].columns:
        print(f"Field {field_name} already exists in tab {tab_name} of the spreadsheet. It will be overwritten with Tier 2 data.")
        del spreadsheet[tab_name][field_name]

def check_key_in_spreadsheet(key, tab_name, spreadsheet):
    if key not in spreadsheet[tab_name].columns:
        raise ValueError(f"Key column {key} not found in tab {tab_name} of the spreadsheet.")

def check_matching_keys(tier2_df, wrangled_spreadsheet, tab_name, key):
    if not wrangled_spreadsheet[tab_name][key].isin(tier2_df[key]).any():
        raise ValueError(f"No matching keys found between Tier 2 metadata and wrangled spreadsheet for tab {tab_name} using key {key}.")

def merge_tier2_with_dcp(tier2_df, wrangled_spreadsheet):
    fields_per_tab = defaultdict(list)
    for col in tier2_df.columns:
        fields_per_tab[get_entity_type(col)].append(col)

    for tab_name, field_list in fields_per_tab.items():
        # do checks
        check_tab_in_spreadsheet(tab_name, wrangled_spreadsheet)
        if len(field_list) == 1 and field_list[0].endswith('_id'):
            continue
        # TODO until protocols is done, we add info manually
        if tab_name.endswith('protocol'):
            print(f"Skipping merge for protocol {tab_name}, not yet implemented.")
            continue
        for field in field_list:
            check_field_already_in_spreadsheet(field, tab_name, wrangled_spreadsheet)
        key = get_tab_id(tab_name)
        check_key_in_spreadsheet(key, tab_name, wrangled_spreadsheet)
        check_matching_keys(tier2_df, wrangled_spreadsheet, tab_name, key)
        # perform merge
        wrangled_spreadsheet[tab_name] = pd.merge(
            wrangled_spreadsheet[tab_name],
            tier2_df[field_list],
            on=key, how='left'
        )
    return wrangled_spreadsheet

def main():
    parser = define_parse()
    args = parser.parse_args()

    tier2_metadata_path = args.tier2_metadata
    wrangled_spreadsheet_path = args.wrangled_spreadsheet
    output_path = args.output_path

    all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}

    tier2_excel = open_dcp_spreadsheet(tier2_metadata_path)
    wrangled_spreadsheet = open_dcp_spreadsheet(wrangled_spreadsheet_path)

    tier2_df = flatten_tier2_spreadsheet(tier2_excel)
    tier2_df = rename_tier2_columns(tier2_df, all_tier2)
    merged_df = merge_tier2_with_dcp(tier2_df, wrangled_spreadsheet)

    output_filename = os.path.basename(wrangled_spreadsheet_path).replace(".xlsx", "_Tier2.xlsx")
    with pd.ExcelWriter(os.path.join(output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in merged_df.items():
            df.to_excel(writer, sheet_name=tab_name, index=False)
    return merged_df

if __name__ == "__main__":
    main()