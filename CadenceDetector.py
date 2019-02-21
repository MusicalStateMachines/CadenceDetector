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
        self.ChordStream = []
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
        Parts = self.NoteStream.getElementsByClass(stream.Part)
        self.hasPickupMeasure = 1
        for part in Parts:
            if not part.flat.notesAndRests[0].isRest:
                self.hasPickupMeasure = 0
                print("Pickup Cancelled")
                break
        self.ChordStream = self.NoteStream.chordify()
        self.NumMeasures = len(self.ChordStream.recurse().getElementsByClass('Measure'))
        self.NumMeasures = min(self.NumMeasures,MaxNumMeasures)

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

        for currMeasure in range(0,self.NumMeasures-1):
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
        for currMeasureIndex in range(0,self.NumMeasures-1):
            currKey = self.KeyPerMeasure[currMeasureIndex]#lists start with 0
            CurrMeasures = self.ChordStream.measures(currMeasureIndex+1,currMeasureIndex+1)#measures start with 1
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
                if "PAC" in Lyric or "IAC" in Lyric or "HC" in Lyric:
                    print('Measure ', currMeasureIndex + 1 - self.hasPickupMeasure, " ", Lyric)
                    print(f"Measure: {currMeasureIndex + 1 -self.hasPickupMeasure} {Lyric}", file=text_file)
                #thisChord.lyric = str("block ") + str(i)
        text_file.close()
        for c in self.ChordStream.recurse().getElementsByClass('Chord'):
            c.closedPosition(forceOctave=4, inPlace=True)
        self.NoteStream.insert(0, self.ChordStream)

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
