import pandas as pd
import json


def main():
    libs = ['TF', 'TORCH']

    for lib in libs:
        data = pd.read_csv(f'data/{lib}_RECORDS.csv',
                           delimiter=',', encoding='utf-8')
        for idx, row in data.iterrows():
            print(row['API'])
            api_ = {row['API'].split('(')[0]: row['API']}
            # data_list.append(api_)

            with open(f"API signatures/{lib}_API_table.json", "a") as json_file:
                json.dump(api_, json_file, indent=4)
                json_file.write(',')
                json_file.write('\n')


if __name__ == "__main__":
    main()
