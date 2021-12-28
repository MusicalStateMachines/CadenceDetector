from CadenceDetectStateMachine import *
import music21 as m21
from collections import Counter
import math
import os
import numpy
import pickle
import enum
import copy
import sys

class CadenceDetector:
    def __init__(self):
        self.HarmonicStateMachine = CDStateMachine()
        self.HarmonicStateMachineChallenger = CDStateMachine()
        self.NoteStream = []
        self.NoteStreamRestless = []
        self.NoteStreamReduced = []
        self.ChordStream = []
        self.ChordStreamRestless = []
        self.KeyPerMeasure = []
        self.CorrectedKeyPerMeasure = []
        self.InterpretationsPerMeasure = []
        self.SmoothedCorrCoefsPerMeasure = []
        self.CurrSmoothedInterpretations = {}
        #{'A': 0, 'B-': 0, 'B': 0, 'C': 0, 'C#': 0, 'D': 0,
        #'E-': 0, 'E': 0, 'F': 0, 'F#': 0, 'G': 0, 'A-': 0,
        #'a': 0, 'b-': 0, 'b': 0, 'c': 0, 'c#': 0, 'd': 0,
        #'e-': 0, 'e': 0, 'f': 0, 'f#': 0, 'g': 0, 'a-': 0}
        self.Top2Keys = []
        self.PrevKeyString = []
        self.PrevChallengerKeyString = []
        self.OptionalKeysPerMeasure = [[]]
        self.NumMeasures = 0
        self.blockSize = 0
        self.overlap = 0
        self.fileName = 0
        self.hasPickupMeasure = 0
        self.WritePath = 0
        self.KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothing
        self.KeyDetectionForgetFactor = 0.9
        self.MeasuresWithRepeatBrackets = []

    def loadMusic21Corpus(self,fileString):
        self.NoteStream = m21.corpus.parse(fileString)
        self.analyze()

    def loadFileAndGetMeasures(self, fileString):
        print("Loading score...")
        self.NoteStream = m21.converter.parse(fileString)
        self.NumMeasures = len(self.NoteStream.recurse().getElementsByClass('Measure'))
        self.NumMeasures = min(self.NumMeasures, MaxNumMeasures)

    def loadFile(self,fileString):
        print("Loading score...")
        self.NoteStream = m21.converter.parse(fileString)
        self.analyze()

    def analyze(self):
        self.removeChordSymbolsInNoteStream()
        self.removePickupMeasure()
        self.addMyLablesToParts(self.NoteStream)
        try:
            self.ChordStream = self.NoteStream.chordify(addPartIdAsGroup=True, removeRedundantPitches=False)
            self.HarmonicStateMachine.CheckBassPartFromChord = True
            self.HarmonicStateMachineChallenger.CheckBassPartFromChord = True
        except:
            print("Cannot add parts to chords!!")
            self.ChordStream = self.NoteStream.chordify(removeRedundantPitches=False)
            self.HarmonicStateMachine.CheckBassPartFromChord = False
            self.HarmonicStateMachineChallenger.CheckBassPartFromChord = False


        self.NumMeasures = len(self.ChordStream.recurse().getElementsByClass('Measure'))
        self.NumMeasures = min(self.NumMeasures, MaxNumMeasures)
        self.findVoltas()
        self.NoteStreamRestless = copy.deepcopy(self.NoteStream)  #create new list so as not to alter the original stream
        self.replaceBassRestsWithPrevs()
        self.addMyLablesToParts(self.NoteStreamRestless)
        if self.HarmonicStateMachine.CheckBassPartFromChord==True:
            self.ChordStreamRestless = self.NoteStreamRestless.chordify(addPartIdAsGroup=True, removeRedundantPitches=False)
        else:
            self.ChordStreamRestless = self.NoteStreamRestless.chordify(removeRedundantPitches=False)


    def findVoltas(self):
        self.MeasuresWithRepeatBrackets = [0] * self.NumMeasures
        RepeatBrackets = self.NoteStream.recurse().getElementsByClass('RepeatBracket')
        for repeat in RepeatBrackets:
            for sp_store in repeat.spannerStorage:
                measureIndex = sp_store.measureNumber - 1
                self.MeasuresWithRepeatBrackets[measureIndex] = 1


    def removePickupMeasure(self):
        Parts = self.NoteStream.getElementsByClass(stream.Part)
        self.hasPickupMeasure = 1
        for part in Parts:
            if not part.flat.notesAndRests[0].isRest:
                self.hasPickupMeasure = 0
                print("Pickup Cancelled")
                break

    def addMyLablesToParts(self, note_stream):
        parts = note_stream.recurse().getElementsByClass(m21.stream.Part)
        num_parts = len(parts)
        # assuming soprano is first and bass last, remaining parts are not accessed individually
        part_names = ['MySoprano', 'MyAlto', 'MyTenor', 'MyBasso']
        part_names[num_parts-1] = 'MyBasso'
        for i, p in enumerate(parts):
            p.id = part_names[i]

    def tryIsChord(x, self):
        try:
            return x.isChord
        except:
            return False

    def removeChordSymbolsInNoteStream(self):
        objects_to_remove = []
        for curr_note in self.NoteStream.recurse().getElementsByClass('ChordSymbol'):
            if curr_note.isChord:
                objects_to_remove.append(curr_note)

        self.NoteStream.remove(objects_to_remove,recurse=True)

        chords_present = False
        for curr_note in self.NoteStream.recurse().getElementsByClass(note.GeneralNote):
            if curr_note.isChord:
                chords_present = True
                break
        if not chords_present:
             print('No more chords in note stream!')


    def replaceBassRestsWithPrevs(self):
        parts = self.NoteStreamRestless.recurse().getElementsByClass(m21.stream.Part)
        self.NumParts = len(parts)
        p=0
        for curr_part in parts:
            if not p==self.NumParts-1:#bass only, assuming bass is last part
                p=p+1
                continue
            prev_note = []
            for curr_measure in curr_part.recurse().getElementsByClass(m21.stream.Measure):
                #prev_note = []  # should we complete bass between measures ???
                measure_modifcations_list = []
                #find rest and create modifications
                for curr_item in curr_measure.recurse().getElementsByClass(m21.note.GeneralNote):
                    if prev_note:
                        if curr_item.isRest:
                            if prev_note.isChord:
                                note_from_rest = self.noteFromRestWithPitch(curr_item, prev_note.pitches[0])
                            else:
                                note_from_rest = self.noteFromRestWithPitch(curr_item, prev_note.pitch)
                            measure_modifcations_list.append([curr_item, note_from_rest])
                        else:
                            prev_note = curr_item
                    elif not curr_item.isRest:
                        prev_note = curr_item
                #make modifications to measure
                for curr_mod in measure_modifcations_list:
                    curr_measure.replace(curr_mod[0], curr_mod[1])


        #self.NoteStreamRestless.show()

    def noteFromRestWithPitch(self,rest,pitch):
        noteFromRest = m21.note.Note(pitch)
        noteFromRest.duration = rest.duration
        noteFromRest.offset = rest.offset
        noteFromRest.quarterLength = rest.quarterLength
        return noteFromRest

    def chordFromRest(self,rest):
        chordFromRest = m21.chord.Chord([])
        chordFromRest.duration = rest.duration
        chordFromRest.offset = rest.offset
        chordFromRest.quarterLength = rest.quarterLength
        return chordFromRest


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
            CurrMeasures = self.NoteStream.measures(currBlock, StopMeasure)
            #print(currBlock, StopMeasure)
            Key = CurrMeasures.analyze('key')
            AllInterpretations = Key.alternateInterpretations.append(Key)
            #print(Key)
            #print(Key.correlationCoefficient)
            CorrCoefs.append(Key.correlationCoefficient)
            iMeasure = currBlock-1
            for thisMeasure in CurrMeasures:
                #adding the keys as a multiple of the correlation coef to get more accurate statistics
                for nCounts in range(1, math.ceil(Key.correlationCoefficient*10)):
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

        for currMeasure in range(0, self.NumMeasures):
            currOptionalKeys = self.OptionalKeysPerMeasure[currMeasure]
            key_counts = Counter(currOptionalKeys)
            mostCommonKey = key_counts.most_common(1)[0][0]
            self.KeyPerMeasure.append(mostCommonKey)
            ####====debug with constant key
            #self.KeyPerMeasure.append(key.Key('D'))#akjshdgakdshg  - temp debug set constant key

    def detectKeyPerMeasure2(self, blockSize,tc):
        print("Num Measures:", self.NumMeasures)
        self.blockSize = blockSize
        ka = m21.analysis.floatingKey.KeyAnalyzer(self.NoteStream)
        ka.windowSize = self.blockSize
        ka.run()
        my_smoothed_interp = []
        for m in range(1, ka.numMeasures):
            if m == 1:
                curr_smooth = ka.getInterpretationByMeasure(m)
            else:
                curr_smooth = {}
                curr_interpretation = ka.getInterpretationByMeasure(m)
                prev_smooth = my_smoothed_interp[m-2]  # measures start from 1, indices start from zero, hence the -2
                # smoothing per key
                for curr_key in curr_interpretation.keys():
                    curr_smooth[curr_key] = tc * prev_smooth[curr_key] + (1-tc) * curr_interpretation[curr_key]
            my_smoothed_interp.append(curr_smooth)
            # finding maximum per measure after smoothing
            max_key = max(curr_smooth, key=curr_smooth.get)
            self.KeyPerMeasure.append(key.Key(max_key))

        # this is to overcome the last measure problem in music21
        self.KeyPerMeasure.append(self.KeyPerMeasure[-1])

    def detectKeyPerMeasure3(self, blockSize, overlap):
        print("Detecting key per block...")
        self.blockSize = blockSize
        self.overlap = overlap
        print("Num Measures:", self.NumMeasures)
        smoothed_corr_coefs = {}
        for currBlock in range(1, self.NumMeasures+1):
            StopMeasure = min(currBlock + self.blockSize - 1, self.NumMeasures)
            CurrMeasures = self.NoteStream.measures(currBlock, StopMeasure)
            #print(currBlock, StopMeasure)
            try:
                Key = CurrMeasures.analyze('key')
                Key.alternateInterpretations.append(Key)
                max_val = 0
                for curr_key in Key.alternateInterpretations:
                    short_name = curr_key.tonicPitchNameWithCase
                    if short_name not in smoothed_corr_coefs:  # no smoothing on first measure
                        smoothed_val = curr_key.correlationCoefficient
                    else:  # append with smoothing
                        smoothed_val = self.KeyDetectionForgetFactor * smoothed_corr_coefs[short_name] + (1-self.KeyDetectionForgetFactor) * curr_key.correlationCoefficient
                    smoothed_corr_coefs[short_name] = smoothed_val
                    if smoothed_val > max_val:
                        max_val = smoothed_val
                        max_key = curr_key
            except:
                print("Key detection error:", sys.exc_info()[0])
                print("Maintaining previous key")
                max_key = self.KeyPerMeasure[-1]

            self.KeyPerMeasure.append(max_key)
            self.InterpretationsPerMeasure.append(Key.alternateInterpretations)
            self.SmoothedCorrCoefsPerMeasure.append(dict(smoothed_corr_coefs))

            #sort keys by values and return top 2
            #Top2 = dict(sorted(smoothed_corr_coefs.items(), key=lambda item: item[1] , reverse = True)[:2])
            #Top2Keys = list(Top2.keys())
            #self.KeyPerMeasure.append(Top2Keys[0])
            #self.KeyPerMeasure2.append(Top2Keys[1])


        # left shift everything by N measures, for per key change cadences - TBD, shift key using cadence detection
        n_shift = 0
        for i in range(0, len(self.KeyPerMeasure)-n_shift):
            self.KeyPerMeasure[i] = self.KeyPerMeasure[i+n_shift]

        #print(currBlock, max_key)

    def detectKeyPerMeasure4(self, blockSize, overlap):
        print("Detecting key per block...")
        self.blockSize = blockSize
        self.overlap = overlap
        print("Num Measures:", self.NumMeasures)
        for currBlock in range(1, self.NumMeasures+1):
            StopMeasure = min(currBlock + self.blockSize - 1, self.NumMeasures)
            CurrMeasures = self.NoteStream.measures(currBlock, StopMeasure)
            #print(currBlock, StopMeasure)
            try:
                #analysisClasses = [
                #    Ambitus,
                #    KrumhanslSchmuckler,
                #    AardenEssen,
                #    SimpleWeights,
                #    BellmanBudge,
                #    TemperleyKostkaPayne,
                #]
                Key = CurrMeasures.analyze('TemperleyKostkaPayne')
                Key.alternateInterpretations.append(Key)
                CurrInterpretations = list(Key.alternateInterpretations)
            except:
                print("Key detection error:", sys.exc_info()[0])
                print("Maintaining previous key")
                CurrInterpretations = list(self.InterpretationsPerMeasure[-1])

            self.InterpretationsPerMeasure.append(CurrInterpretations)


    def detectKeyPerMeasureWrapper(self, blockSize, overlap):
        if self.KeyDetectionMode == CDKeyDetectionModes.KSRaw:
            self.detectKeyPerMeasure(blockSize, overlap)
        #elif self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing:
        #    self.detectKeyPerMeasure3(blockSize, overlap)
        elif self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive or self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing:
            self.detectKeyPerMeasure4(blockSize, overlap)

    def reenforceKeyByFactor(self, keyString, enhancement):
        enhancedCoef = math.pow(self.CurrSmoothedInterpretations[keyString], 1/enhancement)
        self.CurrSmoothedInterpretations[keyString] = enhancedCoef

    def writeKeyPerMeasureToFile(self, KeyDetectionMode):
        if KeyDetectionMode != CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
            print("Writing keys to file...")
            keyfileName = self.fileName.replace(".", "_")
            FullPath = os.path.join(self.WritePath, keyfileName)
            KeyFile = f"{FullPath}_Key_{KeyDetectionMode}.txt"
            with open(KeyFile, 'wb') as f:
                pickle.dump(self.KeyPerMeasure, f)

    def readKeyPerMeasureFromFile(self, KeyDetectionMode):
        if KeyDetectionMode != CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
            print("Reading keys from file...")
            keyfileName = self.fileName.replace(".", "_")
            FullPath = os.path.join(self.WritePath, keyfileName)
            KeyFile = f"{FullPath}_Key_{KeyDetectionMode}.txt"
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
        return m21.key.Key(Music21StringKey,Music21StringMode)

    def isUpwardArpeggioPattern(self, pitches, arp_len):
        if len(pitches) < arp_len:
            retVal = False
        else:
            retVal = True
            if all(x.midi > pitches[0].midi for x in pitches[1:]):
                prev_pitch = []
                for p in pitches:
                    if prev_pitch and (p.midi - prev_pitch.midi) < 3: #minor and major second disqualifies the arpeggio
                        retVal = False
                        break
                    prev_pitch = p
            else:
                retVal = False
        return retVal

    def isAlbertiPattern(self, pitches, pattern_len):
        retVal =  all(x.midi > pitches[0].midi for x in pitches[1:4]) and pitches[1].midi == pitches[3].midi
        # for pattern length 6 (3/4,3/8,6/8) verify last two as well
        if pattern_len == 6:
            retVal = retVal and pitches[3].midi == pitches[5].midi
        return retVal

    def extractBassLine(self, measure):
        lowestPitches = []
        for chord in measure:
            if not chord.isRest:
                lowestPitch = chord.sortFrequencyAscending().pitches[0]
                lowestPitches.append(lowestPitch)
            else:
                lowestPitches.append(None)
        return lowestPitches


    def detectAlbertiBassInMeasure(self, measure, pattern_len):
        #first exact bassline from chords
        lowestPitches = self.extractBassLine(measure)
        albertiBeats = [0]*len(measure)
        for beat in range(0, len(measure), pattern_len):
            if beat+pattern_len <= len(measure):
                pattern_notes = lowestPitches[beat:beat+pattern_len]
                if None not in pattern_notes:
                    isAlberti = self.isAlbertiPattern(pattern_notes,pattern_len)
                    albertiBeats[beat:beat+pattern_len] = [isAlberti] * pattern_len
        return albertiBeats


    def detectArpeggioBassInMeasure(self, measure, arp_len):
        lowestPitches = self.extractBassLine(measure)
        arpeggioBeats = [0]*len(measure)
        for beat in range(0, len(measure), arp_len):
            subsec = lowestPitches[beat:beat+arp_len]
            if None not in subsec:
                isArp = self.isUpwardArpeggioPattern(subsec, arp_len)
                arpeggioBeats[beat:beat+arp_len] = [isArp] * arp_len
        return arpeggioBeats

    def smoothKeyInterpretations(self, measureIndex):
        currInterpretations = self.InterpretationsPerMeasure[measureIndex]
        for interpretation in currInterpretations:
            corrCoef = interpretation.correlationCoefficient
            keyString = interpretation.tonicPitchNameWithCase
            if keyString not in self.CurrSmoothedInterpretations:
                self.CurrSmoothedInterpretations[keyString] = corrCoef
            currSmoothedVal = self.CurrSmoothedInterpretations[keyString]
            currSmoothedVal = self.KeyDetectionForgetFactor * currSmoothedVal + (1-self.KeyDetectionForgetFactor) * corrCoef
            self.CurrSmoothedInterpretations[keyString] = currSmoothedVal


    def getTopNKeyInterpretations(self, N):
        #now sort by value
        SortedKeys = sorted(self.CurrSmoothedInterpretations.items(), key=lambda x: x[1], reverse=True)
        TopNKeys = list(SortedKeys[:N])
        return TopNKeys


    def detectCadences(self):
        print("Detecting cadences...")
        fileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, fileName)
        text_file = open(f"{FullPath}_Analyzed.txt", "w")
        text_fileOffsets = open(f"{FullPath}_Analyzed_OffsetsNums.txt", "w")
        text_fileTransitions = open(f"{FullPath}_Analyzed_Transitions.txt", "w")

        measuresSecondsMap = list(filter(lambda d: d['durationSeconds'] > 0, self.ChordStreamRestless.secondsMap))

        prevState = []
        repeat_counter = 0

        for currMeasureIndex in range(0,self.NumMeasures):
            repeat_counter = repeat_counter + self.MeasuresWithRepeatBrackets[currMeasureIndex]
            CurrMeasuresRestless= self.ChordStreamRestless.measures(currMeasureIndex+1,currMeasureIndex+1)#measures start with 1
            CurrMeasures = self.ChordStream.measures(currMeasureIndex + 1,currMeasureIndex + 1)  # measures start with 1
            #check and update timesig
            for timeSig in CurrMeasures.recurse().getElementsByClass(m21.meter.TimeSignature):
                if timeSig != self.HarmonicStateMachine.CurrHarmonicState.TimeSig:
                    self.HarmonicStateMachine.CurrHarmonicState.TimeSig = timeSig
                    self.HarmonicStateMachineChallenger.CurrHarmonicState.TimeSig = timeSig

            if self.HarmonicStateMachine.CurrHarmonicState.TimeSig.ratioString in ['3/4', '3/8', '6/8']:
                alberti_len = 6
                arp_len = 3
            else:
               alberti_len = 4
               arp_len = 4
            AlbertiBeats = self.detectAlbertiBassInMeasure(CurrMeasuresRestless.recurse().getElementsByClass('GeneralNote'), pattern_len=alberti_len)
            ArpeggioBeats = self.detectArpeggioBassInMeasure(CurrMeasuresRestless.recurse().getElementsByClass('GeneralNote'), arp_len=arp_len)

            #debug per measure
            if currMeasureIndex == 174:
                bla=0

            LyricPerBeat = []

            if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or\
                    self.KeyDetectionMode==CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                #smooth keys here, per measure (TBD - per chord?):
                self.smoothKeyInterpretations(currMeasureIndex)
                #sort and return top 2
                self.Top2Keys = self.getTopNKeyInterpretations(2)
            else:
                currKey = self.KeyPerMeasure[currMeasureIndex]#lists start with 0

            for thisChord, thisChordWithBassRests, alberti, arpeggio in zip(CurrMeasuresRestless.recurse().getElementsByClass('GeneralNote'),CurrMeasures.recurse().getElementsByClass('GeneralNote'),AlbertiBeats, ArpeggioBeats):
                if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or\
                        self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                    currKeyString = self.Top2Keys[0][0]
                    currKey = m21.key.Key(currKeyString)
                    challengerKeyString = self.Top2Keys[1][0]
                    challengerKey = m21.key.Key(challengerKeyString)
                    self.updateKeysAndSwapStateMachines(currKeyString, challengerKeyString)

                if thisChord.isRest:
                    self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, thisChordWithBassRests, [], [], [], alberti, arpeggio, [])
                else:
                    rn = m21.roman.romanNumeralFromChord(thisChord, currKey)
                    self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, thisChordWithBassRests, rn.scaleDegree, rn.inversion(), rn.figure, alberti, arpeggio, rn)

                if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or \
                        self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                    if thisChord.isRest:
                        self.HarmonicStateMachineChallenger.updateHarmonicState(challengerKey, thisChord, thisChordWithBassRests, [], [], [], alberti, arpeggio, [])
                    else:
                        rn2 = m21.roman.romanNumeralFromChord(thisChord, challengerKey)
                        self.HarmonicStateMachineChallenger.updateHarmonicState(challengerKey, thisChord, thisChordWithBassRests, rn2.scaleDegree, rn2.inversion(), rn2.figure, alberti, arpeggio, rn2)


                #TBD - should we handle this reversion in challenger?
                if self.HarmonicStateMachine.getRevertLastPACAndReset() and len(LyricPerBeat)>0: #this limits PAC reversion to within measure
                    LastPACTuple = LyricPerBeat[-1]
                    UpdatedLyric = "IAC"
                    LyricPerBeat[-1] = [LastPACTuple[0], UpdatedLyric]
                    print("Reverting last PAC to IAC")

                Lyric = self.HarmonicStateMachine.getCadentialOutputString()
                LyricChallenger = self.HarmonicStateMachineChallenger.getCadentialOutputString()
                # Cadence Sensitive Key Detection Mode
                if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                    # and self.HarmonicStateMachineChallenger.CurrHarmonicState.Key.tonic != self.HarmonicStateMachine.CurrHarmonicState.Key.tonic: #don't be sensitive to candece in parallel key:
                    # Cadence check in main key (for key re-enforcement)
                    ReenforcementFactors = {'PAC': 2, 'IAC': 5/4, 'HC': 5/4}
                    resort = False
                    for cad in ReenforcementFactors:
                        if cad in Lyric:
                            self.reenforceKeyByFactor(currKeyString, ReenforcementFactors[cad])
                        # Challenger Check (for key switching)
                        if cad in LyricChallenger:
                            self.reenforceKeyByFactor(challengerKeyString, ReenforcementFactors[cad])
                            resort = True

                    if resort:
                        # re-sort and return Top2Keys
                        self.Top2Keys = self.getTopNKeyInterpretations(2)
                        if challengerKeyString == self.Top2Keys[0][0]:
                            Lyric = LyricChallenger
                            print('Cadential Key Change!')

                # debugging
                # print(self.HarmonicStateMachine.getCadentialOutput().value)
                # thisChord.lyric = str(rn.figure)

                if Lyric:   # only work on non-empty lyrics
                    thisChord.lyric = Lyric
                    LyricPerBeat.append([thisChord.beat,Lyric])
                    #TBD - do we still need to print this?
                    print(f"{measuresSecondsMap[currMeasureIndex]['offsetSeconds'] + measuresSecondsMap[currMeasureIndex]['durationSeconds']*(thisChord.beat-1)/CurrMeasuresRestless.duration.quarterLength:.1f} {self.HarmonicStateMachine.getCadentialOutput().value}", file=text_fileTransitions)


            #checking cadences on entire measure
            for LyricTuple in LyricPerBeat:
                Lyric = LyricTuple[1]
                if "PAC" in Lyric or "IAC" in Lyric or "HC" in Lyric or "PCC" in Lyric:
                    if "PAC" in Lyric:
                        CadString = "PAC"
                    elif "IAC" in Lyric:
                        CadString = "IAC"
                    elif "HC" in Lyric:
                        CadString = "HC"
                    elif "PCC" in Lyric:
                        CadString = "PCC"
                    CadStringToNumMap = {"PAC": CDCadentialStates.PACArrival.value, "IAC": CDCadentialStates.IACArrival.value, "HC": CDCadentialStates.HCArrival.value, "PCC": CDCadentialStates.PCCArrival.value}
                    measure_to_write = currMeasureIndex + 1 - self.hasPickupMeasure - math.floor(repeat_counter/2)
                    print('Measure ', measure_to_write, ' offset ', measuresSecondsMap[currMeasureIndex]['offsetSeconds'], " ", Lyric)
                    print(f"Measure: {measure_to_write} Offset: {measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {Lyric}", file=text_file)
                    print(f"{measure_to_write} {measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {CadStringToNumMap[CadString]}", file=text_fileOffsets)
                elif "Key" in Lyric:
                    print(Lyric)

                # save transitions to file regardless of Lyrics
                # if prevState != self.HarmonicStateMachine.getCadentialOutput().value:
                #    print(f"{measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {self.HarmonicStateMachine.getCadentialOutput().value}", file=text_fileTransitions)
                # prevState = self.HarmonicStateMachine.getCadentialOutput().value
                # thisChord.lyric = str("block ") + str(i)

            CurrMeasuresNotes = self.NoteStream.measures(currMeasureIndex + 1, currMeasureIndex + 1)
            Parts = CurrMeasuresNotes.getElementsByClass(stream.Part)
            for thisLyric in LyricPerBeat:
                found = 0
                for index in range(0, self.NumParts):
                    for thisNote in Parts[-1-index].flat.notesAndRests:  # adding lyric from last part up, assuming its the bass line
                        if thisNote.beat == thisLyric[0]:
                            thisNote.lyric = thisLyric[1]
                            found = 1
                            break
                    if found == 1:
                        break

            #write corrected key at end of measure
            if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive or self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing:
                correctedKeyString = self.Top2Keys[0][0]
                correctedKey = m21.key.Key(correctedKeyString)
                self.CorrectedKeyPerMeasure.append(correctedKey)

        text_file.close()
        text_fileOffsets.close()
        text_fileTransitions.close()
        for c in self.ChordStreamRestless.recurse().getElementsByClass('Chord'):
            c.closedPosition(forceOctave=4, inPlace=True)
        # this adds the restless chord stream to the note stream
        # self.NoteStream.insert(0, self.ChordStream)

        if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive or self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing:
            print("Writing cadence corrected keys to file...")
            keyfileName = self.fileName.replace(".", "_")
            FullPath = os.path.join(self.WritePath, keyfileName)
            KeyFile = f"{FullPath}_Key_{self.KeyDetectionMode}.txt"
            with open(KeyFile, 'wb') as f:
                pickle.dump(self.CorrectedKeyPerMeasure, f)

    def updateKeysAndSwapStateMachines(self, currKeyString, challengerKeyString):
        # this swap assures the smoothness of key transition if challenger becomes main (and main becomes challenger)
        if currKeyString != self.PrevKeyString:
            tempStateMachine = copy.deepcopy(self.HarmonicStateMachine)
            if currKeyString == self.PrevChallengerKeyString:
                self.HarmonicStateMachine = copy.deepcopy(self.HarmonicStateMachineChallenger)
                self.HarmonicStateMachine.CadentialKeyChange = 1
            if challengerKeyString == self.PrevKeyString:
                self.HarmonicStateMachineChallenger = copy.deepcopy(tempStateMachine)
        self.PrevKeyString = currKeyString
        self.PrevChallengerKeyString = challengerKeyString

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
