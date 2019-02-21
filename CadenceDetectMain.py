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

SearsPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/5387755/'
FileEnding = ".xml"

MyPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/ResultsAndFiles/'

TotalNumMeasures = 0

import os
for file in os.listdir(SearsPath):
    if file.endswith(FileEnding):
        #define path
        FullPath = os.path.join(SearsPath, file)
        print(f"Analyzing {FullPath}")
        #init detector class
        CD = CadenceDetector()
        #load file to detector
        CD.loadFile(FullPath)
        TotalNumMeasures = TotalNumMeasures + CD.getNumMeasures()
        continue
        #set files
        CD.setFileName(file)
        CD.setWritePath(MyPath)
        #CD.loadMusic21Corpus(music21file)
        #define params
        blockSize = 8 #in measures
        overlap = 1/blockSize #ratio from block size
        #detect key per measure
        CD.detectKeyPerMeasure(blockSize,overlap)
        #detect cadences per key
        CD.detectCadences()
        try:
            CD.writeAnalyzedFile()
        except:
            print('error: could not write file')
        #display
        #CD.displayFull()

print(TotalNumMeasures)