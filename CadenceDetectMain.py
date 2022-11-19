from CadenceDetector import *
from music21 import *
import tqdm
from functools import partial
DownloadsPath = '/Users/matanba/Downloads/'
SearsHaydnPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
DCMLabMozartPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml'
DCMBeethovenPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/ABC_DCM/ABC/data/mxl'
MyPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
#SearsPath = '/Users/matanba/Dropbox/PhD/AlignMidi/alignmidi/'
# haydn singe file
XMLFileEnding = "op050_no06_mv02.xml"
# mozart single file
#XMLFileEnding = "284-3.xml"
# beethoven single file
#XMLFileEnding = "op18_no1_mov2.mxl"
# all files
XMLFileEnding = ".xml"
# multi-core processing
DoParallelProcessing = 1
# select analysis path
InputFilePath = DCMLabMozartPath
OutputFilePath = MyPath

#===for testing a single file not in database
#TestPath = "/Users/matanba/Dropbox/PhD/CadencesResearch/TestData/"
#XMLFileEnding = "son333_1.mxl"
#InputFilePath = TestPath
#OutputFilePath = os.path.join(InputFilePath, "StateMachineData/")

os.makedirs(OutputFilePath, exist_ok=True)
TextFileEnding = ".txt"

# Global Settings
ReadKeyFromSears = 0
RunKeyDetection = 1
RunCadenceDetection = 1
OnlyGetNumMeasures = False
# Tunable Parameters
KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothingCadenceSensitive
KeyDetectionBlockSizes = {SearsHaydnPath: 4, DCMLabMozartPath: 4, DCMBeethovenPath: 4} # in measures
KeyDetectionBlockSize = KeyDetectionBlockSizes[InputFilePath]
KeyDetectionForgetFactor = 0.8
ReenforcementFactorsDict = {SearsHaydnPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2},
                            DCMLabMozartPath: {'PAC': 3, 'IAC': 1, 'HC': 3/2},
                            DCMBeethovenPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2}}
ReenforcementFactors = ReenforcementFactorsDict[InputFilePath]

import os
import time
import multiprocessing as mp

def findCadencesInFile(file, only_get_num_measures = False):
    try:
        if file.endswith(XMLFileEnding):
            # define path
            FullPath = os.path.join(InputFilePath, file)
            print(f"Analyzing {FullPath}")
            # init detector class
            CD = CadenceDetector()
            CD.KeyDetectionMode = KeyDetectionMode
            CD.KeyDetectionForgetFactor = KeyDetectionForgetFactor
            CD.ReenforcementFactors = ReenforcementFactors
            if only_get_num_measures:
                CD.loadFileAndGetMeasures(FullPath)
            else:
                # load file to detector
                CD.loadFile(FullPath)
                # set files
                CD.setFileName(file)
                CD.setWritePath(OutputFilePath)
                # CD.loadMusic21Corpus(music21file)
                overlap = 1 / KeyDetectionBlockSize  # ratio from block size, this creates an step size of 1 measure
                # detect key per measure
                if ReadKeyFromSears:
                    CD.getKeyPerMeasureFromSearsFile(FullPath)
                    CD.writeKeyPerMeasureToFile(KeyDetectionMode)
                elif RunKeyDetection:
                    CD.detectKeyPerMeasureWrapper(KeyDetectionBlockSize, overlap)
                    # write To file
                    CD.writeKeyPerMeasureToFile(KeyDetectionMode)
                if RunCadenceDetection:
                    # read from file
                    CD.readKeyPerMeasureFromFile(KeyDetectionMode)
                    # detect cadences per key
                    CD.detectCadences()
                    try:
                        CD.writeAnalyzedFile()
                    except Exception as e:
                        print('error: could not write file:', e)
            return {'file': file, 'num_measures': CD.NumMeasures}
            #display
            #CD.displayFull()
    except Exception as e:
        print(f"Exception while processing file: {file}")
        raise


if __name__ == '__main__':
    fileList = sorted(os.listdir(InputFilePath))
    full_list = [file for file in fileList if file.endswith(XMLFileEnding)]
    start = time.time()
    num_measures_per_mov = []
    if DoParallelProcessing:
        print("Parallel Processing On")
        print("Number of processors: ", mp.cpu_count())
        with mp.Pool() as pool:
            num_measures_per_mov = list(tqdm.tqdm(pool.imap_unordered(partial(findCadencesInFile, only_get_num_measures=OnlyGetNumMeasures), full_list), total=len(full_list)))
        total_num_measures = sum([curr_tup['num_measures'] for curr_tup in num_measures_per_mov])
    else:
        print("Parallel Processing Off")
        total_num_measures = 0
        for file in tqdm.tqdm(full_list):
            num_measures_per_mov = findCadencesInFile(file, only_get_num_measures=OnlyGetNumMeasures)
            if num_measures_per_mov is not None:
                total_num_measures = total_num_measures + num_measures_per_mov['num_measures']
    if num_measures_per_mov:
        for curr_mov in num_measures_per_mov:
            print(curr_mov)
        print("Total Num Measures:", total_num_measures)

    end = time.time()
    total_time = end - start
    print("Elapsed time", total_time/60, "minutes")