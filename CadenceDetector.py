from CadenceDetectStateMachine import *
from music21 import *
from collections import Counter
import math
import os
import numpy
import pickle
import enum
import copy

class CadenceDetector:
    HarmonicStateMachine = CDStateMachine()
    NoteStream = []
    ChordStream = []
    KeyPerMeasure = []
    NumMeasures = 0
    blockSize = 0
    overlap = 0
    fileName = 0
    hasPickupMeasure = 0
    WritePath = 0


    def __init__(self):
        self.HarmonicStateMachine = CDStateMachine()
        self.NoteStream = []
        self.NoteStreamRestless = []
        self.ChordStream = []
        self.ChordStreamRestless = []
        self.KeyPerMeasure = []
        self.OptionalKeysPerMeasure = [[]]
        self.NumMeasures = 0
        self.blockSize = 0
        self.overlap = 0

    def loadMusic21Corpus(self,fileString):
        self.NoteStream = corpus.parse(fileString)
        self.analyze()

    def loadFile(self,fileString):
        print("Loading score...")
        self.NoteStream = converter.parse(fileString)
        self.analyze()

    def analyze(self):
        self.removePickupMeasure()
        try:
            self.ChordStream = self.NoteStream.chordify(addPartIdAsGroup=True)
            self.HarmonicStateMachine.CheckBassPartFromChord = True
        except:
            print("Cannot add parts to chords!!")
            self.ChordStream = self.NoteStream.chordify()
            self.HarmonicStateMachine.CheckBassPartFromChord = False


        self.NumMeasures = len(self.ChordStream.recurse().getElementsByClass('Measure'))
        self.NumMeasures = min(self.NumMeasures,MaxNumMeasures)
        self.NoteStreamRestless = copy.deepcopy(self.NoteStream)  #create new list so as not to alter the original stream
        self.replaceBassRestsWithPrevs()
        if self.HarmonicStateMachine.CheckBassPartFromChord==True:
            self.ChordStreamRestless = self.NoteStreamRestless.chordify(addPartIdAsGroup=True)
        else:
            self.ChordStreamRestless = self.NoteStreamRestless.chordify()

    def removePickupMeasure(self):
        Parts = self.NoteStream.getElementsByClass(stream.Part)
        self.hasPickupMeasure = 1
        for part in Parts:
            if not part.flat.notesAndRests[0].isRest:
                self.hasPickupMeasure = 0
                print("Pickup Cancelled")
                break

    def replaceBassRestsWithPrevs(self):

        p=0
        for curr_part in self.NoteStreamRestless.recurse().getElementsByClass(stream.Part):
            if not p==3:#bass only, assuming bass is p=3
                p=p+1
                continue

            for curr_measure in curr_part.recurse().getElementsByClass(stream.Measure):
                prev_note = []  # should we complete bass between measures ???
                measure_modifcations_list = []
                #find rest and create modifications
                for curr_item in curr_measure.recurse().getElementsByClass(note.GeneralNote):
                    if prev_note:
                        if curr_item.isRest:
                            noteFromRest = self.noteFromRestWithPitch(curr_item, prev_note.pitch)
                            measure_modifcations_list.append([curr_item,noteFromRest])
                        else:
                            prev_note = curr_item
                    elif not curr_item.isRest:
                        prev_note = curr_item
                #make modifications to measure
                for curr_mod in measure_modifcations_list:
                    curr_measure.replace(curr_mod[0],curr_mod[1])

            #overwriting part ID for later cadence detection, because some files cannot be trusted for this metadata
            curr_part.id = 'MyCello'

        #self.NoteStreamRestless.show()

    def noteFromRestWithPitch(self,rest,pitch):
        noteFromRest = note.Note(pitch)
        noteFromRest.duration = rest.duration
        noteFromRest.offset = rest.offset
        noteFromRest.quarterLength = rest.quarterLength
        return noteFromRest

    def getNumMeasures(self):
        return self.NumMeasures

    def detectKeyPerMeasure(self,blockSize,overlap):
        print("Detecting key per block...")
        self.blockSize = blockSize
        self.overlap = overlap
        stepSize = math.ceil(self.blockSize * self.overlap)
        print("Num Measures:",self.NumMeasures)
        CorrCoefs =[]
        for currBlock in range(1,self.NumMeasures+stepSize-1,stepSize):
            StopMeasure = min(currBlock + self.blockSize - 1,self.NumMeasures)
            if StopMeasure<currBlock:
                break
            CurrMeasures = self.ChordStream.measures(currBlock, StopMeasure)
            #print(currBlock, StopMeasure)
            Key = CurrMeasures.analyze('key')
            #print(Key)
            #print(Key.correlationCoefficient)
            CorrCoefs.append(Key.correlationCoefficient)
            iMeasure = currBlock-1
            for thisMeasure in CurrMeasures:
                #adding the keys as a multiple of the correlation coef to get more accurate statistics
                for nCounts in range(1,math.ceil(Key.correlationCoefficient*10)):
                    if iMeasure >= len(self.OptionalKeysPerMeasure):
                        self.OptionalKeysPerMeasure.append([Key])#if this is the first key anlaysis realted to this measure, append it as new list
                    else:
                        self.OptionalKeysPerMeasure[iMeasure].append(Key)#otherwise append it to existing list
                iMeasure = iMeasure + 1

            #write this Key for entire block - Fix for overlapping
            # for thisChord in CurrMeasures.recurse().getElementsByClass('Chord'):
            #     thisChord.extend(Key)

        print("Mean CorrCoef: ",numpy.mean(CorrCoefs))
        #loop thru optional keys per measure and determine key by highset distribution

        for currMeasure in range(0,self.NumMeasures):
            currOptionalKeys = self.OptionalKeysPerMeasure[currMeasure]
            key_counts = Counter(currOptionalKeys)
            mostCommonKey = key_counts.most_common(1)[0][0]
            self.KeyPerMeasure.append(mostCommonKey)
            ####====debug with constant key
            #self.KeyPerMeasure.append(key.Key('D'))#akjshdgakdshg  - temp debug set constant key


    def writeKeyPerMeasureToFile(self):
        print("Writing keys to file...")
        keyfileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, keyfileName)
        KeyFile = f"{FullPath}_Key.txt"
        with open(KeyFile, 'wb') as f:
            pickle.dump(self.KeyPerMeasure, f)

    def readKeyPerMeasureFromFile(self):
        print("Reading keys from file...")
        keyfileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, keyfileName)
        KeyFile = f"{FullPath}_Key.txt"
        with open(KeyFile, 'rb') as f:
            self.KeyPerMeasure=pickle.load(f)

    def getKeyPerMeasureFromSearsFile(self,FullPath):
        FullPath = FullPath.replace(".xml", ".txt")

        class SearKeyDataIndices(enum.IntEnum):
            Key = 0
            Mode = 1
            StartBar = 2
            StartPulse = 3
            EndBar = 4
            EndPulse = 5

        with open(FullPath,'r') as f:
            lines = f.readlines()
            FoundRow = 0
            totalNumMeasures = 0
            startMeasure = 0
            endMeasure = -1
            for line in lines:
                if FoundRow==0:
                    if "Tonal Region" in line:
                        FoundRow = 1
                        continue
                else:
                    if "Major" in line or "Minor" in line:
                        elements = line.strip().split("\t")
                        currKey = self.mapSearsKeyToMusic21Key(elements[SearKeyDataIndices.Key],elements[SearKeyDataIndices.Mode])
                        print(elements, len(elements))
                        #print(line, file=text_file_reduced)
                        startMeasure = elements[SearKeyDataIndices.StartBar]

                        if "Begin" in startMeasure:
                            startMeasure = 1
                        else:
                            startMeasure = int(startMeasure)

                        # check if start measure is before prev end measure then there is an overlap in tonal regions (TBD - what to do with this?)
                        if startMeasure<=endMeasure:
                            startMeasure = endMeasure + 1

                        endMeasure = elements[SearKeyDataIndices.EndBar]
                        if "End" in endMeasure:
                            endMeasure = self.NumMeasures
                        else:
                            endMeasure = int(endMeasure)

                        numMeasuresToAppend = endMeasure-startMeasure+1 #including start and end

                        for i in range(numMeasuresToAppend):
                            self.KeyPerMeasure.append(currKey)

            print("KeysLen=", len(self.KeyPerMeasure))
            print("NumMeasures=",self.NumMeasures)

    def mapSearsKeyToMusic21Key(self,SearStringKey, SearStringMode):
        Music21StringKey = SearStringKey.replace("b","-")
        Music21StringMode = SearStringMode.replace("M","m")
        return key.Key(Music21StringKey,Music21StringMode)


    def detectCadences(self):
        print("Detecting cadences...")
        fileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, fileName)
        text_file = open(f"{FullPath}_Analyzed.txt", "w")
        text_fileOffsets = open(f"{FullPath}_Analyzed_OffsetsNums.txt", "w")

        measuresSecondsMap = list(filter(lambda d: d['durationSeconds'] > 0, self.ChordStreamRestless.secondsMap));

        for currMeasureIndex in range(0,self.NumMeasures):
            currKey = self.KeyPerMeasure[currMeasureIndex]#lists start with 0
            CurrMeasures = self.ChordStreamRestless.measures(currMeasureIndex+1,currMeasureIndex+1)#measures start with 1
            #debug
            if currMeasureIndex==36:
                bla=0
            j = 0
            for thisChord in CurrMeasures.recurse().getElementsByClass('Chord'):
                j = j + 1
                rn = roman.romanNumeralFromChord(thisChord,currKey)
                self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, rn.scaleDegree, rn.inversion(), rn.figure)
                # debugging
                #print(self.HarmonicStateMachine.getCadentialOutput().value)
                #thisChord.lyric = str(rn.figure)
                Lyric = self.HarmonicStateMachine.getCadentialOutputString()
                thisChord.lyric = Lyric
                if "PAC" in Lyric or "IAC" in Lyric or "HC" in Lyric or "PCC" in Lyric:
                    print('Measure ', currMeasureIndex + 1 - self.hasPickupMeasure, ' offset ', measuresSecondsMap[currMeasureIndex - self.hasPickupMeasure]['offsetSeconds'], " ", Lyric)
                    print(f"Measure: {currMeasureIndex + 1 - self.hasPickupMeasure} Offset: {measuresSecondsMap[currMeasureIndex - self.hasPickupMeasure]['offsetSeconds']} {Lyric}", file=text_file)
                    print(f"{currMeasureIndex + 1 - self.hasPickupMeasure} {measuresSecondsMap[currMeasureIndex - self.hasPickupMeasure]['offsetSeconds']} {self.HarmonicStateMachine.getCadentialOutput().value}", file=text_fileOffsets)
                #thisChord.lyric = str("block ") + str(i)
        text_file.close()
        text_fileOffsets.close()
        for c in self.ChordStreamRestless.recurse().getElementsByClass('Chord'):
            c.closedPosition(forceOctave=4, inPlace=True)
        self.NoteStream.insert(0, self.ChordStreamRestless)

    def setFileName(self,fileName):
        self.fileName = fileName

    def display(self):
        # open in MuseScore
        self.ChordStream.show()

    def writeAnalyzedFile(self):
        fileName = self.fileName.replace(".", "_")
        fileName = (f"{fileName}_Analyzed.xml")
        FullPath = os.path.join(self.WritePath, fileName)
        self.NoteStream.write(fp=FullPath)

    def displayFull(self):
        self.NoteStream.show()

    def setWritePath(self,path):
        self.WritePath = path
