import os
import re
import argparse
from collections import defaultdict

import pandas as pd

from helper_files.constants.tier2_mapping import TIER2_TO_DCP, TIER2_TO_DCP_UPDATE, LUNG_DIGESTION, TIER2_MANUAL_FIX
from helper_files.constants.dcp_required import dcp_required_entities
from helper_files.file_io import open_spreadsheet
from convert_to_dcp import fill_missing_ontology_ids, fill_ontology_labels

# Small helpers
def lower_list_values(l):
    return [field.lower() for field in l]

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
    

def get_fields_per_tab(tier2_df):
    fields_per_tab = defaultdict(list)
    for col in tier2_df.columns:
        fields_per_tab[get_entity_type(col)].append(col)
    return fields_per_tab

def field_is_id(field_name):
    return re.match(r'[\w_]+\.\w+_core\.\w+_id', field_name) is not None

def field_is_protocol(field_name):
    return re.match(r'^[\w_]+protocol\.\w+', field_name) is not None

def tab_is_protocol(tab_name):
    return re.match(r'.*protocol', tab_name) is not None

# Checks
def check_tab_in_spreadsheet(tab_name, spreadsheet):
        if tab_name not in spreadsheet:
            raise ValueError(f"Tab {tab_name} from Tier 2 metadata not found in spreadsheet.")

def check_field_already_in_spreadsheet(field_name, tab_name, spreadsheet):
    if field_name in spreadsheet[tab_name].columns and not field_is_id(field_name):
        del spreadsheet[tab_name][field_name]
        return field_name

def check_key_in_spreadsheet(key, spreadsheet):
    if key not in spreadsheet.columns:
        raise ValueError(f"Key column {key} not found in spreadsheet.")

def check_matching_keys(tier2_df, wrangled_spreadsheet, tab_name, key):
    if not wrangled_spreadsheet[tab_name][key].isin(tier2_df[key]).any():
        raise ValueError(f"No matching keys found between Tier 2 metadata and wrangled spreadsheet for tab {tab_name} using key {key}.")
    
def check_dcp_required_fields(df):
    req_ent = []
    for tab_name, tab in df.items():
        if tab_name == 'Schemas':
            continue
        req_ent.extend([req for req in dcp_required_entities[tab_name] if req not in tab])
        # req_mod = [tab for req_mod in dcp_required_modules[tab_name] if tab.columns.isin(req_mod)]
    if req_ent:
        print(f"Missing DCP required field(s) {'; '.join(req_ent)}")
        # if req_mod:
        #     print(f"Missing DCP required module field(s) {'; '.join(req_mod)}")

# other functions
def define_parse():
    parser = argparse.ArgumentParser(description="Merge Tier 2 metadata into DCP format.")
    parser.add_argument('--tier2_metadata', '-t2', type=str, required=True, help="Path to the Tier 2 metadata excel file.")
    parser.add_argument('--wrangled_spreadsheet', '-w', type=str, required=True, help="Path to the wrangled spreadsheet excel file.")
    parser.add_argument('--output_path', '-o', type=str, default='metadata', help="Path to save the merged output excel file.")
    return parser

def rename_tier2_columns(tier2_df, tier2_to_dcp):
    mapped_fields = list(tier2_to_dcp.keys()) + TIER2_MANUAL_FIX['dcp']
    mapped_fields= lower_list_values(mapped_fields)
    tier2_df.columns = lower_list_values(tier2_df.columns)
    if any(col.lower() not in mapped_fields for col in tier2_df.columns):
        raise ValueError(f"Tier 2 fields missing in mapping: {set(tier2_df.columns) - set(mapped_fields)}")
    return tier2_df.rename(columns=tier2_to_dcp)

def split_lung_dissociation(tier2_df, lung_digest_dict):
    if tier2_df['protocol_tissue_dissociation'].isna().all():
        if not tier2_df['protocol_tissue_dissociation_free_text'].isna().all():
            print(f"Need to update schema to include {tier2_df.loc[tier2_df['protocol_tissue_dissociation_free_text'].notna(), 'protocol_tissue_dissociation_free_text'].unique()} in enum.")
        else:
            print("Only NA values. Skipping tissue_dissociation conversion")
        return tier2_df
    all_diss_fields = set().union(*[lung_digest_dict[prot].keys() for prot in tier2_df['protocol_tissue_dissociation'].unique()])
    for diss in all_diss_fields:
        tier2_df[diss] = pd.NA
    for i, row in tier2_df.iterrows():
        prot = row['protocol_tissue_dissociation']
        if pd.isna(prot):
            continue
        if prot not in lung_digest_dict:
            raise ValueError(f"Digestion protocol {prot} not in pre-defined enum. Should be under `protocol_tissue_dissociation`")
        for diss in all_diss_fields:
            tier2_df.loc[i, diss] = lung_digest_dict[prot].get(diss, pd.NA)
    del tier2_df['protocol_tissue_dissociation']
    return tier2_df

def manual_fixes(tier2_df):
    if tier2_df.columns.isin(['protocol_tissue_dissociation', 'protocol_tissue_dissociation_free_text']).any():
        tier2_df = split_lung_dissociation(tier2_df, LUNG_DIGESTION)
    # TODO add gut diet fields mapping to diet_meat_consumption
    return tier2_df

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
    if flat_t2_df.columns.isin(TIER2_MANUAL_FIX['tier2']).any():
        flat_t2_df = manual_fixes(flat_t2_df)
    if drop_na:
        return flat_t2_df.dropna(axis=1, how='all')
    return flat_t2_df

