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
        self.BassChords = []
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
        self.Parts = []
        self.MeasuresPerPart = []
        self.NumMeasures = 0
        self.blockSize = 0
        self.overlap = 0
        self.key_detection_lookahead = 0
        self.fileName = 0
        self.hasPickupMeasure = 0
        self.WritePath = 0
        self.KeyDetectionMode = CDKeyDetectionModes.KSWithSmoothing
        self.KeyDetectionForgetFactor = 0.9
        self.RepeatedMeasureByVolta = []
        self.IncompleteMeasures = []
        self.EmptyMeasures = []
        self.ReenforcementFactors = []
        self.FinalBarlines = []

    def loadMusic21Corpus(self,fileString):
        self.NoteStream = m21.corpus.parse(fileString)
        self.analyze()

    def loadFileAndGetMeasures(self, fileString):
        print("Loading score...")
        self.NoteStream = m21.converter.parse(fileString)
        self.Parts = self.NoteStream.recurse().getElementsByClass(m21.stream.Part)
        self.NumParts = len(self.Parts)
        for part in self.Parts:
            self.MeasuresPerPart.append(part.recurse().getElementsByClass(m21.stream.Measure))
        self.NumMeasures = max([len(curr_part_measures) for curr_part_measures in self.MeasuresPerPart])
        self.NumMeasures = min(self.NumMeasures, MaxNumMeasures)
        #update some data to state machines
        self.HarmonicStateMachine.NumParts = self.NumParts
        self.HarmonicStateMachineChallenger.NumParts = self.NumParts
        # do some other quick analysis for debugging without full cadence detection
        # self.findVoltas()

    def loadFile(self,fileString):
        self.loadFileAndGetMeasures(fileString)
        self.analyze()

    def analyze(self):
        self.removeChordSymbolsInNoteStream()
        self.removePickupMeasure()
        self.addMyLablesToParts(self.NoteStream)
        NoteStreamNoGrace = self.removeGraceNotes(self.NoteStream)
        try:
            self.ChordStream = NoteStreamNoGrace.chordify(addPartIdAsGroup=True, removeRedundantPitches=False, copyPitches=False)
            self.HarmonicStateMachine.CheckBassPartFromChord = True
            self.HarmonicStateMachineChallenger.CheckBassPartFromChord = True
        except:
            print("Cannot add parts to chords!!")
            self.ChordStream = NoteStreamNoGrace.chordify(removeRedundantPitches=False, copyPitches=False)
            self.HarmonicStateMachine.CheckBassPartFromChord = False
            self.HarmonicStateMachineChallenger.CheckBassPartFromChord = False


        self.NumMeasures = len(self.ChordStream.recurse().getElementsByClass(m21.stream.Measure))
        self.NumMeasures = min(self.NumMeasures, MaxNumMeasures)
        self.findVoltas()
        self.findFinalBarlines()
        self.findEmptyMeasures()
        self.findIncompleteMeasures()
        self.NoteStreamRestless = copy.deepcopy(self.NoteStream)  #create new list so as not to alter the original stream
        self.replaceBassRestsWithPrevsViaSecondsMaps()
        self.addMyLablesToParts(self.NoteStreamRestless)
        NoteStreamRestlessNoGrace = self.removeGraceNotes(self.NoteStreamRestless)
        if self.HarmonicStateMachine.CheckBassPartFromChord==True:
            self.ChordStreamRestless = NoteStreamRestlessNoGrace.chordify(addPartIdAsGroup=True, removeRedundantPitches=False, copyPitches=False)
        else:
            self.ChordStreamRestless = NoteStreamRestlessNoGrace.chordify(removeRedundantPitches=False, copyPitches=False)

        #chordifying only bass part
        parts = self.NoteStream.recurse().getElementsByClass(m21.stream.Part)
        BassPartNoGrace = self.removeGraceNotes(parts[-1])
        try:
            self.BassChords = BassPartNoGrace.chordify(addPartIdAsGroup=True, removeRedundantPitches=False, copyPitches=False)
        except:
            self.BassChords = BassPartNoGrace.chordify(removeRedundantPitches=False, copyPitches=False)

        self.findGroupLimitsViaSecondsMap()

    def findGroupLimits(self):
        for part in self.Parts:
            prev_note = []
            prev_diff = []
            prev_measure = []
            for curr_measure in part.recurse().getElementsByClass(m21.stream.Measure):
                first_note_in_measure = True
                for curr_note in curr_measure.recurse().getElementsByClass(m21.note.Note):
                    if curr_note.tie and not curr_note.tie == m21.tie.Tie('start'):
                        continue
                    if prev_note:
                        curr_diff = curr_note.offset - prev_note.offset
                        if first_note_in_measure and prev_measure: # first note but not first measure, complete previous measure
                            curr_diff += prev_measure.duration.quarterLength
                        if prev_diff:
                            # long note groups backward with previous shorter notes, adding epsilon becuase they may be different due to fraction inaccuracy
                            # also close grouping on very long notes (longer than a measure)
                            epsilon = 0.001
                            if (curr_diff > prev_diff + epsilon) or curr_diff >= curr_measure.duration.quarterLength:
                                prev_note.groups.append('}')
                                curr_note.groups.append('{')
                        prev_diff = curr_diff
                    else: # first note of work
                        curr_note.groups.append('{')
                    prev_note = curr_note
                    first_note_in_measure = False
                prev_measure = curr_measure
            # always mark last note in part
            if prev_note:
                prev_note.groups.append('}')
            # add grouping lyrics for debug
            for note in part.recurse().getElementsByClass(m21.note.Note):
                note.lyric = ' '.join(note.groups)

    def findGroupLimitsViaSecondsMap(self):
        for part in self.Parts:
            prev_secondsDict = prev_note = prev_diff = []
            part_measures_secondsMap = sorted(part.recurse().getElementsByClass(m21.stream.Measure).secondsMap, key=lambda d: d['offsetSeconds'])
            part_notes_secondsMap = sorted(part.recurse().notesAndRests.secondsMap, key=lambda d: d['offsetSeconds'])
            for secondsDict in part_notes_secondsMap:
                curr_note = secondsDict['element']
                if curr_note.tie and not curr_note.tie == m21.tie.Tie('start'):
                    continue
                if prev_secondsDict:
                    curr_diff = secondsDict['offsetSeconds'] - prev_secondsDict['offsetSeconds']
                    if curr_diff <= 0:
                        continue
                    prev_note = prev_secondsDict['element']
                    if (prev_note.isRest and curr_note.isRest): # no grouping on consecutive rests
                        pass
                    elif not prev_note.isRest and curr_note.isRest:
                        prev_note.groups.append('}')
                    elif prev_note.isRest and not curr_note.isRest:
                        curr_note.groups.append('{')
                    elif prev_diff:
                        # long note groups backward with previous shorter notes
                        # also close grouping on very long notes (longer than a measure)
                        # epsilon and frac needed because they may be different due to fraction and measure duration inaccuracy
                        epsilon = 0.001
                        frac = 0.9
                        # === debug per measure
                        if curr_note.measureNumber and curr_note.measureNumber==66:
                            bla = 0
                        if (curr_diff > prev_diff + epsilon) or (prev_note.measureNumber and curr_diff >= frac * part_measures_secondsMap[prev_note.measureNumber-1]['durationSeconds']):
                            prev_note.groups.append('}')
                            curr_note.groups.append('{')
                    prev_diff = curr_diff
                else:  # first note of work
                    curr_note.groups.append('{')
                prev_secondsDict = secondsDict
            # always mark last note in part
            if prev_note:
                prev_note.groups.append('}')
            # add grouping lyrics for debug
            for note in part.recurse().getElementsByClass(m21.note.GeneralNote):
                note.lyric = ' '.join(note.groups)


    def findVoltas(self):
        self.RepeatedMeasureByVolta = [0] * self.NumMeasures
        RepeatBrackets = self.NoteStream.recurse().getElementsByClass('RepeatBracket')
        for repeat in RepeatBrackets:
            for sp_store in repeat.spannerStorage:
                measureIndex = sp_store.measureNumber - 1
                self.RepeatedMeasureByVolta[measureIndex] = 1

    def findFinalBarlines(self):
        self.FinalBarlines = [0] * self.NumMeasures
        final_barlines = self.NoteStream.recurse().getElementsByClass('Barline')
        for curr_barline in final_barlines:
            if curr_barline.type == 'final':
                measureIndex = curr_barline.measureNumber - 1
                self.FinalBarlines[measureIndex] = 1

    def findIncompleteMeasures(self):
        print('Finding incomplete measures...')
        self.IncompleteMeasures = [0] * self.NumMeasures
        time_sig = []
        measure_zero = self.ChordStream.measure(0)
        if measure_zero:
            for currSig in measure_zero.recurse().getElementsByClass(m21.meter.TimeSignature):
                time_sig = currSig
        for i in range(self.NumMeasures): #enumerate(self.ChordStream.recurse().getElementsByClass(stream.Measure)):
            measure = self.ChordStream.measure(i+1)
            if measure:
                if i==36:
                    bla = 0
                for timeSig in measure.recurse().getElementsByClass(m21.meter.TimeSignature):
                    time_sig = timeSig
                chords = [chord for chord in measure.recurse().getElementsByClass('GeneralNote')]
                if chords and not chords[-1].isRest: # this attemps to avoid false pickups (i.e. ignore cases where the rest is just not long enough) - not sure this is solid for all pickups
                    lengths = [chord.duration.quarterLength for chord in chords]
                    total_duration = sum(lengths)
                    epsilon = 0.1 # this epsilon is needed because of inaccuracy caused by decoration notes in some scores
                    if total_duration < (1 - epsilon) * time_sig.barDuration.quarterLength:
                        self.IncompleteMeasures[i] = True
        # using pickup detection from Haydn, find first non-empty measure and set it incomplete there exists a pickup
        first_non_empty_measure = self.EmptyMeasures.index(0)
        self.IncompleteMeasures[first_non_empty_measure] = self.IncompleteMeasures[first_non_empty_measure] or self.hasPickupMeasure
        incomplete_measures = [i+1 for i,inc in enumerate(self.IncompleteMeasures) if inc]
        print('Incomplete meaures:', incomplete_measures)


    def findEmptyMeasures(self):
        print('Finding empty measures...')
        self.EmptyMeasures = [0] * self.NumMeasures
        for i in range(self.NumMeasures):
            curr_measure = self.ChordStream.measure(i+1)
            if curr_measure and len(curr_measure.recurse().notesAndRests) == 0:
                self.EmptyMeasures[i] = 1
        empty_measures = [i + 1 for i, emp in enumerate(self.EmptyMeasures) if emp]
        print('Empty measures:', empty_measures)


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
        # for more than one voice, assuming soprano is first and bass last, remaining parts are not accessed individually
        parts[0].id = 'MySoprano'
        parts[-1].id = 'MyBasso'

    def removeGraceNotes(self, note_stream):
        # remove grace notes
        note_stream = copy.deepcopy(note_stream)
        graceNotes = []
        for n in note_stream.recurse().notes:
            if n.duration.isGrace:
                graceNotes.append(n)
        for grace in graceNotes:
            grace.activeSite.remove(grace)
        return note_stream

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
            measure_modifcations_list = []
            for i,curr_measure in enumerate(curr_part.recurse().getElementsByClass(m21.stream.Measure)):
                if i==55:
                    bla = 0
                if len(measure_modifcations_list) > 0: # only complete one measure forward
                    prev_note = []
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

    def replaceBassRestsWithPrevsViaSecondsMaps(self):
        max_consec_empty_meas = 1
        prev_note = []
        prev_measure_dur = []
        consecutive_empty_measure_durations = []
        measures_to_tie = []
        parts = self.NoteStreamRestless.recurse().getElementsByClass(m21.stream.Part)
        for curr_measure in parts[-1].recurse().getElementsByClass(m21.stream.Measure):
            notes_in_measure = 0
            measure_modifcations_list = []
            if curr_measure.measureNumber == 121:
                bla  = 0
            # get curr meaure duration before alterations
            curr_measure_duration = copy.deepcopy(curr_measure.duration.quarterLength)
            #find rest and create modifications
            sortedSecondsMaps = sorted(curr_measure.recurse().secondsMap, key=lambda d: d['offsetSeconds'])
            for curr_item in sortedSecondsMaps:
                #only notes, chords, and rests have durations
                if not curr_item['durationSeconds'] > 0:
                    continue
                if curr_item['element'].isRest:# found rest, remove it but not after one measure
                    if prev_note and (notes_in_measure > 0 or len(consecutive_empty_measure_durations) <= max_consec_empty_meas):
                        measure_modifcations_list.append(curr_item['element'])
                else: # note or chord
                    if not prev_note:
                        prev_note = curr_item
                    else: # not a rest and prev_note exists
                        if notes_in_measure > 0 and (curr_item['element'].offset == prev_note['element'].offset or curr_item['endTimeSeconds'] == prev_note['endTimeSeconds']):# if has same offset but lower bass update new curr item without changing duration
                            curr_lowest_pitch = curr_item['element'].sortFrequencyAscending().pitches[0] if curr_item['element'].isChord else curr_item['element'].pitch
                            prev_lowest_pitch = prev_note['element'].sortFrequencyAscending().pitches[0] if prev_note['element'].isChord else prev_note['element'].pitch
                            if curr_lowest_pitch.midi < prev_lowest_pitch.midi:
                                prev_note = curr_item
                        else: # found note or chord with new offset, extend duration till this note
                            curr_offset = curr_item['element'].offset
                            prev_offset = prev_note['element'].offset
                            extended_quarterLength = curr_offset - prev_offset
                            if notes_in_measure == 0 and prev_measure_dur: # first note in measure, complete previous measure
                                extended_quarterLength += prev_measure_dur
                            # now complete the empty measues (if exist)
                            extended_quarterLength += np.sum([dur for dur in consecutive_empty_measure_durations])
                            if extended_quarterLength > prev_note['element'].quarterLength and (notes_in_measure > 0 or len(consecutive_empty_measure_durations) <= max_consec_empty_meas):
                                prev_note['element'].duration = m21.duration.Duration(extended_quarterLength)
                                prev_note['element'].quarterLength = extended_quarterLength
                            # now check if prev_note exceeded its measure length
                            if (prev_note['element'].offset + prev_note['element'].quarterLength > curr_measure_duration):
                                measures_to_tie.append({'from': prev_note['element'].measureNumber, 'to': curr_measure.measureNumber})
                            prev_note = curr_item
                    notes_in_measure += 1
                    consecutive_empty_measure_durations = []
            #extend last note to complete measure
            if prev_note and notes_in_measure > 0:
                remainder = curr_measure_duration - prev_note['element'].offset
                if remainder > prev_note['element'].quarterLength:
                    prev_note['element'].duration = m21.duration.Duration(remainder)
                    prev_note['element'].quarterLength = remainder
            # check for final barline
            if curr_measure.rightBarline and curr_measure.rightBarline.type == 'final':
                prev_note = []
            # check if measure was empty
            if notes_in_measure == 0 and prev_note:
                consecutive_empty_measure_durations.append(curr_measure.duration.quarterLength)
            prev_measure_dur = curr_measure.duration.quarterLength
            # make erase modifications to measure
            curr_measure.remove(measure_modifcations_list, recurse=True)
        # making ties for notes extending beyond measure locally
        makeTies_local_failure = False
        for curr_measures_to_tie in measures_to_tie:
            try:
                self.NoteStreamRestless.parts[-1].measures(curr_measures_to_tie['from'], curr_measures_to_tie['to']).recurse().makeTies(inPlace=True)
            except:
                makeTies_local_failure = True
                print(f'makeTies failed on measures {curr_measures_to_tie}')
        # making ties on entire stream if it failed locally
        if makeTies_local_failure:
            try:
                self.NoteStreamRestless.parts[-1].recurse().makeTies(inPlace=True)
                print(f'makeTies overall succeeded')
            except:
                print(f'makeTies failed')
        else:
            print(f'makeTies locally succeeded')

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
            # this only looks at current bar and backwards, simulating realtime
            lookahead = round((self.blockSize - 1) * self.key_detection_lookahead)
            lookback = self.blockSize - lookahead - 1
            StopMeasure = min(currBlock + lookahead, self.NumMeasures)
            StartMeasure = max(currBlock - lookback, 0)
            CurrMeasures = self.NoteStream.measures(StartMeasure, StopMeasure)
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

    def isArpeggioPattern(self, pitches, lengths, arp_len, up_down=None):
        if len(pitches) < arp_len or not all(lengths[0] == l for l in lengths[1:4]):
            retVal = False
        else:
            retVal = True
            if up_down == 'up':
                if all(x.midi > pitches[0].midi for x in pitches[1:]):
                    prev_pitch = []
                    for p in pitches:
                        if prev_pitch and (p.midi - prev_pitch.midi) < 3: #minor and major second disqualifies the arpeggio
                            retVal = False
                            break
                        prev_pitch = p
                else:
                    retVal = False
            elif up_down == 'down':
                if all(x.midi < pitches[0].midi for x in pitches[1:]):
                    prev_pitch = []
                    for p in pitches:
                        if prev_pitch and (prev_pitch.midi - p.midi) < 3: #minor and major second disqualifies the arpeggio
                            retVal = False
                            break
                        prev_pitch = p
                else:
                    retVal = False
        return retVal

    def isAlbertiPattern(self, pitches, lengths, pattern_len):
        retVal = all(lengths[0] == l for l in lengths[1:4])
        retVal = retVal and all(x.midi >= pitches[0].midi for x in pitches[1:4]) and pitches[1].midi == pitches[3].midi
        # for pattern length 6 (3/4,3/8,6/8) verify last two as well, either continuing the same pattern or repeating the bass
        if pattern_len == 6:
            retVal = all(lengths[0] == l for l in lengths)
            retVal = retVal and (pitches[3].midi == pitches[5].midi or pitches[0] == pitches[4])
        return retVal

    def extractBassLine(self, measure):
        lowestPitches = []
        quarterLengths= []
        for chord in measure:
            if not chord.isRest:
                lowestNote = chord.sortFrequencyAscending()[0]
                lowestPitches.append(lowestNote.pitch)
                quarterLengths.append(lowestNote.quarterLength)
            else:
                lowestPitches.append(None)
        return {'pitches': lowestPitches, 'lengths': quarterLengths}

    def detectAlbertiOrArpeggioBassInMeasure(self, measure_chords, bass_chords, pattern_len, arp_type):
        #first exact bassline from chords
        measure_general_notes = measure_chords.recurse().getElementsByClass('GeneralNote')
        bass_general_notes = bass_chords.recurse().getElementsByClass('GeneralNote')
        lowest_pitches_in_bass = self.extractBassLine(bass_general_notes)
        arp_patterns = []

        for i in range(0, len(bass_general_notes), pattern_len):
            if i+pattern_len <= len(bass_general_notes):
                curr_pitches = lowest_pitches_in_bass['pitches'][i:i+pattern_len]
                curr_lengths = lowest_pitches_in_bass['lengths'][i:i+pattern_len]
                if None not in curr_pitches:
                    if arp_type == 'alberti':
                        isArp = self.isAlbertiPattern(pitches=curr_pitches, lengths=curr_lengths, pattern_len=pattern_len)
                    elif arp_type == 'arp_up':
                        isArp = self.isArpeggioPattern(pitches=curr_pitches, lengths=curr_lengths, arp_len=pattern_len, up_down='up')
                    elif arp_type =='arp_down':
                        isArp = self.isArpeggioPattern(pitches=curr_pitches, lengths=curr_lengths, arp_len=pattern_len, up_down='down')
                    else:
                        isArp = False
                    if isArp:
                        epsilon = 0.1  # this epsilon is required to mark the last alberti beat including its length, but not the next beat
                        arp_patterns.append({'start': bass_general_notes[i + 1].beat,
                                             'stop': bass_general_notes[i + pattern_len - 1].beat + bass_general_notes[i + pattern_len - 1].duration.quarterLength - epsilon})

        arp_beats = [0] * len(measure_general_notes)
        for i,gen_note in enumerate(measure_general_notes):
            for pat in arp_patterns:
                if pat['start'] <= gen_note.beat <= pat['stop']:
                    arp_beats[i] = True
                    break

        return arp_beats

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


    def getNotesPerChordBeatPerPart(self, ChordsMeasure, NotesMeasure):
        Parts = NotesMeasure.recurse().getElementsByClass(m21.stream.Part)
        parts_flat = [part.flat.notesAndRests for part in Parts]
        notesPerChordBeatPerPart = [[[real_note for real_note in part if chord.beat == real_note.beat] for part in parts_flat] for chord in ChordsMeasure.recurse().getElementsByClass('GeneralNote')]
        return notesPerChordBeatPerPart


    def detectCadences(self):
        print("Detecting cadences...")
        fileName = self.fileName.replace(".", "_")
        FullPath = os.path.join(self.WritePath, fileName)
        text_file = open(f"{FullPath}_Analyzed.txt", "w")
        print(f"NumMeasures: {self.NumMeasures}", file=text_file)
        text_fileOffsets = open(f"{FullPath}_Analyzed_OffsetsNums.txt", "w")
        text_fileTransitions = open(f"{FullPath}_Analyzed_Transitions.txt", "w")

        measuresSecondsMap = list(filter(lambda d: d['durationSeconds'] > 0, self.ChordStreamRestless.secondsMap))

        prevState = []
        repeat_counter = 0
        incomplete_counter = 0
        empty_measure_counter = 0
        coefs_per_measure = []

        # check first timesig
        measure_zero = self.ChordStream.measure(0)
        curr_time_sig = self.check_and_update_timesig(measure_zero, [])

        # loop on measures:
        try:
            for currMeasureIndex in range(0,self.NumMeasures):
                # debug per measure
                if currMeasureIndex == 47:
                    bla = 0
                # true measures start with 1, pickups will start from zero, but not all corpora will abide to this
                # for example, data that originates from midi cannot contain this info
                # to overcome this, we attempt to find the pickup via initial rests and discard it
                # also, we count the empty measures and index them out while writing the label
                measure_number = currMeasureIndex + 1
                # print(f"measure number {measure_number}")
                CurrMeasuresRestless = self.ChordStreamRestless.measure(measure_number)
                CurrMeasures = self.ChordStream.measure(measure_number)
                CurrMeasuresNotes = self.NoteStream.measure(measure_number)
                CurrMeasureBass = self.BassChords.measure(measure_number)

                # check and update timesig
                curr_time_sig = self.check_and_update_timesig(CurrMeasures, curr_time_sig)

                # reset state machines after repeat brackets (TBD  - add double barlines to this)
                if currMeasureIndex > 0 and self.FinalBarlines[currMeasureIndex-1]:
                    self.HarmonicStateMachine.reset()
                    self.HarmonicStateMachineChallenger.reset()

                if self.EmptyMeasures[currMeasureIndex]:
                    empty_measure_counter = empty_measure_counter + 1
                    continue

                if self.IncompleteMeasures[currMeasureIndex]:
                    incomplete_counter = incomplete_counter + 1

                if not CurrMeasures or not CurrMeasuresRestless:
                    continue

                NotesPerChordBeatPerPart = self.getNotesPerChordBeatPerPart(CurrMeasures, CurrMeasuresNotes)

                AlbertiBeats4 = self.detectAlbertiOrArpeggioBassInMeasure(CurrMeasuresRestless, CurrMeasureBass, pattern_len=4, arp_type='alberti')
                AlbertiBeats = AlbertiBeats4
                if curr_time_sig.ratioString in ['3/4', '6/8', '3/8']:
                    AlbertiBeats6 = self.detectAlbertiOrArpeggioBassInMeasure(CurrMeasuresRestless, CurrMeasureBass, pattern_len=6, arp_type='alberti')
                    AlbertiBeats = [x or y for (x, y) in zip(AlbertiBeats4, AlbertiBeats6)]

                ArpeggioBeats4 = self.detectAlbertiOrArpeggioBassInMeasure(CurrMeasuresRestless, CurrMeasureBass, pattern_len=4, arp_type='arp_up')
                ArpeggioBeats = ArpeggioBeats4
                if curr_time_sig.ratioString in ['3/4', '6/8', '3/8']:
                    ArpeggioBeats3 = self.detectAlbertiOrArpeggioBassInMeasure(CurrMeasuresRestless, CurrMeasureBass, pattern_len=3, arp_type='arp_up')
                    ArpeggioBeats = [x or y for (x, y) in zip(ArpeggioBeats3, ArpeggioBeats4)]

                LyricPerBeat = []

                if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or\
                        self.KeyDetectionMode==CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                    #smooth keys here, per measure (TBD - per chord?):
                    self.smoothKeyInterpretations(currMeasureIndex)
                    #sort and return top 2
                    self.Top2Keys = self.getTopNKeyInterpretations(2)
                else:
                    currKey = self.KeyPerMeasure[currMeasureIndex]#lists start with 0

                for thisChord, thisChordWithBassRests, alberti, arpeggio, thisRealNotes in zip(CurrMeasuresRestless.recurse().getElementsByClass('GeneralNote'),CurrMeasures.recurse().getElementsByClass('GeneralNote'), AlbertiBeats, ArpeggioBeats, NotesPerChordBeatPerPart):
                    if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or\
                            self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                        currKeyString = self.Top2Keys[0][0]
                        currKey = m21.key.Key(currKeyString)
                        challengerKeyString = self.Top2Keys[1][0]
                        challengerKey = m21.key.Key(challengerKeyString)
                        self.updateKeysAndSwapStateMachines(currKeyString, challengerKeyString)

                    # main key state machine
                    if thisChordWithBassRests.isRest:
                        self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, thisChordWithBassRests, [], [], [], alberti, arpeggio, [], thisRealNotes)
                    else:
                        rn = m21.roman.romanNumeralFromChord(thisChordWithBassRests, currKey)
                        self.HarmonicStateMachine.updateHarmonicState(currKey, thisChord, thisChordWithBassRests, rn.scaleDegree, rn.inversion(), rn.figure, alberti, arpeggio, rn, thisRealNotes)

                    # challenger key state machine
                    if self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothing or self.KeyDetectionMode == CDKeyDetectionModes.KSWithSmoothingCadenceSensitive:
                        if thisChordWithBassRests.isRest:
                            self.HarmonicStateMachineChallenger.updateHarmonicState(challengerKey, thisChord, thisChordWithBassRests, [], [], [], alberti, arpeggio, [], thisRealNotes)
                        else:
                            rn2 = m21.roman.romanNumeralFromChord(thisChordWithBassRests, challengerKey)
                            self.HarmonicStateMachineChallenger.updateHarmonicState(challengerKey, thisChord, thisChordWithBassRests, rn2.scaleDegree, rn2.inversion(), rn2.figure, alberti, arpeggio, rn2, thisRealNotes)

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

                        resort = False
                        for cad in self.ReenforcementFactors:
                            if cad in Lyric:
                                self.reenforceKeyByFactor(currKeyString, self.ReenforcementFactors[cad])
                            # Challenger Check (for key switching, but ignore HCs in subdominant key (becuase they are more likely PACs in main key))
                            if cad in LyricChallenger:
                                reenforce =  not (challengerKey.tonic.pitchClass == self.getSubDominantPitchClass(currKey) and (cad == 'HC')) # and not (challengerKey.tonic.pitchClass == currKey.getDominant().pitchClass and (cad == 'PAC'))
                                if reenforce:
                                    self.reenforceKeyByFactor(challengerKeyString, self.ReenforcementFactors[cad])
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

                #if self.HarmonicStateMachine.PACPending and len(LyricPerBeat) > 0:  # PAC reversion at end of measure in case PAC state was not exited within the measure
                #    for i,curr_tup in enumerate(LyricPerBeat):
                #        if 'PAC' in curr_tup[1]:
                #            UpdatedLyric = "IAC"
                #            LyricPerBeat[i] = [curr_tup[0], UpdatedLyric]
                #            print("Reverting last PAC to IAC")

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
                        # incomplete and empty counters count measures that should be discarded
                        measure_to_write = measure_number - self.hasPickupMeasure - empty_measure_counter
                        print('Measure ', measure_to_write, ' offset ', measuresSecondsMap[currMeasureIndex]['offsetSeconds'], " ", Lyric)
                        print(f"Measure: {measure_to_write} Offset: {measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {Lyric}", file=text_file)
                        print(f"{measure_to_write} {measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {CadStringToNumMap[CadString]}", file=text_fileOffsets)
                    elif "Key" in Lyric:
                        print(Lyric)

                # ONLY NOW update repeat counter!!
                repeat_counter = repeat_counter + self.RepeatedMeasureByVolta[currMeasureIndex]

                    # save transitions to file regardless of Lyrics
                    # if prevState != self.HarmonicStateMachine.getCadentialOutput().value:
                    #    print(f"{measuresSecondsMap[currMeasureIndex]['offsetSeconds']} {self.HarmonicStateMachine.getCadentialOutput().value}", file=text_fileTransitions)
                    # prevState = self.HarmonicStateMachine.getCadentialOutput().value
                    # thisChord.lyric = str("block ") + str(i)

                # === for debugging measure number problems
                #LyricPerBeat.append((1,str(currMeasureIndex)))
                # === for debugging key shifting
                #currKeyString = self.Top2Keys[0][0]
                #challengerKeyString = self.Top2Keys[1][0]
                #LyricPerBeat.append((1, f'{currKeyString} {self.CurrSmoothedInterpretations[currKeyString]}'))
                #LyricPerBeat.append((1, f'{challengerKeyString} {self.CurrSmoothedInterpretations[challengerKeyString]}'))

                # write coefs per measure for offline analysis
                coefs_per_measure.append(copy.deepcopy(self.CurrSmoothedInterpretations))

                Parts = CurrMeasuresNotes.recurse().getElementsByClass(m21.stream.Part)
                Lyrics_to_filter = ['CA'] # for filtering the display
                for thisLyric in LyricPerBeat:
                    if thisLyric[1] not in Lyrics_to_filter:
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
        except:
            print(f"Exception occurred on measure {measure_number}")
            raise

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
            CoefsFile = f"{FullPath}_Coefs_{self.KeyDetectionMode}.txt"
            with open(CoefsFile, 'wb') as f:
                pickle.dump(coefs_per_measure, f)

    def check_and_update_timesig(self, CurrMeasures, measure_time_sig):
        if CurrMeasures:
            for timeSig in CurrMeasures.recurse().getElementsByClass(m21.meter.TimeSignature):
                measure_time_sig = timeSig
                if timeSig != self.HarmonicStateMachine.CurrHarmonicState.TimeSig:
                    self.HarmonicStateMachine.CurrHarmonicState.TimeSig = timeSig
                    self.HarmonicStateMachineChallenger.CurrHarmonicState.TimeSig = timeSig
        return measure_time_sig

    def getSubDominantPitchClass(self, currKey):
        return (currKey.getDominant().pitchClass - 2) % 12

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
        max_num_measures_for_writing = 400
        if self.NumMeasures <= max_num_measures_for_writing:
            fileName = self.fileName.replace(".", "_")
            fileName = (f"{fileName}_Analyzed.xml")
            FullPath = os.path.join(self.WritePath, fileName)
            self.NoteStream.write(fp=FullPath)
        else:
            print(f'file too long for writing. Max num measures for writing is {max_num_measures_for_writing}.'
                  f'Num measures is:', self.NumMeasures)

    def displayFull(self):
        self.NoteStream.show()

    def setWritePath(self,path):
        self.WritePath = path
