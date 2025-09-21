import os
import argparse
import pandas as pd

from helper_files.constants.file_mapping import FILE_MANIFEST_MAPPING, TIER_1_MAPPING, FASTQ_STANDARD_FIELDS
from helper_files.utils import open_spreadsheet
from helper_files.convert import flatten_tier1

LAST_BIOMATERIAL = 'cell_suspension.biomaterial_core.biomaterial_id'

def define_parse():
    parser = argparse.ArgumentParser(description="Merge Tier 2 metadata into DCP format.")
    parser.add_argument("--file_manifest", "-f", type=str, required=True, help="Path to the File manifest excel file.")
    parser.add_argument("--wrangled_spreadsheet", "-w", type=str, required=True, help="Path to the wrangled spreadsheet excel file.")
    parser.add_argument("--tier1_spreadsheet", "-t1", type=str, required=True, help="Path to the Tier 1 metadata excel file.")
    parser.add_argument("--output_path", "-o", type=str, default="metadata", help="Path to save the merged output excel file.")
    return parser

def merge_file_manifest(wrangled_spreadsheet, file_manifest, file_mapping_dictionary):
    """Merge file manifest tab into wrangled spreadsheet and return wrangled_spreadsheet"""
    file_manifest = file_manifest[file_mapping_dictionary.keys()].rename(columns=file_mapping_dictionary)
    wrangled_spreadsheet['Sequence file'] = file_manifest
    return wrangled_spreadsheet

def get_fastq_ext(row):
    for suffix in ['fastq.gz', 'fastq', 'fq.gz', 'fq']:
        if row.endswith(suffix):
            return suffix 
    raise KeyError(f'filename {row} does not have known extension [`fastq.gz`, `fastq`, `fq.gz`, `fq`] for fastq file.')

def add_standard_fields(wrangled_spreadsheet, standard_values_dictionary):
    """Add standard fields like content description which for fastqs will always be DNA sequence"""
    wrangled_spreadsheet['Sequence file']['sequence_file.file_core.format'] = wrangled_spreadsheet['Sequence file']['sequence_file.file_core.file_name'].apply(get_fastq_ext)
    for key, value in standard_values_dictionary.items():
        wrangled_spreadsheet['Sequence file'][key] = value
    return wrangled_spreadsheet


def add_tier1_fields(wrangled_spreadsheet, tier1_spreadsheet, tier1_to_file_dictionary):
    """Add info from tier1 into seq file tab."""
    if any(key not in tier1_spreadsheet for key in tier1_to_file_dictionary.keys()):
        raise KeyError(f'Did not find {[key for key in tier1_to_file_dictionary.keys() if key not in tier1_spreadsheet]} in tier 1 spreadsheet')
    tier1_mapped = tier1_spreadsheet[tier1_to_file_dictionary.keys()].rename(columns=tier1_to_file_dictionary)
    tier1_mapped = get_dcp_protocol_ids(tier1_mapped, wrangled_spreadsheet)
    wrangled_spreadsheet['Sequence file'] = wrangled_spreadsheet['Sequence file'].merge(tier1_mapped,
                                                    on=LAST_BIOMATERIAL,
                                                    how='left')
    return wrangled_spreadsheet


def get_dcp_protocol_ids(tier1_spreadsheet, wrangled_spreadsheet):
    """Add protocol ids based on assay or sequencer type provided in tier 1. Raise error if not singular match is found."""
    for key, value in tier1_spreadsheet.items():
        if 'protocol' not in key:
            continue
        df_dict = map_key_to_id(key, wrangled_spreadsheet)
        if not all(value.isin(df_dict.keys())):
            raise KeyError(f"Value {value[value.isin(df_dict.keys())].unique()} not found in wrangled spreadsheet, but exist on tier 1")
        id_key = get_protocol_id(key)
        tier1_spreadsheet[id_key] = value.replace(df_dict)
        tier1_spreadsheet = tier1_spreadsheet.drop(columns=key)

    return tier1_spreadsheet

def get_protocol_id(key):
    return f"{key.split('.')[0]}.protocol_core.protocol_id"

def get_tab_value(key):
    return key.split('.')[0].replace("_"," ").capitalize()

def map_key_to_id(key, wrangled_spreadsheet, key_to_id=True):
    tab_value = get_tab_value(key)
    id_key = get_protocol_id(key)

    df_key_id = wrangled_spreadsheet[tab_value][[key, id_key]]
    if df_key_id.duplicated(key).any():
        print(f"Could not distinguish multiple protocols based on {key}. Will assign the first one.\n{df_key_id}")
        df_key_id.drop_duplicates(subset=key, keep='first')
    if key_to_id:
        return {row[key]: row[id_key] for i, row in df_key_id.iterrows()}
    return {row[id_key]: row[key] for i, row in df_key_id.iterrows()}

def get_files_per_library(seq_tab):
    return seq_tab.groupby(LAST_BIOMATERIAL)['sequence_file.file_core.file_name'].nunique()

def check_10x_n_files(wrangled_spreadsheet):
    """Check validity of spreadsheet with basic checks"""
    lib_key = 'library_preparation_protocol.library_construction_method.text'
    lib_id = get_protocol_id(lib_key)
    libs_dict = map_key_to_id(lib_key, wrangled_spreadsheet, key_to_id=False)
    for key, value in libs_dict.items():
        indx_values = wrangled_spreadsheet['Sequence file'][lib_id] == key
        if '10x' not in value or not any(indx_values):
            continue
        n_per_lib = get_files_per_library(wrangled_spreadsheet['Sequence file'][indx_values])
        if any(n_per_lib < 2):
            raise ValueError("10x fastqs should include at least 2 read files per read")

def perform_checks(wrangled_spreadsheet):
    check_10x_n_files(wrangled_spreadsheet)
    # if wrangled_spreadsheet['fastq']['biomaterials'] not in wrangled_spreadsheet['biomaterials']['id']:
    #     raise KeyError("IDs in sequence file tab, are not listed in biomaterial tab")

def main():
    parser = define_parse()
    args = parser.parse_args()

    file_manifest = open_spreadsheet(spreadsheet_path=args.file_manifest, tab_name="File_manifest")
    wrangled_spreadsheet = open_spreadsheet(args.wrangled_spreadsheet)
    if 'Sequence file' in wrangled_spreadsheet:
        del wrangled_spreadsheet['Sequence file']
    tier1_spreadsheet = open_spreadsheet(args.tier1_spreadsheet)
    tier1_spreadsheet = flatten_tier1(tier1_spreadsheet)

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