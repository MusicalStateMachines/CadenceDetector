from CadenceDetector import *
from music21 import *
DownloadsPath = '/Users/matanba/Downloads/'
SearsHaydnPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
DCMLabMozartPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml'
BeethovenPath = '/Users/matanba/Downloads/'
MyPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
#SearsPath = '/Users/matanba/Dropbox/PhD/AlignMidi/alignmidi/'
XMLFileEnding = ".xml"

InputFilePath = SearsHaydnPath
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
DoParallelProcessing = 1
OnlyGetNumMeasures = False
# Tunable Parameters
KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothingCadenceSensitive
KeyDetectionBlockSizes = {SearsHaydnPath: 4, DCMLabMozartPath: 4, BeethovenPath: 4} # in measures
KeyDetectionBlockSize = KeyDetectionBlockSizes[InputFilePath]
KeyDetectionForgetFactor = 0.8
ReenforcementFactorsDict = {SearsHaydnPath: {'PAC': 3/2, 'IAC': 1, 'HC': 5/4},
                            DCMLabMozartPath: {'PAC': 2, 'IAC': 1, 'HC': 5/4},
                            BeethovenPath: {'PAC': 3/2, 'IAC': 1, 'HC': 5/4}}
ReenforcementFactors = ReenforcementFactorsDict[InputFilePath]

import os
import time
import multiprocessing as mp

def findCadencesInFile(file, only_get_num_measures = False):
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
                except:
                    print('error: could not write file')
        return CD.NumMeasures
        #display
        #CD.displayFull()


if __name__ == '__main__':
    fileList = sorted(os.listdir(InputFilePath))
    start = time.time()
    if DoParallelProcessing:
        print("Parallel Processing On")
        print("Number of processors: ", mp.cpu_count())
        pool = mp.Pool(mp.cpu_count())
        pool.map_async(findCadencesInFile, [file for file in fileList]).get()
        pool.close()
    else:
        print("Parallel Processing Off")
        total_num_measures = 0
        for file in fileList:
            curr_num_measures = findCadencesInFile(file, only_get_num_measures=OnlyGetNumMeasures)
            if curr_num_measures is not None:
                total_num_measures = total_num_measures + curr_num_measures
        print("Total Num Measures:", total_num_measures)

    end = time.time()
    total_time = end - start
    print("Elapsed time", total_time/60, "minutes")