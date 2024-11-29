import argparse
import os
import re
import sys
import json

import pandas as pd
from helper_files.tier1_mapping import entity_types, all_entities

# Open cellxgene spreadsheet
# Open DCP spreadsheet
    # provide file locally
# Compare number of tabs, use intersection
# Open each common tab 
    # compare number of entites per tab
    # compare ids per tab, for intersection
        # search for Tier 1 ID in DCP name, description, accession
    # compare values of common IDs

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--collection_id", "-c", action="store",
                        dest="collection_id", type=str, required=True, help="Collection ID")
    parser.add_argument("--wrangled_path", "-w", action="store", 
                        dest="wrangled_path", type=str, required=True, help="Path of previously wrangled project spreadsheet")
    parser.add_argument("--dataset_id", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    return parser

def get_dataset_id(args):
    if args.dataset_id is not None:
        return args.dataset_id
    dataset_ids = [file.split("_")[1] for file in os.listdir('metadata') if file.startswith(args.collection_id)]
    if len(set(dataset_ids)) == 1:
        return dataset_ids[0]
    print("Please specify the -d dataset_id. There are available files for:")
    print('\n'.join(set(dataset_ids)))
    sys.exit()

def open_tier1_spreadsheet(collection_id, dataset_id):
    try:
        tier1_spreadsheet_path = f"metadata/{collection_id}_{dataset_id}_dcp.xlsx"
        return pd.read_excel(tier1_spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"File not found: {tier1_spreadsheet_path}")
        sys.exit()

def open_wrangled_spreadsheet(wranged_spreadsheet_path):
    try:
        return pd.read_excel(wranged_spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"File not found: {wranged_spreadsheet_path}")
        sys.exit()

def get_tab_id(tab, spreadsheet):
    id_suffixs = ['.biomaterial_core.biomaterial_id', '.file_core.file_name', '.protocol_core.protocol_id']
    id_fields = [tab.lower().replace(" ", "_") + suffix for suffix in id_suffixs]
    id_field = spreadsheet[tab].columns[spreadsheet[tab].columns.isin(id_fields)].tolist()
    if len(id_field) > 1:
        print("More ID fields than expected: " + id_fields)
        return False
    return id_field[0]

def check_tab_id(tab, wrangled_spreadsheet, tier1_spreadsheet):
    tab_id = get_tab_id(tab, tier1_spreadsheet)
    if tab_id != get_tab_id(tab, wrangled_spreadsheet):
        print(f"Id field doesn't match across spreadsheets for {tab}:\n\t" +
              f"Tier1 {get_tab_id(tab, tier1_spreadsheet)} vs Wrangled {get_tab_id(tab, wrangled_spreadsheet)}")
        return True
    return False

def get_number_of_field(tab, spreadsheet, field):
    return len(spreadsheet[tab][field])

def get_values_of_field(tab, spreadsheet, field):
    return spreadsheet[tab][field].tolist()

def export_report_json(collection_id, dataset_id, report_dict):
    with open(f'report_compare/{collection_id}_{dataset_id}_compare.json', 'w', encoding='UTF-8') as json_file:
                    json.dump(report_dict, json_file)

def init_report_dict():
    report_dict = {}
    report_dict['ids'] = {'n': {}, 'values': {}}
    report_dict['tabs'] = {'excess': {}, 'n': {}, 'intersect': []}
    report_dict['values'] = {}
    os.makedirs('report_compare', exist_ok=True)
    return report_dict

def compare_n_tabs(tier1_spreadsheet, wrangled_spreadsheet, report_dict):
    wrangled_excess_tabs = [tab for tab in set(wrangled_spreadsheet) if tab not in set(tier1_spreadsheet)]
    tier1_excess_tabs = [tab for tab in set(tier1_spreadsheet) if tab not in set(wrangled_spreadsheet)]
    if not tier1_excess_tabs and not wrangled_excess_tabs:
        intersect_tabs = list(tier1_spreadsheet)
    elif len(tier1_spreadsheet) > len(wrangled_spreadsheet):
        intersect_tabs = [tab for tab in set(tier1_spreadsheet) if tab in set(wrangled_spreadsheet)]
        print(f"{BOLD_START}WARNING{BOLD_END}: More tabs in Tier 1.\n\t" + '\n\t'.join(tier1_excess_tabs))
    else:
        intersect_tabs = [tab for tab in set(wrangled_spreadsheet) if tab in set(tier1_spreadsheet)]
        print(f"More tabs in DCP.\n\t {'; '.join(wrangled_excess_tabs)}")
    
    report_dict['tabs']['n'] = {'tier1':len(tier1_spreadsheet), 'wranlged': len(wrangled_spreadsheet)}
    report_dict['tabs']['excess'] = {'tier1': tier1_excess_tabs, 'wrangled': wrangled_excess_tabs}
    report_dict['tabs']['intersect'] = intersect_tabs
    return report_dict

def compare_n_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet, collection_id, dataset_id):
    n_ids = {}
    
    tab_id = get_tab_id(tab, tier1_spreadsheet)
    n_ids['tier1'] = get_number_of_field(tab, tier1_spreadsheet, tab_id)
    n_ids['wrangled'] = get_number_of_field(tab, wrangled_spreadsheet, tab_id)
    report_dict['ids']['n'][tab] = {'tier1': n_ids['tier1'], 'wrangled': n_ids['wrangled']}
    
    if n_ids['tier1'] != n_ids['wrangled']:
        print(f"{BOLD_START}WARNING{BOLD_END}: Not equal number of {tab}\n\tTier1 {n_ids['tier1']} vs Wrangled {n_ids['wrangled']}")
        if input("Continue anyway? (yes/no)") in ['no', 'n', 'NO', 'No']:
            export_report_json(collection_id, dataset_id, report_dict)
            sys.exit()
    return report_dict

