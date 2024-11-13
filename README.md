# HCA - Tier 1 to DCP
Convert Human Cell Atlas Tier 1 metadata extracted out of an anndata object of a published CELLxGENE dataset,into [HCA DCP metadata schema](https://github.com/HumanCellAtlas/metadata-schema/tree/master/json_schema) ingestible [spreadsheet](https://github.com/ebi-ait/geo_to_hca/tree/master/template).

# Todo
- [ ] fix title in excel
- [ ] fill ontologised field from ontology_id (or text in collection)
- [ ] fill library prep based on cheatsheet for 10x & smartseq
- [ ] fix analysis_file `nan`s
- [ ] pull doi info from crossref api
- [ ] add process specific fields
- [ ] if multiple collapse with double pipe