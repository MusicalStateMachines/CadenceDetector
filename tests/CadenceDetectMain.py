from src.cadence_detector.CadenceDetector import *
import tqdm
from functools import partial
import os
import time
import multiprocessing as mp

HomeDir = os.path.expanduser("~") if os.name != 'nt' else os.environ['USERPROFILE']
DownloadsPath = os.path.join(HomeDir,'Downloads')
BachWTCPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/BachWTC/mxl')
SearsHaydnPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/SearsData')
DCMLabMozartPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml')
DCMBeethovenPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/ABC_DCM/ABC/data/mxl')
MyPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/StateMachineData')
# for running on files not in database
TestPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/TestData')

# select analysis path
InputFilePath = SearsHaydnPath
OutputFilePath = MyPath if InputFilePath != TestPath else os.path.join(InputFilePath, "StateMachineData/")

OutputSubPaths = {BachWTCPath: "BachWTC", SearsHaydnPath: "SearsHaydn", DCMLabMozartPath: "DCMLabMozart", DCMBeethovenPath: "DCMLabBeethoven", TestPath: "Misc"}
OutputFilePath = os.path.join(OutputFilePath, OutputSubPaths[InputFilePath])

XMLFileEndings = {BachWTCPath: ".mxl", SearsHaydnPath: ".xml", DCMLabMozartPath: ".xml", DCMBeethovenPath: ".mxl", TestPath: ".xml"}
# select files
# all files in path
XMLFileEnding = XMLFileEndings[InputFilePath]
# ===for testing haydn singe file
XMLFileEnding = "op020_no04_mv01.xml"
# ===for testing mozart single file
# XMLFileEnding = "576-2.xml"
# XMLFileEnding = "279-2.xml"
# ===for testing beethoven single file
# XMLFileEnding = "op18_no1_mov2.xml"
# ===for testing bach single file
# XMLFileEnding = "BWV_0858b.mxl"
# ===for testing a single file not in database
# XMLFileEnding = "al_p69_1_1-82.mxl"
# multi-core processing
DoParallelProcessing = XMLFileEnding in ['.xml', '.mxl', '.mid']



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
MinPostCadenceMeasuresDict = {BachWTCPath: 2, SearsHaydnPath: 2, DCMLabMozartPath: 0, DCMBeethovenPath: 0, TestPath: 3}
MinPostCadenceMeasures = MinPostCadenceMeasuresDict[InputFilePath]
KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothingCadenceSensitive
KeyDetectionBlockSizes = {BachWTCPath: 1, SearsHaydnPath: 4, DCMLabMozartPath: 4, DCMBeethovenPath: 4, TestPath: 4}
KeyDetectionBlockSize = KeyDetectionBlockSizes[InputFilePath] # in measures
KeyDetectionOverlap = 1 / KeyDetectionBlockSize  # ratio from block size, this creates an step size of 1 measure
KeyDetectionLookAhead = 0.5 # percentage from block size
KeyDetectionForgetFactors = {BachWTCPath: 0.9, SearsHaydnPath: 0.8, DCMLabMozartPath: 0.8, DCMBeethovenPath: 0.8, TestPath: 0.8}
KeyDetectionForgetFactor = KeyDetectionForgetFactors[InputFilePath]
ReenforcementFactorsDict = {BachWTCPath: {'PAC': 3, 'IAC': 1, 'HC': 1},
                            SearsHaydnPath: {'PAC': 2, 'IAC': 1, 'HC': 2},
                            DCMLabMozartPath: {'PAC': 3, 'IAC': 1, 'HC': 3/2},
                            DCMBeethovenPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2},
                            TestPath: {'PAC': 2, 'IAC': 1, 'HC': 3/2}}
ReenforcementFactors = ReenforcementFactorsDict[InputFilePath]
CompletePickupFormats = {BachWTCPath: False, SearsHaydnPath: True, DCMLabMozartPath: False, DCMBeethovenPath: False, TestPath: False}
CompletePickupFormat = CompletePickupFormats[InputFilePath]
RevertReboundPerData = {BachWTCPath: False, SearsHaydnPath: True, DCMLabMozartPath: True, DCMBeethovenPath: True, TestPath: True}
RevertRebounds = RevertReboundPerData[InputFilePath]
BeatStrengthsForGrouping = {BachWTCPath: 0.5, SearsHaydnPath: 1.0, DCMLabMozartPath: 1.0, DCMBeethovenPath: 1.0, TestPath: 1.0}
BeatStrengthForGrouping = BeatStrengthsForGrouping[InputFilePath]
IncludePicardys = {BachWTCPath: True, SearsHaydnPath: False, DCMLabMozartPath: False, DCMBeethovenPath: False, TestPath: False}
IncludePicardy = IncludePicardys[InputFilePath]
WeightedKeyInterps = {BachWTCPath: True, SearsHaydnPath: False, DCMLabMozartPath: False, DCMBeethovenPath: False, TestPath: False}
WeightedKeyInterp = WeightedKeyInterps[InputFilePath]

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
                                 keyDetectionOverlap=KeyDetectionOverlap,
                                 completePickupFormat=CompletePickupFormat,
                                 revertRebounds=RevertRebounds,
                                 beatStrengthForGrouping=BeatStrengthForGrouping,
                                 includePicardy=IncludePicardy,
                                 weightedKeyInterp=WeightedKeyInterp)
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