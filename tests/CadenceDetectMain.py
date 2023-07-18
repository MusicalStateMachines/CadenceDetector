from src.cadence_detector.CadenceDetector import *
import tqdm
from functools import partial
import os
import time
import multiprocessing as mp

DownloadsPath = '/Users/matanba/Downloads/'
SearsHaydnPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
DCMLabMozartPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml'
DCMBeethovenPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/ABC_DCM/ABC/data/mxl'
MyPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
# for running on files not in database
TestPath = "/Users/matanba/Dropbox/PhD/CadencesResearch/TestData/"

# select analysis path
InputFilePath = DCMBeethovenPath
OutputFilePath = MyPath if InputFilePath != TestPath else os.path.join(InputFilePath, "StateMachineData/")

# select files
# all files in path
XMLFileEnding = ".xml" if InputFilePath != DCMBeethovenPath else ".mxl"
# ===for testing haydn singe file
# XMLFileEnding = "op055_no02_mv02.xml"
# ===for testing mozart single file
# XMLFileEnding = "331-1.xml"
# XMLFileEnding = "279-2.xml"
# ===for testing beethoven single file
# XMLFileEnding = "op18_no1_mov2.xml"
# ===for testing a single file not in database
# XMLFileEnding = "al_p69_1_1-82.mxl"
# multi-core processing
DoParallelProcessing = XMLFileEnding in ['.xml', '.mxl']



os.makedirs(OutputFilePath, exist_ok=True)
TextFileEnding = ".txt"

# Global Settings
ReadKeyFromSears = 0
RunKeyDetection = 1
SetConstantKey = 'a'
RunCadenceDetection = 1
OnlyGetNumMeasures = False
# Cadence Detector Tunable Parameters
MaxNumMeasures = 500
MinInitialMeasures = 3
MinPostCadenceMeasuresDict = {SearsHaydnPath: 2, DCMLabMozartPath: 0, DCMBeethovenPath: 0, TestPath: 3}
MinPostCadenceMeasures = MinPostCadenceMeasuresDict[InputFilePath]
KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothingCadenceSensitive
KeyDetectionBlockSize = 4 # in measures
KeyDetectionOverlap = 1 / KeyDetectionBlockSize  # ratio from block size, this creates an step size of 1 measure
KeyDetectionLookAhead = 0.5 # percentage from block size
KeyDetectionForgetFactor = 0.8
ReenforcementFactorsDict = {SearsHaydnPath: {'PAC': 2, 'IAC': 1, 'HC': 2},
                            DCMLabMozartPath: {'PAC': 3, 'IAC': 1, 'HC': 3/2},
                            DCMBeethovenPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2},
                            TestPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2}}
ReenforcementFactors = ReenforcementFactorsDict[InputFilePath]


def findCadencesInFile(file, only_get_num_measures = False):
    try:
        if file.endswith(XMLFileEnding):
            # define path
            FullPath = os.path.join(InputFilePath, file)
            print(f"Analyzing {FullPath}")
            # init detector class
            CD = CadenceDetector(maxNumMeasures=MaxNumMeasures,
                                 minInitialMeasures=MinInitialMeasures,
                                 minPostCadenceMeasures=MinPostCadenceMeasures,
                                 keyDetectionMode=KeyDetectionMode,
                                 keyDetectionLookahead=KeyDetectionLookAhead,
                                 keyDetectionForgetFactor=KeyDetectionForgetFactor,
                                 reinforcementFactors=ReenforcementFactors,
                                 keyDetectionBlockSize=KeyDetectionBlockSize,
                                 keyDetectionOverlap=KeyDetectionOverlap)
            if only_get_num_measures:
                CD.loadFileAndGetMeasures(FullPath)
            else:
                # load file to detector
                CD.loadFile(FullPath)
                # set files
                CD.setFileName(file)
                CD.setWritePath(OutputFilePath)
                # detect key per measure
                if ReadKeyFromSears:
                    CD.getKeyPerMeasureFromSearsFile(FullPath)
                    CD.writeKeyPerMeasureToFile()
                elif RunKeyDetection:
                    CD.detectKeyPerMeasure()
                    CD.writeKeyPerMeasureToFile()
                else:
                    CD.setConstantKeyPerMeasure(SetConstantKey)
                if RunCadenceDetection:
                    # read from file
                    CD.readKeyPerMeasureFromFile()
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