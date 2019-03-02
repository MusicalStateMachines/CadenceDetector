from CadenceDetectStateMachine import *
from music21 import *
from collections import Counter
import math
import os

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
        self.ChordStream = self.NoteStream.chordify()
        self.NumMeasures = len(self.ChordStream.recurse().getElementsByClass('Measure'))
        self.NumMeasures = min(self.NumMeasures,MaxNumMeasures)
        self.replaceRestWithPrevs()

    def removePickupMeasure(self):
        Parts = self.NoteStream.getElementsByClass(stream.Part)
        self.hasPickupMeasure = 1
        for part in Parts:
            if not part.flat.notesAndRests[0].isRest:
                self.hasPickupMeasure = 0
                print("Pickup Cancelled")
                break

    def replaceRestWithPrevs(self):
        self.NoteStreamRestless = self.NoteStream
        p=0
        for curr_part in self.NoteStreamRestless.recurse().getElementsByClass(stream.Part):
            if p<3:#bass only
                p=p+1
                continue
            prev_note = []
            for curr_measure in curr_part.recurse().getElementsByClass(stream.Measure):
                measure_modifcations_list = []
                #find rest and create modifications
                for curr_item in curr_measure:
                    if isinstance(curr_item,note.GeneralNote):
                        if prev_note:
                            if curr_item.isRest:
                                noteFromRest = self.noteFromRestWithPitch(curr_item, prev_note.pitch)
                                measure_modifcations_list.append([curr_measure.index(curr_item),noteFromRest])
                            else:
                                prev_note = curr_item
                        elif not curr_item.isRest:
                            prev_note = curr_item
                #make modifications to measure
                for curr_mod in measure_modifcations_list:
                    curr_measure.pop(curr_mod[0])
                    curr_measure.insert(curr_mod[1])

        self.ChordStreamRestless = self.NoteStreamRestless.chordify()

        #self.NoteStreamRestless.show()

    def noteFromRestWithPitch(self,rest,pitch):
        noteFromRest = note.Note(pitch)
        noteFromRest.duration = rest.duration
        noteFromRest.quarterLength = rest.quarterLength
        noteFromRest.offset = rest.offset

        return noteFromRest

    def getNumMeasures(self):
        return self.NumMeasures

    def detectKeyPerMeasure(self,blockSize,overlap):
        print("Detecting key per block...")
        self.blockSize = blockSize
        self.overlap = overlap
        stepSize = math.ceil(self.blockSize * self.overlap)
        print(self.NumMeasures)
        for currBlock in range(1,self.NumMeasures+stepSize-1,stepSize):
            StopMeasure = min(currBlock + self.blockSize - 1,self.NumMeasures)
            if StopMeasure<currBlock:
                break
            CurrMeasures = self.ChordStream.measures(currBlock, StopMeasure)
            print(currBlock, StopMeasure)
            Key = CurrMeasures.analyze('key')
            print(Key)
            print(Key.correlationCoefficient)
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

        #loop thru optional keys per measure and determine key by highset distribution

        for currMeasure in range(0,self.NumMeasures):
            currOptionalKeys = self.OptionalKeysPerMeasure[currMeasure]
            key_counts = Counter(currOptionalKeys)
            mostCommonKey = key_counts.most_common(1)[0][0]
            self.KeyPerMeasure.append(mostCommonKey)
            #self.KeyPerMeasure.append(key.Key('D'))#akjshdgakdshg  - temp debug set constant key

    def detectCadences(self):
        print("Detecting cadences...")
        fileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, fileName)
        text_file = open(f"{FullPath}_Analyzed.txt", "w")
        for currMeasureIndex in range(0,self.NumMeasures):
            currKey = self.KeyPerMeasure[currMeasureIndex]#lists start with 0
            CurrMeasures = self.ChordStreamRestless.measures(currMeasureIndex+1,currMeasureIndex+1)#measures start with 1
            j = 0
            for thisChord in CurrMeasures.recurse().getElementsByClass('Chord'):
                j = j + 1
                rn = roman.romanNumeralFromChord(thisChord,currKey)
                self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, rn.scaleDegree, rn.inversion(), rn.figure)
                # debugging
                #print(self.HarmonicStateMachine.getCadentialState().value)
                #thisChord.lyric = str(rn.figure)
                Lyric = self.HarmonicStateMachine.getCadentialStateString()
                thisChord.lyric = Lyric
                if "PAC" in Lyric or "IAC" in Lyric or "HC" in Lyric or "PCC" in Lyric:
                    print('Measure ', currMeasureIndex + 1 - self.hasPickupMeasure, " ", Lyric)
                    print(f"Measure: {currMeasureIndex + 1 - self.hasPickupMeasure} {Lyric}", file=text_file)
                #thisChord.lyric = str("block ") + str(i)
        text_file.close()
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