def merge_overlap(wrangled_tab, tier2_fields, field_list, key):
    merged_df = pd.merge(
            wrangled_tab,
            tier2_fields.drop_duplicates(),
            on=key, how='outer', suffixes=('', '_t2')
        )
    common_cols = set(wrangled_tab.columns) & set(field_list) - {key}
    for col in common_cols:
        merged_df[col] = merged_df[col].combine_first(merged_df[f"{col}_t2"])
        merged_df = merged_df.drop([f"{col}_t2"], axis=1)
    return merged_df

def merge_sheets(wrangled_spreadsheet, tier2_df, tab_name, field_list, key, is_protocol):
    check_key_in_spreadsheet(key, wrangled_spreadsheet[tab_name])
    check_key_in_spreadsheet(key, tier2_df)
    if is_protocol:
        return merge_overlap(
            wrangled_spreadsheet[tab_name],
            tier2_df[field_list], field_list,
            key)
    check_matching_keys(tier2_df, wrangled_spreadsheet, tab_name, key)
    return pd.merge(
            wrangled_spreadsheet[tab_name],
            tier2_df[field_list],
            on=key, how='left'
        )

def merge_tier2_with_dcp(tier2_df, wrangled_spreadsheet):
    fields_per_tab = get_fields_per_tab(tier2_df)

    for tab_name, field_list in fields_per_tab.items():
        # do checks
        is_protocol = tab_is_protocol(tab_name)
        check_tab_in_spreadsheet(tab_name, wrangled_spreadsheet)
        if len(field_list) == 1 and field_is_id(field_list[0]):
            continue
        removed_fields = set()
        if not tab_is_protocol(tab_name):
            removed_fields = {check_field_already_in_spreadsheet(field, tab_name, wrangled_spreadsheet) for field in field_list}
            removed_fields.remove(None)
        if removed_fields:
            print(f'Fields exist in both spreadsheets. Overwritting previously wrangled metadata with tier 2:\n{"; ".join(removed_fields)}')
        key = get_tab_id(tab_name)
        # perform merge
        wrangled_spreadsheet[tab_name] = merge_sheets(wrangled_spreadsheet, tier2_df, tab_name, field_list, key, is_protocol)
    return wrangled_spreadsheet

def add_protocol_targets(tier2_df, wrangled_spreadsheet):
    prot_ids = [col for col in tier2_df if field_is_protocol(col) and field_is_id(col)]
    # to add dict of protocol: APpLied biomaterial if we have more tier 2 protocols
    # for now map only dissociation to cell_suspension
    apl = {'dissociation_protocol.protocol_core.protocol_id': {'from': 'specimen_from_organism.biomaterial_core.biomaterial_id', 'to': 'cell_suspension.biomaterial_core.biomaterial_id'}}
    for prot_id in prot_ids:
        if prot_id not in apl:
            raise KeyError(f'Add protocol {get_entity_type(prot_id)} to protocol biomaterial mapping dictionary')
        input_b = apl[prot_id]['from']
        output_b = apl[prot_id]['to']
        output_e = get_entity_type(output_b)
        b2p = {row[input_b]: row[prot_id] for _, row in tier2_df[[input_b, prot_id]].iterrows()}
        if not wrangled_spreadsheet[output_e][prot_id].isna().any():
            print(f'Merging {get_entity_type(prot_id)} with existing values. Investigate for potential need for merging.')
        wrangled_spreadsheet[output_e][prot_id] = wrangled_spreadsheet[output_e].apply(lambda x: '||'.join([b2p[x[input_b]], x[prot_id]]), axis=1)
    return wrangled_spreadsheet

def main():
    parser = define_parse()
    args = parser.parse_args()

    tier2_metadata_path = args.tier2_metadata
    wrangled_spreadsheet_path = args.wrangled_spreadsheet
    output_path = args.output_path

    all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}

    tier2_excel = open_spreadsheet(tier2_metadata_path)
    wrangled_spreadsheet = open_spreadsheet(wrangled_spreadsheet_path)

    tier2_df = flatten_tier2_spreadsheet(tier2_excel)
    tier2_df = rename_tier2_columns(tier2_df, all_tier2)
    print('\nPull ontology ids from fields:')
    tier2_df = fill_missing_ontology_ids(tier2_df)
    print('\nPull ontology labels from fields:')
    tier2_df = fill_ontology_labels(tier2_df)

    merged_df = merge_tier2_with_dcp(tier2_df, wrangled_spreadsheet)
    merged_df = add_protocol_targets(tier2_df, merged_df)
    check_dcp_required_fields(merged_df)

    output_filename = os.path.basename(wrangled_spreadsheet_path).replace(".xlsx", "_Tier2.xlsx")
    with pd.ExcelWriter(os.path.join(output_path, output_filename), engine='openpyxl') as writer:
        for tab_name, df in merged_df.items():
            # add empty row for "FILL OUT INFORMATION BELOW THIS ROW" row
            df = df.reindex(index=[-1] + list(df.index)).reset_index(drop=True)
            df.to_excel(writer, sheet_name=tab_name, index=False, startrow=3)
    print(f"Tier 2 metadata has been added to {os.path.join(output_path, output_filename)}.")

if __name__ == "__main__":
    main()