def compare_v_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet):
    v_ids = {}
    tab_id = get_tab_id(tab, tier1_spreadsheet)
    v_ids['tier1'] = get_values_of_field(tab, tier1_spreadsheet, tab_id)
    v_ids['wrangled'] = get_values_of_field(tab, wrangled_spreadsheet, tab_id)
    intersect_ids = [t for t in v_ids['tier1'] if t in v_ids['wrangled']]
    report_dict['ids']['values'][tab] = {'tier1': v_ids['tier1'], 'wrangled': v_ids['wrangled']}
    if intersect_ids != v_ids['tier1']:
        print(f"{BOLD_START}WARNING{BOLD_END}: {tab_id} IDs not identical between spreadsheets\n\t"+
              f"Tier 1 {', '.join(sorted(v_ids['tier1']))}\n\tWrangled {', '.join(sorted(v_ids['wrangled']))}")
    
    return report_dict

def get_unmatched_ids(report_dict, tab, origin):
    opposed_origin = 'tier1' if origin == 'wrangled' else 'wrangled'
    return set(report_dict['ids']['values'][tab][origin]) - set(report_dict['ids']['values'][tab][opposed_origin])

def compare_filled_fields_stats(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet):
    tier1_cols = tier1_spreadsheet[tab].dropna(axis='columns').columns
    wrang_cols = wrangled_spreadsheet[tab].dropna(axis='columns').columns
    tier1_excess_fields = [col for col in tier1_cols if col not in wrang_cols]
    wrang_excess_fields = [col for col in wrang_cols if col not in tier1_cols]
    fields_intersect = [col for col in wrang_cols if col in tier1_cols]
    report_dict['values'][tab] = {'excess': {'tier1': tier1_excess_fields, 'wrang': wrang_excess_fields}, 'intersect': fields_intersect}
    return report_dict

def drop_external_ids(comp_df):
    '''Drop columns that are IDs of protocols or input biomaterials'''
    linked_ids = [re.match(r'.*_core\..*_id',e).string for e in comp_df.columns.levels[0] if re.match(r'.*_core\..*_id',e)]
    if linked_ids:
        comp_df = comp_df.drop(columns=linked_ids)
        comp_df.columns = comp_df.columns.remove_unused_levels()
    return comp_df

def get_slim_comp_df(comp_df, tab):
    '''Drop ontology & ontology label fields if only all are different and shorten id index'''
    drop_ont_col = []
    for field in comp_df.columns.levels[0]:
        if field.endswith('ontology') and \
                field.replace('ontology', 'text') in comp_df and \
                    field.replace('ontology', 'ontology_label') in comp_df:
            drop_ont_col.extend([field, field.replace('ontology', 'ontology_label')])
    comp_df.index.name = tab.lower().replace(' ', '_') + '_id'
    if drop_ont_col:
        comp_df_slim = comp_df.drop(columns=drop_ont_col)
        return comp_df_slim
    return comp_df

