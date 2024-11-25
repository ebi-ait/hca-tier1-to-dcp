# Description of report json structure
# TODO: ADD EXPLANATION
```json
{
    "ids": {
        "n":{
            "donor_organism": {
                "tier1": 1,
                "wrangled": 1
            },
            "specimen_from_organism": {
                "tier1": 3,
                "wrangled": 3
            }
        },
        "values": {
            "donor_organism":{
                "tier1": [
                    "D1"
                ],
                "wrangled": [
                    "D1"
                ]
            },
            "specimen_from_organism":{
                "tier1": [
                    "S1",
                    "S2",
                    "S3"
                ],
                "wrangled": [
                    "S1",
                    "S2",
                    "S3"
                ]
            }
        }
    },
    "tabs":{
        "excess": {
            "tier1": [],
            "wrangled": [
                "Project - Contributors",
                "Dissociation protocol"
            ]
        },
        "n":{
            "tier1": 11,
            "wranlged": 16
        },
        "intersect":[
            "Project",
            "Donor organism",
            "Specimen from organism"
        ]
    },
    "values":
    {
        "Donor organism": {
            "excess": {
                "tier1": [],
                "wrang": [
                    "donor_organism.biomaterial_core.biomaterial_name",
                    "donor_organism.biomaterial_core.biomaterial_description"
                ]
            },
            "intersect": [
                "donor_organism.biomaterial_core.biomaterial_id",
                "donor_organism.biomaterial_core.ncbi_taxon_id",
                "donor_organism.sex",
                "donor_organism.is_living",
                "donor_organism.development_stage.text",
                "donor_organism.development_stage.ontology",
                "donor_organism.development_stage.ontology_label"
            ],
            "values_diff": {
                "donor_organism.development_stage.text": {
                    "D1": {
                        "tier1": "25-year-old stage",
                        "wrangled": "adult"
                    }
                },
                "donor_organism.development_stage.ontology": {
                    "D1":
                    {
                        "tier1": "HsapDv:0000119",
                        "wrangled": "EFO:0001272"
                    }
                },
                "donor_organism.development_stage.ontology_label": {
                    "D1": {
                        "tier1": "25-year-old stage",
                        "wrangled": "adult"
                    }
                }
            }
        },
        "Specimen from organism": {
            "excess": {
                "tier1": [
                    "specimen_from_organism.transplant_organ",
                    "specimen_from_organism.preservation_storage.storage_method"
                ],
                "wrang": [
                    "specimen_from_organism.biomaterial_core.biomaterial_name",
                    "specimen_from_organism.biomaterial_core.biomaterial_description",
                    "specimen_from_organism.organ_parts.text",
                    "specimen_from_organism.organ_parts.ontology",
                    "specimen_from_organism.organ_parts.ontology_label"
                ]
            },
            "intersect": [
                "specimen_from_organism.biomaterial_core.biomaterial_id",
                "specimen_from_organism.biomaterial_core.ncbi_taxon_id",
                "specimen_from_organism.organ.text",
                "specimen_from_organism.organ.ontology",
                "specimen_from_organism.organ.ontology_label"
            ],
            "values_diff": {
                "specimen_from_organism.organ.text": {
                    "S1": {
                        "tier1": "zone of skin",
                        "wrangled": "skin"
                    },
                    "S2": {
                        "tier1": "zone of skin",
                        "wrangled": "skin"
                    },
                    "S3": {
                        "tier1": "zone of skin",
                        "wrangled": "skin"
                    }
                },
                "specimen_from_organism.organ.ontology":{
                    "S1": {
                        "tier1": "UBERON:0000014",
                        "wrangled": "UBERON:0002097"
                    },
                    "S2":
                    {
                        "tier1": "UBERON:0000014",
                        "wrangled": "UBERON:0002097"
                    },
                    "S3": {
                        "tier1": "UBERON:0000014",
                        "wrangled": "UBERON:0002097"
                    }
                },
                "specimen_from_organism.organ.ontology_label": {
                    "S1": {
                        "tier1": "zone of skin",
                        "wrangled": "skin of body"
                    },
                    "S2": {
                        "tier1": "zone of skin",
                        "wrangled": "skin of body"
                    }, 
                    "S3": {
                        "tier1": "zone of skin",
                        "wrangled": "skin of body"
                    }
                }
            }
        }
    }
```