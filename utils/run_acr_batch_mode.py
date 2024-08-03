import subprocess, os

def main():
    libname = 'pytorch'
    for root, dir, files in os.walk(f"dl_data/{libname}/"):
        for j, file in enumerate(files):
            print(f"@@@@@@@@@@@ I am working on {file}:: {j}/{len(files)}")
            current_file = os.path.join(root, file)
            hash_ = "_".join(current_file.split('_')[2:4])
            output_id = hash_.replace('.txt', f"_{j}")
            command_ = f"PYTHONPATH=. python app/main.py local-issue --output-dir output --model gpt-4o-mini --model-temperature 0.2 --task-id {output_id} --local-repo {libname} --issue-file {current_file}"
            subprocess.call(command_, shell=True)
            print('')
    

if __name__ == '__main__':
    main()