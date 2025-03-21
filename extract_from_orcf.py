import os
import pandas as pd
import convert_to_dcp

def to_uuid(filename):
    return '-'.join([filename[0:8], filename[8:12], filename[12:16], filename[16:20], filename[20:32]])

def clean_string(filename):
    return filename.replace("HCA_Tier 1 metadata_ORCF.xlsx","").replace(" ","").replace(".","").replace("_","")

def gen_uuid(filename):
    newf = clean_string(filename)
    newf = ("0" * (32 - len(newf)) + newf) if len(newf) < 32 else newf[:32]
    return to_uuid(newf)

def main(summary_filename):
    df_all = pd.read_csv(f'metadata/{summary_filename}', sep=',')
    for file in df_all['worksheet'].unique():
        df = df_all[df_all['worksheet'] == file].dropna(axis=1, how='all')
        file_uuid = gen_uuid(file)
        df.to_csv(f'metadata/{file_uuid}_{file_uuid}_metadata.csv', index=False)
        if os.path.exists(f'metadata/{file_uuid}_{file_uuid}_dcp.xlsx'):
            continue
        convert_to_dcp.main(collection_id=file_uuid,
                            dataset_id=file_uuid)

if '__main__' == __name__:
    main('perstudy/orcf_t1_all.csv')