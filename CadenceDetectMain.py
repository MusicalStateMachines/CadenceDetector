from CadenceDetector import *
from music21 import *
#music21file = 'k155'
DownloadsPath = '/Users/matanba/Downloads/'

#file = 'WA_Mozart_Marche_Turque_Turkish_March_fingered.mxl'
#file = 'Haydn_Cello_Concerto_C_Major_Piano_AccompanimentComplete.mxl'
#file = 'Sonata_in_G_Minor_HWV_360_Op._1_No._2_for_Viola__Piano_.mxl'
#file = 'Mozart-Piano_Sonata_in_A_Minor.mxl'
#file = 'Polonaise_W.A._Mozart.mxl'
#file = '[Free-scores.com]_bach-wilhelm-friedemann-menuet-113324-670.xml'
#file = 'Joseph_Haydn_-_String_quartet_-_Op._76_no.5_in_D_major_-_Movement_I.mxl'
#file = 'chopin_prelude_a.xml'
#file =  'string_quartet_1_1_(c)edwards_shifted.xml'
#file  = 'string_quartet_1_2_(c)edwards.xml'
#file = 'Schumann_Clara_-_6_Lieder_Op.13_No.1_-_Ich_stand_in_dunklen_Traumen.xml'
#file = 'Haydn_String_Quartet_Op._64__No._3_Mvmnt_1.mxl'
#file = 'Haydn_String_Quartet_Melody.mxl'
#file = 'haydn_string_quartet_33_2_(c)harfesoft.xml'
#file = 'mozart_chamber_music_502_(c)harfesoft.xml' - bad file ?

SearsHaydnPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
DCMLabMozartPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml'
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
ReadKeyFromSears = 1
RunKeyDetection = 0
DoParallelProcessing = 1
OnlyGetNumMeasures = False
KeyDetectionBlockSize = 4  # in measures
KeyDetectionForgetFactor = 0.9

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
                CD.writeKeyPerMeasureToFile()
            elif RunKeyDetection:
                CD.detectKeyPerMeasure3(KeyDetectionBlockSize, overlap, KeyDetectionForgetFactor)
                # write To file
                CD.writeKeyPerMeasureToFile()
            # read from file
            CD.readKeyPerMeasureFromFile()
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