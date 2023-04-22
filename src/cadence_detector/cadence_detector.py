from .CadenceDetector import *
import tqdm
from functools import partial
import os
import time
import multiprocessing as mp

def detect_cadences_in_file(full_path="", output_path=None):
    if not os.path.exists(full_path):
        print(f"file {full_path} not found")
        return
    CD = CadenceDetector()
    CD.loadFile(full_path)
    input_file_path, input_file_name = os.path.split(full_path)
    CD.setFileName(input_file_name)
    if output_path is None:
        output_path = input_file_path
    CD.setWritePath(output_path)
    CD.detectKeyPerMeasure()
    CD.writeKeyPerMeasureToFile()
    CD.readKeyPerMeasureFromFile()
    CD.detectCadences()
    try:
        CD.writeAnalyzedFile()
    except Exception as e:
        print('error: could not write file:', e)
    print(f"Analysis for {full_path} done.")
    return {'file': input_file_name, 'num_measures': CD.NumMeasures}


def detect_cadences_in_folder(input_dir="", file_ending=".xml", output_dir=None, do_parallel=True):
    fileList = sorted(os.listdir(input_dir))
    full_list = [os.path.join(input_dir, file) for file in fileList if file.endswith(file_ending)]
    start = time.time()
    num_measures_per_mov = []
    if output_dir is None:
        output_dir = input_dir
    if do_parallel:
        print("Parallel Processing On")
        print("Number of processors: ", mp.cpu_count())
        with mp.Pool() as pool:
            num_measures_per_mov = list(tqdm.tqdm(pool.imap_unordered(partial(detect_cadences_in_file, output_path=output_dir), full_list), total=len(full_list)))
        total_num_measures = sum([curr_tup['num_measures'] for curr_tup in num_measures_per_mov])
    else:
        print("Parallel Processing Off")
        total_num_measures = 0
        for file in tqdm.tqdm(full_list):
            num_measures_per_mov = detect_cadences_in_file(file, output_path=output_dir)
            if num_measures_per_mov is not None:
                total_num_measures = total_num_measures + num_measures_per_mov['num_measures']
    if num_measures_per_mov:
        for curr_mov in num_measures_per_mov:
            print(curr_mov)
        print("Total Num Measures:", total_num_measures)

    end = time.time()
    total_time = end - start
    print("Elapsed time", total_time/60, "minutes")
