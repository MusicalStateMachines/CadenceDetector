import tqdm
import multiprocessing as mp
from concurrent import futures
from functools import partial
import os
import subprocess
import random

def get_full_list_with_ending(root_dir, file_ending):
    full_list = [os.path.join(root_dir, subdir, file)
                 for subdir, dirs, files in os.walk(root_dir)
                 for file in files
                 if os.path.splitext(file)[-1] in file_ending]
    return full_list

def synthesize_file(midi_fp, wav_folder):
    try:
        midi_file = os.path.split(midi_fp)[-1]
        wav_fp = os.path.join(wav_folder, midi_file.replace('.mid','.wav').replace('.MID','.wav'))
        fls_path = 'fluidsynth' #r'C:\Program Files (x86)\fluidsynth-2.2.7-win10-x64\bin\fluidsynth.exe'
        sf_dir = r'C:\Program Files (x86)\fluidsynth-2.2.7-win10-x64\FluidR3_GM\soundfonts'
        sound_fonts = os.listdir(sf_dir)
        select = random.randint(0, len(sound_fonts)-1)
        reverb_on = random.randint(0, 1)
        chorus_on = random.randint(0, 1)
        sf_path = os.path.join(sf_dir, sound_fonts[select])
        cmd = f'"{fls_path}" -F "{wav_fp}" -g 0.5 -R {reverb_on} -C {chorus_on} "{sf_path}" "{midi_fp}"'
        subprocess.run(cmd)
    except Exception as e:
        print('failed file:', midi_fp, e)

def _main():
    root_dir_midi = r'C:\KeyDetectionDatabase\The_Magic_of_MIDI\MIDI_excerpts'
    wav_folder = r'C:\KeyDetectionDatabase\The_Magic_of_MIDI\WAV_excerpts'
    full_list = get_full_list_with_ending(root_dir_midi, ['.mid','.MID'])
    parallel = True
    if parallel:
        print("num processors: ", mp.cpu_count())
        with futures.ProcessPoolExecutor() as pool:
            tqdm.tqdm(pool.map(partial(synthesize_file, wav_folder=wav_folder), full_list), total=len(full_list))
    else:
        for file in tqdm.tqdm(full_list):
            synthesize_file(file, wav_folder=wav_folder)

if __name__ == "__main__":
    _main()