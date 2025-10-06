import re
from collections import defaultdict
from numpy import nan
import pandas as pd

from helper_files.constants.file_mapping import FASTQ_STANDARD_FIELDS
from helper_files.utils import open_spreadsheet
from helper_files.constants.tier1_mapping import KEY_COLS
from helper_files.constants.tier2_mapping import LUNG_DIGESTION, TIER2_MANUAL_FIX, TIER2_TO_DCP, TIER2_TO_DCP_UPDATE
from helper_files.constants.dcp_required import dcp_required_entities
from helper_files.convert import flatten_tiered_spreadsheet

LAST_BIOMATERIAL = 'cell_suspension.biomaterial_core.biomaterial_id'
def merge_file_manifest(wrangled_seq_tab, file_manifest, file_mapping_dictionary):
    """Merge file manifest tab into wrangled spreadsheet and return wrangled_spreadsheet"""
    file_manifest = file_manifest[file_mapping_dictionary.keys()].rename(columns=file_mapping_dictionary)
    wrangled_seq_tab = wrangled_seq_tab.merge(file_manifest, on='cell_suspension.biomaterial_core.biomaterial_id', how='left')
    return wrangled_seq_tab

def get_fastq_ext(row):
    for suffix in ['fastq.gz', 'fastq', 'fq.gz', 'fq']:
        if row.endswith(suffix):
            return suffix 
    raise KeyError(f'filename {row} does not have known extension [`fastq.gz`, `fastq`, `fq.gz`, `fq`] for fastq file.')

def add_standard_fields(wrangled_seq_tab, standard_values_dictionary):
    """Add standard fields like content description which for fastqs will always be DNA sequence"""
    if 'sequence_file.file_core.format' not in wrangled_seq_tab:
        wrangled_seq_tab['sequence_file.file_core.format'] = wrangled_seq_tab['sequence_file.file_core.file_name'].apply(get_fastq_ext)
    for key, value in standard_values_dictionary.items():
        wrangled_seq_tab[key] = value
    return wrangled_seq_tab


def add_tier1_fields(wrangled_spreadsheet, tier1_spreadsheet, tier1_to_file_dictionary):
    """Add info from tier1 into seq file tab."""
    if any(key not in tier1_spreadsheet for key in tier1_to_file_dictionary.keys()):
        raise KeyError(f'Did not find {[key for key in tier1_to_file_dictionary.keys() if key not in tier1_spreadsheet]} in tier 1 spreadsheet')
    tier1_mapped = tier1_spreadsheet[tier1_to_file_dictionary.keys()].rename(columns=tier1_to_file_dictionary)
    tier1_mapped = get_dcp_protocol_ids(tier1_mapped, wrangled_spreadsheet)
    wrangled_spreadsheet['Sequence file'] = merge_overlap(wrangled_spreadsheet['Sequence file'], tier1_mapped,
                                                    key=LAST_BIOMATERIAL, field_list=list(tier1_mapped.columns),
                                                    suffix='t1')
    return wrangled_spreadsheet['Sequence file']


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
        tier2_df[diss] = pd.Series([nan] * len(tier2_df), dtype="object")
    for i, row in tier2_df.iterrows():
        prot = row['protocol_tissue_dissociation']
        if pd.isna(prot):
            continue
        if prot not in lung_digest_dict:
            raise ValueError(f"Digestion protocol {prot} not in pre-defined enum. Should be under `protocol_tissue_dissociation`")
        for diss in all_diss_fields:
            tier2_df.loc[i, diss] = lung_digest_dict[prot].get(diss, nan)
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

def merge_overlap(wrangled_tab, tier2_fields, field_list, key, suffix = 't2'):
    merged_df = pd.merge(
            wrangled_tab,
            tier2_fields.drop_duplicates(),
            on=key, how='outer', suffixes=('', f'_{suffix}')
        )
    common_cols = set(wrangled_tab.columns) & set(field_list) - {key}
    for col in common_cols:
        merged_df[col] = merged_df[f"{col}_{suffix}"].combine_first(merged_df[col])
        merged_df = merged_df.drop([f"{col}_{suffix}"], axis=1)
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
        # TODO if protocol does not exist in wrangled, add it
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

def merge_tier2_with_flat_dcp(tier2_spreadsheet, dcp_flat, tier1_to_dcp):
    tier2_df = open_spreadsheet(tier2_spreadsheet)
    
    all_tier2 = {**TIER2_TO_DCP, **TIER2_TO_DCP_UPDATE}
    tier2_flat = flatten_tiered_spreadsheet(tier2_df, merge_type='outer')
    tier2_low_key = tier1_to_dcp[next(id for id in KEY_COLS if id in tier2_flat.columns)]
    tier2_flat = manual_fixes(tier2_flat)
    print(f'\nConverting {"; ".join([col for col in tier2_flat])} tier 2 values')
    tier2_flat = rename_tier2_columns(tier2_flat, all_tier2)
    dcp_flat = dcp_flat.merge(tier2_flat, how='outer', on=tier2_low_key, suffixes=('_dcp', ''))
    if dcp_flat.filter(like='_dcp').shape[1]:
        print(f"Conflicts between tier 1 and tier 2 for {'; '.join(dcp_flat.filter(like='_dcp').columns.tolist())}. Kept tier 2 values.")
    return dcp_flat.drop(columns=dcp_flat.filter(like='_dcp').columns, errors='ignore')

def merge_file_manifest_with_flat_dcp(dcp_flat, file_manifest, file_mapping_dictionary):
    file_manifest = open_spreadsheet(spreadsheet_path=file_manifest, tab_name="File_manifest")
    dcp_flat = merge_file_manifest(dcp_flat, file_manifest, file_mapping_dictionary)
    dcp_flat = add_standard_fields(dcp_flat, FASTQ_STANDARD_FIELDS)
    return dcp_flat