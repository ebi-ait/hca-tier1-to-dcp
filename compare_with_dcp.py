import argparse
import os
import sys
import json

import pandas as pd

# Open cellxgene spreadsheet
# Open DCP spreadsheet
    # provide file locally
    # if DOI, if unique ingest project/ submission, pull with api
# Compare number of tabs, use intersection
# Open each common tab 
    # compare number of entites per tab
    # compare ids per tab, for intersection
        # search for Tier 1 ID in DCP name, description, accession
    # compare values of common IDs

def define_parser():
    """Defines and returns the argument parser."""
    parser = argparse.ArgumentParser(description="Parser for the arguments")
    parser.add_argument("--collection", "-c", action="store",
                        dest="collection_id", type=str, required=True, help="Collection ID")
    parser.add_argument("--dataset", "-d", action="store",
                        dest="dataset_id", type=str, required=False, help="Dataset id")
    parser.add_argument("--wrangled-path", "-w", action="store", 
                        dest="wrangled_path", type=str, required=False, help="Path of previously wrangled project spreadsheet")
    parser.add_argument("--ingest-token", '-t', action="store",
                        dest='token', type=str, required=False,
                        help="Ingest token to query for existing projects with same DOI")
    return parser

def get_dataset_id(args):
    if args.dataset_id is not None:
        return args.dataset_id
    dataset_ids = [file.split("_")[1] for file in os.listdir('metadata') if file.startswith(args.collection_id)]
    if len(set(dataset_ids)) == 1:
        return dataset_ids[0]
    print("Please specify the -d dataset_id. There are available files for:")
    print('\n'.join(dataset_ids))
    sys.exit()

def open_tier1_spreadsheet(collection_id, dataset_id):
    try:
        tier1_spreadsheet_path = f"metadata/{collection_id}_{dataset_id}_dcp.xlsx"
        return pd.read_excel(tier1_spreadsheet_path, sheet_name=None, skiprows=[0, 1, 2, 4])
    except FileNotFoundError:
        print(f"File not found: {tier1_spreadsheet_path}")
        sys.exit()

def open_wrangled_spreadsheet(wranged_spreadsheet_path):
    # TODO add more options, from ingest
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
        return
    return id_field[0]

def get_number_of_field(tab, spreadsheet, field):
    return len(spreadsheet[tab][field])

def get_values_of_field(tab, spreadsheet, field):
    return spreadsheet[tab][field].tolist()

def export_report_json(collection_id, dataset_id, report_dict):
    with open(f'compare_report/{collection_id}_{dataset_id}_compare.json', 'w', encoding='UTF-8') as json_file:
                    json.dump(report_dict, json_file)

def main():
    args = define_parser().parse_args()
    collection_id = args.collection_id
    dataset_id = get_dataset_id(args)
    wrangled_path = args.wrangled_path
    report_dict = {}
    report_dict['ids'] = {'n': {}, 'values': {}}
    report_dict['tabs'] = {'excess': {}, 'n': {}, 'intersect': []}
    os.makedirs('compare_report', exist_ok=True)

    # Open cellxgene spreadsheet
    tier1_spreadsheet = open_tier1_spreadsheet(collection_id, dataset_id)
    # Open DCP spreadsheet
    wrangled_spreadsheet = open_wrangled_spreadsheet(wrangled_path)

    # Compare number of tabs, use intersection
    if set(tier1_spreadsheet) == set(wrangled_spreadsheet):
        tier1_excess_tabs = [] 
        wrangled_excess_tabs = []
        intersect_tabs = list(tier1_spreadsheet)
        print("All good on tabs side.")
    elif len(tier1_spreadsheet) > len(wrangled_spreadsheet):
        tier1_excess_tabs = [tab for tab in set(tier1_spreadsheet) if tab not in set(wrangled_spreadsheet)]
        wrangled_excess_tabs = []
        intersect_tabs = [tab for tab in set(tier1_spreadsheet) if tab in set(wrangled_spreadsheet)]
        print("More tabs in Tier 1.\n\t" + '\n\t'.join(tier1_excess_tabs))
    else:
        tier1_excess_tabs = []
        wrangled_excess_tabs = [tab for tab in set(wrangled_spreadsheet) if tab not in set(tier1_spreadsheet)]
        intersect_tabs = [tab for tab in set(wrangled_spreadsheet) if tab in set(tier1_spreadsheet)]
        print("More tabs in DCP.\n\t" + '\n\t'.join(wrangled_excess_tabs))

    report_dict['tabs']['n'] = {'tier1':len(tier1_spreadsheet), 'wranlged': len(wrangled_spreadsheet)}
    report_dict['tabs']['excess'] = {'tier1': tier1_excess_tabs, 'wrangled': wrangled_excess_tabs}
    report_dict['tabs']['intersect'] = intersect_tabs

    # compare number and values of ids
    for tab in intersect_tabs:
        print(f"\n\nComparing tab {tab}")
        if tab.startswith("Project") or tab == 'Analysis file' or tab == 'Sequence file':
            # skip those tabs since this info is not entirely recorded in the CxG collection
            continue
        # find id field
        tab_id = get_tab_id(tab, tier1_spreadsheet)
        if tab_id != get_tab_id(tab, wrangled_spreadsheet):
            print(f"Id field doesn't match across spreadsheets for {tab}:\n\tTier1 {get_tab_id(tab, tier1_spreadsheet)} vs Wrangled {get_tab_id(tab, wrangled_spreadsheet)}")
            continue

        # compare Number and Values of ids per tab
        report_dict['ids']['n'][tab] = {}
        # Number of ids
        n_ids = {}
        n_ids['tier1'] = get_number_of_field(tab, tier1_spreadsheet, tab_id)
        n_ids['wrangled'] = get_number_of_field(tab, wrangled_spreadsheet, tab_id)
        report_dict['ids']['n'][tab] = {'tier1': n_ids['tier1'], 'wrangled': n_ids['wrangled']}

        if n_ids['tier1'] != n_ids['wrangled']:
            print(f"WARNING: Not equal number of {tab}\n\tTier1 {n_ids['tier1']} vs Wrangled {n_ids['wrangled']}")
            if input("Continue anyway? (yes/no)\n") in ['no', 'n', 'NO', 'No']:
                export_report_json(collection_id, dataset_id, report_dict)
                sys.exit()
        
        # Value of ids
        v_ids = {}
        v_ids['tier1'] = get_values_of_field(tab, tier1_spreadsheet, tab_id)
        v_ids['wrangled'] = get_values_of_field(tab, wrangled_spreadsheet, tab_id)
        intersect_ids = [t for t in v_ids['tier1'] if t in v_ids['wrangled']]
        report_dict['ids']['values'][tab] = {'tier1': v_ids['tier1'], 'wrangled': v_ids['wrangled']}

        if intersect_ids != v_ids['tier1']:
            print(f"WARNING: Values of {tab_id} not identical across spreadsheets\n\t"+
                  f"Tier 1 {','.join(sorted(v_ids['tier1']))}\n\tWrangled {','.join(sorted(v_ids['wrangled']))}")

    export_report_json(collection_id, dataset_id, report_dict)

if __name__ == "__main__":
    main()