def compare_filled_fields(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet):
    report_dict = compare_filled_fields_stats(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet)
    tier1_excess_fields = report_dict['values'][tab]['excess']['tier1']
    fields_intersect = report_dict['values'][tab]['intersect']
    if tier1_excess_fields:
        print(f"In tab {tab} we have more metadata in Tier 1:\n\t{', '.join(tier1_excess_fields)}")
    tab_id = get_tab_id(tab, tier1_spreadsheet)
    # get clean dfs (identical IDs & columns) to compare
    if tab in entity_types['biomaterial']:
        if not all(id in wrangled_spreadsheet[tab][tab_id].values for id in tier1_spreadsheet[tab][tab_id]):
            print(f"{BOLD_START}WARNING{BOLD_END}: Cannot compare entities with not identical IDs")
            print(f"\tTier1 {tab} unmatched IDs: {get_unmatched_ids(report_dict, tab, 'tier1')}")
            print(f"\tWrangled {tab} unmatched IDs: {get_unmatched_ids(report_dict, tab, 'wrangled')}")
            return report_dict
        comp_tier1 = tier1_spreadsheet[tab][fields_intersect].set_index(fields_intersect[0]).sort_index()
        comp_wrang = wrangled_spreadsheet[tab][fields_intersect].set_index(fields_intersect[0]).sort_index()
    else:
        # protocol IDs are not defined in tier 1, therefore, we can skip them
        comp_tier1 = tier1_spreadsheet[tab][fields_intersect].drop(columns=get_tab_id(tab, tier1_spreadsheet))
        comp_wrang = wrangled_spreadsheet[tab][fields_intersect].drop(columns=get_tab_id(tab, wrangled_spreadsheet))
    comp_df = comp_tier1.compare(comp_wrang,result_names= ('tier1', 'wrangled'), align_axis=1)
    comp_df = drop_external_ids(comp_df)
    report_dict['values'][tab]['values_diff'] = {}
    for field in comp_df.columns.levels[0]:
        report_dict['values'][tab]['values_diff'][field] = comp_df[field].to_dict(orient='index')
    if not comp_df.empty:
        ont_fields = sum(['ontology' in field for field in comp_df.columns.levels[0]])
        print(f'{tab}: {len(comp_df.columns.levels[0])} fields from {len(comp_df.index)} ids, have different values.' + \
              f'\t{ont_fields} ontology fields not shown here' if ont_fields == 2 else '')
        print(get_slim_comp_df(comp_df, tab))
    return report_dict

def main():
    args = define_parser().parse_args()
    collection_id = args.collection_id
    dataset_id = get_dataset_id(args)
    wrangled_path = args.wrangled_path

    report_dict = init_report_dict()

    # Open cellxgene spreadsheet
    tier1_spreadsheet = open_tier1_spreadsheet(collection_id, dataset_id)
    # Open DCP spreadsheet
    wrangled_spreadsheet = open_wrangled_spreadsheet(wrangled_path)
    
    # Compare number of tabs
    print(f"{BOLD_START}____COMPARE TABS____{BOLD_END}")
    report_dict = compare_n_tabs(tier1_spreadsheet, wrangled_spreadsheet, report_dict)

    # compare number and values of ids for intersect tabs
    print(f"{BOLD_START}____COMPARE IDs____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            # skip project or file tabs since info is not fully recorded in the CxG collection
            continue
            
        # check tab id
        if check_tab_id(tab, wrangled_spreadsheet, tier1_spreadsheet):
            continue
        
        # compare Number and Values of ids per tab
        report_dict = compare_n_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet, collection_id, dataset_id)
        # Value of ids
        if tab in entity_types['protocol']:
            # for protocol we don't care about matching IDs with tier 1
            continue
        print(f"{BOLD_START}Comparing {tab} IDs:{BOLD_END}")
        report_dict = compare_v_ids(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet)

    # compare values
    print(f"{BOLD_START}____COMPARE VALUES____{BOLD_END}")
    for tab in all_entities:
        if tab not in report_dict['tabs']['intersect'] or tab in entity_types['project'] + entity_types['file']:
            continue
        print(f"{BOLD_START}Comparing {tab} values:{BOLD_END}")
        report_dict = compare_filled_fields(tab, report_dict, tier1_spreadsheet, wrangled_spreadsheet)

    export_report_json(collection_id, dataset_id, report_dict)

BOLD_START = '\033[1m'
BOLD_END = '\033[0;0m'

if __name__ == "__main__":
    main()
