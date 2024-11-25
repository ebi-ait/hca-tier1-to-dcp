# HCA - Tier 1 to DCP
Convert Human Cell Atlas Tier 1 metadata extracted out of an anndata object of a published CELLxGENE dataset,into [HCA DCP metadata schema](https://github.com/HumanCellAtlas/metadata-schema/tree/master/json_schema) ingestible [spreadsheet](https://github.com/ebi-ait/geo_to_hca/tree/master/template).

## Algorithm
This convertion is done in 3 steps.
1. Pull data from CxG [collect_cellxgene_metadata.py](collect_cellxgene_metadata.py)
    1. Given a collection_id, select dataset and download h5ad
    1. Pull obs and uns layer into csv files in `metadata` dir with `<collection_id>_<dataset_id>` prefix in `_metadata.csv` and `_study_metadata.csv` filenames
    1. Test if DOI exists in [ingest](https://contribute.data.humancellatlas.org/) (ingest-token required)
1. Convert to DCP spreadsheet [convert_to_dcp.py](convert_to_dcp.py)
    1. Given a collection_id & dataset_id pull metadata from metadata dir
    1. Based on [hca_template.xlsx](https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx), using the [mapping](tier1_mapping.py) convert to dcp flat metadata file with dcp programmatic fields
    1. Based on the field programmatic name, the dcp spreadsheet is populated
    1. Exported into an xlsx file in `metadata` dir to `<collection_id>_<dataset_id>_dcp.csv` filename
1. Compare previously wrangled spreadsheet vs tier 1 [compare_with_dcp.py](compare_with_dcp.py)
    1. Open cellxgene and previously wrangled DCP spreadsheet
    1. Compare number of tabs, use intersection
    1. On each common tab 
        1. Compare number of entites per tab
        1. Compare ids per tab, for intersection
        1. Compare values of entities with same IDs (except protocols)
    1. Export all comparison in a report json file in `report_compare` dir to `<collection_id>_<dataset_id>_compare.json` filename



## Usage
Tested in python3.9. To run scripts you can run:
```bash
python3 -m pip install -r requirements.txt
python3 collect_cellxgene_metadata.py -c <CxG collection_id> -t <ingest-token>
python3 convert_to_dcp.py -c <CxG collection_id> -d <CxG dataset_id>
python3 compare_with_dcp.py -c <CxG collection_id> -d <CxG dataset_id> -w <previously wrangled spreadsheet path>
```

### Arguments
- `--collection_id` or `-c`: CxG collection_id of the project. 
    - i.e. `c353707f-09a4-4f12-92a0-cb741e57e5f0`, `dc3a5256-5c39-4a21-ac0c-4ede3e7b2323`, `20eea6c8-9d64-42c9-9b6f-c11b5249e0e9`
- `--dataset` or `-d`: Select the CxG dataset_id to download and convert.
    - i.e. `124744b8-4681-474a-9894-683896122708`, `0bae7ebf-eb54-46a6-be9a-3461cecefa4c`, `2e9d2f32-4cfb-49b5-b990-cbf4c241214e`
- `--wrangled-path` or `-w`: Path of previously wrangled spreadsheet to compare with converted from tier 1 spreadsheet
    - i.e. [`metadata/scAgingHumanMaleSkin_metadata_03-08-2023.xlsx`](https://explore.data.humancellatlas.org/projects/10201832-7c73-4033-9b65-3ef13d81656a)
- `--ingest-token` or `-t`: Token of ingest for collecting DOI info from [ingest](https://contribute.data.humancellatlas.org/)
- `--local_template` or `-l`: Local instance of [hca_template.xlsx](https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx)

#### Requirement of arguments per script
| args | [collect](collect_cellxgene_metadata.py) | [convert](convert_to_dcp.py) | [compare](compare_with_dcp.py) |
| ---- | ---------- | ---------- | ---------- | 
| `--collection_id`, `-c` | required | required | required |
| `--dataset_id`, `-d` | optional | optional | optional | 
| `--wrangled_path`, `-w` | n/a | n/a | required |
| `--ingest_token`, `-t` | optional | n/a | n/a |
| `--local_template`, `-l` | n/a | optional | n/a | 
