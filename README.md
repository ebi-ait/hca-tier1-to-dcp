# HCA - Tier 1 to DCP
Convert Human Cell Atlas Tier 1 metadata extracted out of an anndata object of a published CELLxGENE dataset,into [HCA DCP metadata schema](https://github.com/HumanCellAtlas/metadata-schema/tree/master/json_schema) ingestible [spreadsheet](https://github.com/ebi-ait/geo_to_hca/tree/master/template).

## Algorithm
This convertion is done in 3 steps.
1. Pull data from CxG [cellxgene_metadata_collection.py](cellxgene_metadata_collection.py)
    1. Given a collection_id
    1. Select dataset
    1. Download h5ad
    1. Pull obs layer into a csv file in `metadata` dir to `<collection_id>_<dataset_id>_metadata.csv` filename
    1. Pull uns layer into a csv file in `metadata` dir to `<collection_id>_<dataset_id>_study_metadata.csv` filename
    1. Test if DOI exists in [ingest](https://contribute.data.humancellatlas.org/) (ingest-token required)
1. Convert to DCP spreadsheet [convert_to_dcp.py](convert_to_dcp.py)
    1. Given a collection_id & dataset_id pull metadata from metadata dir (optional if single dataset per collection exists in dir)
    1. Download latest hca_template.xlsx from [ebi-ait/geo_to_hca](https://github.com/ebi-ait/geo_to_hca/raw/master/template/hca_template.xlsx), using the [mapping](tier1_mapping.py) the spreadsheet fields are renamed & converted to dcp metadata
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
python3 cellxgene_metadata_collection.py -c <CxG collection_id> -t <ingest-token>
python3 convert_to_dcp.py -c <CxG collection_id> -d <CxG dataset_id>
python3 compare_with_dcp.py -c <CxG collection_id> -d <CxG dataset_id> -w <previously wrangled spreadsheet path>
```

### Arguments
- `--collection_id` or `-c`: CxG collection_id of the project. 
    - i.e. `e5f58829-1a66-40b5-a624-9046778e74f5`
- `--wrangled-path` or `-w`: Path of previously wrangled spreadsheet to compare with converted from tier 1 spreadsheet
    - i.e. `metadata/scAgingHumanMaleSkin_metadata_03-08-2023.xlsx`
- `--ingest-token` or `-t`: Token of ingest for collecting DOI info from [ingest](https://contribute.data.humancellatlas.org/)
- `--dataset` or `-d`: Select the CxG dataset_id to download and convert.
    - i.e. `6ec405bb-4727-4c6d-ab4e-01fe489af7ea`

| table with optional and req per script | 