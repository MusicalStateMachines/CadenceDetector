from .CadenceDetectData import *
from music21 import *
import numpy as np
import copy

class CDStateMachine(object):
    def __init__(self, isChallenger=False, minInitialMeasures=0, minPostCadenceMeasures=0):
        self.NumParts = 0
        self.MeasureCounter = 0 # measure counter is for the entire movement and not included in reset
        self.MinInitialMeasures = {CDCadentialStates.PACArrival: minInitialMeasures, CDCadentialStates.IACArrival: minInitialMeasures, CDCadentialStates.HCArrival: round(minInitialMeasures/2)}
        self.MinPostCadenceMeasures = minPostCadenceMeasures
        self.MinPostCadenceMeasuresHC = max(1, minPostCadenceMeasures)
        self.IsChallenger = isChallenger
        self.reset()

    def reset(self):
        # initiliaze with invalid states
        self.PrevCadentialState = CDCadentialStates.Idle
        self.CurrCadentialState = CDCadentialStates.Idle
        self.CurrCadentialOutput = CDCadentialStates.Idle
        self.CurrHarmonicState = CDHarmonicState([], chord.Chord(), chord.Chord(), 0, 0, 0, 0, 0, meter.TimeSignature(), [], [])
        self.PrevHarmonicState = self.CurrHarmonicState
        self.LastNonAlbertiHarmonicState = self.CurrHarmonicState
        self.ChangeFlagOneShot = 0
        self.KeyChangeOneShot = 0
        self.FirstKeyDetectionDone = 0
        self.CadentialKeyChange = 0
        self.TriggerString = str("")
        self.PostPACMeasureCounter = self.MinPostCadenceMeasures
        self.PostHCMeasureCounter = self.MinPostCadenceMeasuresHC
        self.CheckBassPartFromChord = False
        self.PACPending = False
        self.RevertLastPAC = False
        self.HCPending = False
        self.RevertLastHC = False
        self.RevertLastIAC = False
        self.HarmonicStateOfLastCadence = 0
        self.SopranoOfLastCadence = 0
        self.WeightOfLastCadence = 0
        self.PrevMeasureAlberti = False
        self.PrevMeasureArpeggio = False
        self.IsPickupMeasure = False

    def resetPostCadentialCounters(self):
        self.PostPACMeasureCounter = self.MinPostCadenceMeasures
        self.PostHCMeasureCounter = self.MinPostCadenceMeasuresHC

    def updateHarmonicState(self, Key, Chord, ChordWithRests, ChordDegree, ChordInversion, ChordFigure, Alberti, Arpeggio, RomamNumeral, RealNotes):

        if not (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
            self.LastNonAlbertiHarmonicState = copy.deepcopy(self.CurrHarmonicState)
        self.PrevHarmonicState = copy.deepcopy(self.CurrHarmonicState)
        self.KeyChangeOneShot = 0
        if self.CurrHarmonicState.Key and self.CurrHarmonicState.Key != Key:
            self.KeyChangeOneShot = 1
        self.CurrHarmonicState.Key = Key
        self.CurrHarmonicState.Chord = Chord
        self.CurrHarmonicState.ChordWithBassRests = ChordWithRests
        self.CurrHarmonicState.ChordDegree = ChordDegree
        self.CurrHarmonicState.ChordInversion = ChordInversion
        self.CurrHarmonicState.ChordFigure = ChordFigure
        self.CurrHarmonicState.Alberti = Alberti
        self.CurrHarmonicState.Arpeggio = Arpeggio
        self.CurrHarmonicState.RomanNumeral = RomamNumeral
        self.CurrHarmonicState.RealNotes = RealNotes
        if not self.IsPickupMeasure:
            self.updateCounters()
        self.updateCadentialState()

    def checkStateChanged(self):
        self.ChangeFlagOneShot = 0
        if self.PrevCadentialState != self.CurrCadentialState:
            self.ChangeFlagOneShot = 1
            self.TriggerString = str("T") + str(self.PrevCadentialState.value) + str(u'\u208B') + str(self.CurrCadentialState.value)
            self.TriggerString = self.TriggerString.translate(SUB)
            self.PrevCadentialState = self.CurrCadentialState
            if self.CurrCadentialState == CDCadentialStates.PACArrival or self.CurrCadentialState == CDCadentialStates.PCCArrival:
                self.PostPACMeasureCounter = -1
            elif self.CurrCadentialState == CDCadentialStates.HCArrival or self.CurrCadentialState == CDCadentialStates.PCHArrival:
                self.PostHCMeasureCounter = -1

    def getBassFromChord(self, chord, favor_by_part=False):
        retVal = False
        if not chord.isRest:
            # first checking the bass part (even if it is not the lowest note in the chord)
            for p in chord:
                if 'MyBasso' in p.groups:
                    if not retVal or p.pitch.midi < retVal.midi:
                        retVal = p.pitch
            if not favor_by_part or not retVal:
                # now checking the lowest pitch while verifying an octave below soprano
                sorted_pitches = chord.sortFrequencyAscending().pitches
                lowestPitch = sorted_pitches[0]
                # if MyBasso not found or if it was found but it isn't the lowest pitch
                if not retVal or retVal.midi > lowestPitch.midi:
                    highestPitch = sorted_pitches[-1]
                    # this is an ugly hack to overcome the cases where part id is lost in chordify
                    if (highestPitch.midi-lowestPitch.midi) > 11 or lowestPitch.midi <= 72:
                        retVal = lowestPitch
        return retVal

    def compareBassWithPitch(self, pitchClass, mode='any', favor_by_part=False, HarmonicState=None):
        if HarmonicState is None:
            HarmonicState = self.CurrHarmonicState
        retVal = False
        bassPitch = []
        if mode in ['any', 'restless']:
            if not retVal:
                bassPitch = self.getBassFromChord(HarmonicState.Chord, favor_by_part=favor_by_part)
                if bassPitch:
                    retVal = bassPitch.pitchClass==pitchClass
        if mode in ['any', 'orig']:
            if not bassPitch:
                bassPitch = self.getBassFromChord(HarmonicState.ChordWithBassRests, favor_by_part=favor_by_part)
                if bassPitch:
                    retVal = bassPitch.pitchClass==pitchClass
        return retVal

    def isSopranoOnDegree(self, deg):
        retVal = 0
        if not self.CurrHarmonicState.Chord.isRest:
            if not isinstance(deg, list):
                deg = [deg]
            for curr_deg in deg:
                target_pitch_class = self.CurrHarmonicState.Key.pitchFromDegree(curr_deg).pitchClass
                if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == target_pitch_class:
                    retVal = 1
                    #check for voice crossing of other voices
                elif self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1].pitchClass == target_pitch_class:
                    retVal = 1
                    #in multipart scores, check for explicit soprano
                elif self.NumParts > 2:
                    sopranoPartPitch = self.getSopranoPartPitch(self.CurrHarmonicState)
                    if sopranoPartPitch and sopranoPartPitch.pitchClass == target_pitch_class:
                        retVal = 1
                if retVal:
                    break
        return retVal

    def getSopranoPartPitch(self, HarmonicState):
        retVal  = 0
        if not HarmonicState.Chord.isRest:
            for p in HarmonicState.Chord.pitches:
                if 'MySoprano' in p.groups:
                    retVal = p
                    break
        return retVal

    def getSopranoPitch(self, HarmonicState):
        retVal = 0
        if not HarmonicState.Chord.isRest:
            retVal = HarmonicState.Chord.sortFrequencyAscending().pitches[-1]
        return retVal

    def getCurrSopranoPitch(self):
        return self.getSopranoPitch(self.CurrHarmonicState)

    def getPrevSopranoPitch(self):
        return self.getSopranoPitch(self.PrevHarmonicState)

    def isSopranoAtSemitoneFromDegree(self, n_semitones, deg):
        retVal = 0
        if not isinstance(deg, list):
            deg = [deg]
        for curr_deg in deg:
            if abs(self.CurrHarmonicState.Chord.pitches[-1].pitchClass - self.CurrHarmonicState.Key.pitchFromDegree(curr_deg).pitchClass) == n_semitones:
                 retVal = 1
                 #check for voice crossing of other voices
            elif abs(self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1].pitchClass - self.CurrHarmonicState.Key.pitchFromDegree(curr_deg).pitchClass) == n_semitones:
                 retVal = 1
            else:
                for p in self.CurrHarmonicState.Chord.pitches:
                    if abs(p.pitchClass - self.CurrHarmonicState.Key.pitchFromDegree(curr_deg).pitchClass) == n_semitones and 'MySoprano' in p.groups:
                        retVal = 1
                        break
            if retVal:
                break
        return retVal

    def isPartInChord(self, chord, partString):
        retVal = 0
        for p in chord.pitches:
            if partString in p.groups:
                retVal = 1
                break
        return retVal

    def getPartPitchFromChord(self, chord, partString):
        retPitch = 0
        for p in chord.pitches:
            if partString in p.groups:
                retPitch = p
                break
        return retPitch

    def isDominantBass(self, favor_by_part=False, HarmonicState=None):
        if HarmonicState is None:
            HarmonicState = self.CurrHarmonicState
        dominantPitchClass = HarmonicState.Key.pitchFromDegree(5).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.compareBassWithPitch(dominantPitchClass, mode='any', favor_by_part=favor_by_part, HarmonicState=HarmonicState)
        return retVal

    def isSubDominantBass(self, favor_by_part=False):
        subDominantPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(4).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.compareBassWithPitch(subDominantPitchClass, mode='any', favor_by_part=favor_by_part)
        return retVal

    def isMediantBass(self, favor_by_part=False):
        dominantPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.compareBassWithPitch(dominantPitchClass, mode='any', favor_by_part=favor_by_part)
        return retVal

    def isTonicBass(self):
        tonicPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass
        retVal = self.compareBassWithPitch(tonicPitchClass, mode='any', favor_by_part=True)
        return retVal

    def harmonyHasSeventh(self, HarmonicState):
        return self.harmonyContainsPitchDegree(HarmonicState=HarmonicState, degree=4)
        #return not (HarmonicState.Chord.seventh is None)

    def harmonyHasTonic(self,  HarmonicState):
        return self.harmonyContainsPitchDegree(HarmonicState=HarmonicState, degree=1)

    def harmonyHasMediant(self, HarmonicState):
        return self.harmonyContainsPitchDegree(HarmonicState=HarmonicState, degree=3)

    def isI64(self, HarmonicState):
        return self.harmonyContainsOnlyPitchDegrees(HarmonicState=HarmonicState, degrees=[1, 3, 5]) and\
               (self.harmonyHasTonic(HarmonicState) or self.harmonyHasMediant(HarmonicState)) and\
               self.isDominantBass(HarmonicState=HarmonicState)

    def harmonyContainsOnlyPitchDegrees(self, HarmonicState, degrees):
        pitch_classes = [HarmonicState.Key.pitchFromDegree(degree).pitchClass for degree in degrees]
        return self.harmonyContainsOnlyPitchClasses(HarmonicState=HarmonicState, pitch_classes=pitch_classes)

    def harmonyContainsOnlyPitchClasses(self, HarmonicState, pitch_classes):
        retVal = True
        if not HarmonicState.ChordWithBassRests.isRest:
            for p in HarmonicState.ChordWithBassRests.pitches:
                if p.pitchClass not in pitch_classes:
                    retVal = False
                    break
        return retVal

    def isDominantHarmony(self, HarmonicState):
        dominant_harmony_degrees = [5, 2, 4] # first without leading tone
        pitch_classes = [HarmonicState.Key.pitchFromDegree(degree).pitchClass for degree in dominant_harmony_degrees]
        leading_tone_pitch_class = HarmonicState.Key.pitchFromDegree(7).pitchClass
        if HarmonicState.Key.mode == 'minor':
            leading_tone_pitch_class = (leading_tone_pitch_class + 1) % 12 # raise the leading tone
        pitch_classes.append(leading_tone_pitch_class)
        return self.harmonyContainsOnlyPitchClasses(HarmonicState=HarmonicState, pitch_classes=pitch_classes)

    def harmonyContainsPitchDegree(self, HarmonicState, degree):
        retVal = False
        if not HarmonicState.ChordWithBassRests.isRest:
            PitchClass = HarmonicState.Key.pitchFromDegree(degree).pitchClass
            retVal = PitchClass in [p.pitchClass for p in HarmonicState.ChordWithBassRests.pitches]
        return retVal

    def isLeadingToneSoprano(self):
        interval_to_tonic = self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1].pitchClass - self.CurrHarmonicState.Key.tonic.pitchClass
        return interval_to_tonic % 12 == 11

    def isSopranoOnSemitonesFromTonic(self, intervalsFromTonic):
        interval_to_tonic = self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1].pitchClass - self.CurrHarmonicState.Key.tonic.pitchClass
        return interval_to_tonic % 12 in intervalsFromTonic

    def isLeadingToneBass(self):
        retVal = False
        bassPitch = self.getBassFromChord(self.CurrHarmonicState.Chord, favor_by_part=True)
        if not bassPitch:
            bassPitch = self.getBassFromChord(self.CurrHarmonicState.ChordWithBassRests, favor_by_part=True)
        if bassPitch:
            interval_to_tonic = bassPitch.pitchClass - self.CurrHarmonicState.Key.tonic.pitchClass
            retVal = interval_to_tonic % 12 == 11
        return retVal

    def isRootedHarmony(self):
        return self.compareBassWithPitch(self.CurrHarmonicState.Chord.root().pitchClass, mode='any')

    def isSecondaryDominantLeadingTone(self):
        retVal= 0
        Fourth = self.CurrHarmonicState.Key.pitchFromDegree(4)
        RaisedFourth = pitch.Pitch(midi=Fourth.midi+1)
        pSecondaryLeadingTone = RaisedFourth.pitchClass
        if not self.CurrHarmonicState.Chord.isRest:
            for p in self.CurrHarmonicState.Chord.pitches:
                if p.pitchClass == pSecondaryLeadingTone:
                    retVal = 1
                    break
        return retVal

    def isSecondaryDominantUpperLeadingTone(self):
        retVal= 0
        if not self.CurrHarmonicState.Chord.isRest:
            Fifth = self.CurrHarmonicState.Key.pitchFromDegree(5)
            RaisedFifth = pitch.Pitch(midi=Fifth.midi+1)
            pSecondaryDominantUpperLeadingTone = RaisedFifth.pitchClass
            for p in self.CurrHarmonicState.Chord.pitches:
                if p.pitchClass == pSecondaryDominantUpperLeadingTone:
                    retVal = 1
                    break
        return retVal

    def isDominantEmbellishment(self):
        retVal = 0
        VpitchClass = self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass
        if self.CurrHarmonicState.Key.mode == 'major':
            # Vb,V#,VIIb,IIb,II#
            embellishment_offsets = [-1, 1, 3, 6, 8]
        else:
            # Vb,V#,VIIb,IIb
            embellishment_offsets = [-1, 1, 3, 6]
        embellishments = [(VpitchClass + eo) % 12 for eo in embellishment_offsets]
        if not self.CurrHarmonicState.Chord.isRest:
            for p in self.CurrHarmonicState.Chord.pitches:
                if p.pitchClass in embellishments:
                    retVal = 1
                    break
        return retVal

    def isVMajorExclusive(self, HarmonicState):
        retVal = 1
        VpitchClass = self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass
        # V,VII,II
        major_triad_offsets = [0, 4, 7]
        VchordPitchClass = [(VpitchClass + mto) % 12 for mto in major_triad_offsets]
        if not HarmonicState.Chord.isRest:
            for p in HarmonicState.Chord.pitches:
                if p.pitchClass not in VchordPitchClass:
                    retVal = 0
                    break
        return retVal

    def verifyHCHarmony(self, HarmonicState):
        return self.isVMajorExclusive(HarmonicState)

    def isTonicHarmony(self, HarmonicState):
        retVal = 1
        IpitchClass = self.CurrHarmonicState.Key.tonic.pitchClass
        if HarmonicState.Key.mode == 'major':
            # major triad
            tonic_triad_offsets = [0, 4, 7]
        else:
            # minor triad
            tonic_triad_offsets = [0, 3, 7]
        IchordPitchClass = [(IpitchClass + mto) % 12 for mto in tonic_triad_offsets]
        if not HarmonicState.Chord.isRest:
            for p in HarmonicState.Chord.pitches:
                if p.pitchClass not in IchordPitchClass:
                    retVal = 0
                    break
        return retVal

    def isUnison(self):
        retVal = 1
        Pitch0 = self.CurrHarmonicState.Chord.pitches[0].pitchClass
        for p in self.CurrHarmonicState.Chord.pitches:
            if p.pitchClass != Pitch0:
                retVal = 0
                break
        return retVal

    def numTonics(self):
        nTonics = 0
        pTonic = self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass
        for p in self.CurrHarmonicState.Chord.pitches:
            if p.pitchClass == pTonic:
                nTonics = nTonics + 1
        print("nTonics:",nTonics)
        return nTonics

    def tryGetBeatStrength(self):
        retVal = 0
        try:
            retVal = self.CurrHarmonicState.Chord.beatStrength
        except:
            retVal = 0
            print('error: could not get beat strength. Returning 0')
        return retVal

    def verifyPACGrouping(self, HarmonicState):
        return self.verifyGrouping(HarmonicState=HarmonicState, start_stop='any') or self.tryGetBeatStrength()==1.0

    def verifyIACGrouping(self, HarmonicState):
        return self.verifyGrouping(HarmonicState=HarmonicState, start_stop='stop')

    def verifyHCGrouping(self, HarmonicState, start_stop='stop'):
        beatStrength = self.tryGetBeatStrength()
        return beatStrength == 1.0 or\
               (beatStrength >= 0.5 and self.verifyGrouping(HarmonicState=HarmonicState, start_stop='any')) or\
               (beatStrength >= 0.25 and self.verifyGrouping(HarmonicState=HarmonicState, start_stop='stop'))

    def verifyCadenceVoiceLeading(self, prev_soprano_pitch, curr_soprano_pitch, cadence_type='PAC'):
        retVal = True
        if curr_soprano_pitch and prev_soprano_pitch:
            midi_diff = curr_soprano_pitch.midi - prev_soprano_pitch.midi
            allowed_interval_table = {'PAC': np.array([0, 1, -2, -3, -4, 5, -7]), # anticipated tonic, minor second up, major second down, major/minor third down, fourth up, fifth down
                                      'IAC': np.array([0, 1, 2, 3, 4, -1, -2, -3, -4, 5]),  # anticipated third or fifth, major/minor second up, major/minor second down, major/minor third up and down, fourth up
                                      'HC': np.array([0, 1, 2, -1, -2, -3, -5, -7])}
            allowed_intervals = allowed_interval_table[cadence_type]
            allowed_intervals_full = np.concatenate((allowed_intervals, allowed_intervals-12, allowed_intervals+12)) # check also an octave down and up, Mozart K533-1, Haydn17_3_4
            retVal = midi_diff in allowed_intervals_full
        return retVal

    def verifySopranoVoiceLeading(self, cadence_type='PAC'):
        curr_soprano_pitch = self.getSopranoPitch(self.CurrHarmonicState)
        prev_soprano_pitch = self.getSopranoPitch(self.PrevHarmonicState)
        retVal = self.verifyCadenceVoiceLeading(prev_soprano_pitch, curr_soprano_pitch, cadence_type=cadence_type)
        if not retVal:
            curr_soprano_pitch = self.getSopranoPartPitch(self.CurrHarmonicState)
            prev_soprano_pitch = self.getSopranoPartPitch(self.PrevHarmonicState)
            retVal = self.verifyCadenceVoiceLeading(prev_soprano_pitch, curr_soprano_pitch, cadence_type=cadence_type)
        return retVal

    def verifyGrouping(self, HarmonicState, start_stop='any'):
        search_sign = {'start': ['{'], 'stop': ['}'], 'any': ['{','}']}
        for real_part in HarmonicState.RealNotes:
            for note in real_part:
                for sign in search_sign[start_stop]:
                    if sign in note.groups:
                        return True
        return False

    def verifySopranoGrouping(self, HarmonicState, start_stop='any'):
        search_sign = {'start': ['{'], 'stop': ['}'], 'any': ['{', '}']}
        retVal  = False
        highest_pitch_midi = 0
        for real_part in HarmonicState.RealNotes:
            for note in real_part:
                if note.isChord:
                    curr_note = note.sortFrequencyAscending()[-1]
                else:
                    curr_note = note
                if curr_note.pitch.midi >= highest_pitch_midi:
                    highest_pitch_midi = curr_note.pitch.midi
                    for sign in search_sign[start_stop]:
                        retVal = sign in note.groups
        return retVal

    def isBassPartRest(self):
        retVal = True
        # serach for explicit rest in bass part
        bass_part = self.CurrHarmonicState.RealNotes[-1]
        if len(bass_part) == 0:
            retVal = False
        else:
            for noteOrRest in bass_part:
                if not noteOrRest.isRest:
                    retVal = False
                    break
        return retVal


    def updateCadentialState(self):

        curr_state = self.CurrCadentialState #set to temp variable for clean code

        # ====on key change, return to Cadence expected, not idle since the key change itself creates the initial tension
        if self.KeyChangeOneShot==1:
            curr_state = CDCadentialStates.CadExpected

        # ===============================================
        # ====idle state, wait for IV or II6 or I6=======
        # ===============================================
        if curr_state == CDCadentialStates.Idle:
            if (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                # do nothing
                curr_state = curr_state
            elif self.CurrHarmonicState.ChordWithBassRests.isRest and not self.PrevHarmonicState.Chord.isRest and not self.IsChallenger:
                if self.tryGetBeatStrength() < 1.0:
                    #if sudden rest and not on strongest beat, check if previous harmony could have been HC
                    if isinstance(self.PrevHarmonicState.Key, key.Key):
                        if self.verifyHCGrouping(HarmonicState=self.PrevHarmonicState) and self.verifyHCHarmony(HarmonicState=self.PrevHarmonicState):
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                        else:
                            curr_state = curr_state
                else:
                    curr_state = curr_state
            elif self.isDominantEmbellishment() and not self.IsChallenger:# this can create false HCs, need to consider non-cadential chromatic situations
                curr_state = CDCadentialStates.HCArrivalExpected
            elif self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = curr_state
            elif self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(4).pitchClass, mode='any'):
                #== bass in 4th degree - IV or II6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(6).pitchClass, mode='any'):
                #== bass in 6th degree - VI or IV6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif self.tryGetBeatStrength() >= 0.5 and self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass, mode='any'):
                #== bass in 3rd degree - iii or I6 on strong beat go to expecting cadence
                curr_state = CDCadentialStates.CadExpected

        # ===================================================
        # ====expecting cadence, wait for V Dominant=========
        # ===================================================
        elif curr_state == CDCadentialStates.CadExpected or curr_state == CDCadentialStates.CadAvoided or curr_state == CDCadentialStates.IACArrival:
            # only stay in CadAvoided once (currently for display purposes)
            if curr_state == CDCadentialStates.CadAvoided:
                curr_state = CDCadentialStates.CadExpected
            elif curr_state == CDCadentialStates.IACArrival and not (self.isTonicBass() and self.isSopranoOnDegree(1)):
                curr_state = CDCadentialStates.CadExpected
            elif curr_state == CDCadentialStates.IACArrival and self.tryGetBeatStrength() == 1:
                curr_state = CDCadentialStates.CadExpected
            # now start the real state logic
            # === Revert IAC to PAC  - this catches some debatable PACs and also False Positives
            #if curr_state == CDCadentialStates.IACArrival and (self.isTonicBass() and self.isSopranoOnDegree(1)):
            #    self.RevertLastIAC = True
            #    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state, verify_beat_strength=False)
            if self.isDominantEmbellishment():
                curr_state = CDCadentialStates.HCArrivalExpected
            elif self.CurrHarmonicState.ChordWithBassRests.isRest and not self.PrevHarmonicState.Chord.isRest and not self.IsChallenger:
                if self.tryGetBeatStrength() < 1.0:
                    # if sudden rest and not on strongest beat, check if previous harmony could have been HC
                    if isinstance(self.PrevHarmonicState.Key, key.Key):
                        if self.verifyHCGrouping(HarmonicState=self.PrevHarmonicState) and self.verifyHCHarmony(HarmonicState=self.PrevHarmonicState):
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                        else:
                            curr_state = curr_state
                else:
                    curr_state = curr_state
            #ignoring arppegios
            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                #if alberti or arpeggio bass unless explicit V chord
                if self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState) and self.harmonyHasSeventh(self.CurrHarmonicState):
                    curr_state = CDCadentialStates.CadInevitable
                else:
                    curr_state = curr_state
            elif self.isDominantBass() and self.harmonyHasSeventh(self.CurrHarmonicState):
                curr_state = CDCadentialStates.CadInevitable
            elif self.isTonicBass():
                curr_state = CDCadentialStates.HCArrivalExpected
            elif self.isDominantBass(favor_by_part=True):
                if self.verifySopranoVoiceLeading(cadence_type='HC') and \
                    ((self.tryGetBeatStrength()==1 and self.verifyHCGrouping(HarmonicState=self.CurrHarmonicState)) or
                     self.verifyHCGrouping(HarmonicState=self.CurrHarmonicState, start_stop='stop')):
                    if self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                    elif self.harmonyHasTonic(self.CurrHarmonicState) or self.harmonyHasMediant(self.CurrHarmonicState):
                        curr_state = CDCadentialStates.HCAppoggExpected
                    else:
                        curr_state = CDCadentialStates.CadInevitable
                else:
                    curr_state = CDCadentialStates.CadInevitable


        # ========================================================
        # ====inevitable cadence (PAC or IAC), wait for Is========
        # ========================================================
        elif curr_state==CDCadentialStates.CadInevitable or curr_state==CDCadentialStates.IACArrivalExpected:
            # on dominant and then a complete rest --> HC with constraints
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                if self.verifySopranoVoiceLeading(cadence_type='HC') and\
                        self.verifyHCGrouping(HarmonicState=self.PrevHarmonicState) and\
                        self.verifyHCHarmony(HarmonicState=self.PrevHarmonicState):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                else:
                    curr_state = curr_state
            # on dominant and then bass rest --> HC with constraints
            elif self.isBassPartRest() and\
                    self.isDominantBass(favor_by_part=True) and\
                    self.verifyHCGrouping(HarmonicState=self.CurrHarmonicState) and\
                    self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState):
                curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
            elif self.isDominantEmbellishment():
                curr_state = CDCadentialStates.HCArrivalExpected
            elif (self.isI64(HarmonicState=self.CurrHarmonicState) and not self.isBassPartRest()):
                curr_state = CDCadentialStates.HCArrivalExpected
            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                #if alberti and weak beat do nothing
                curr_state = curr_state
            else:
                # for the case where in IAC expected and dominant appears again, back to Cad inevitable
                if curr_state==CDCadentialStates.IACArrivalExpected and self.isDominantBass(favor_by_part=True) and not self.isBassPartRest():
                    curr_state = CDCadentialStates.CadInevitable
                # meter - look for cadences on strong beat:
                elif self.tryGetBeatStrength() >= 0.25:#cadence can only occur on strong beats
                    # harmony  - chordal degree and bass analysis
                    # bass rest on strong beat --> HC
                    if self.isDominantBass(favor_by_part=True) and\
                            self.isBassPartRest() and\
                            self.tryGetBeatStrength() < 1.0 and\
                            self.verifyHCGrouping(self.CurrHarmonicState) and\
                            self.verifyHCHarmony(self.CurrHarmonicState) and\
                            self.verifySopranoVoiceLeading(cadence_type='HC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                    elif self.isTonicBass():
                        # harmony  - chordal inversion
                        if (self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.Root.value or
                            self.isRootedHarmony() or
                            self.isTonicHarmony(HarmonicState=self.CurrHarmonicState)) and\
                                self.verifyPACGrouping(HarmonicState=self.CurrHarmonicState):
                            # ==I after V after IV or II6, cadential arrival
                            # melody  - soprano degree
                            if self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC'):
                                if curr_state==CDCadentialStates.CadInevitable:
                                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state)
                                elif self.verifySopranoVoiceLeading(cadence_type='IAC') and self.verifyIACGrouping(HarmonicState=self.CurrHarmonicState):
                                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                            #soprano not on 1, either IAC or appoggiatura
                            elif self.isSopranoOnDegree([3, 5]) and self.verifySopranoVoiceLeading(cadence_type='IAC') and self.verifyIACGrouping(HarmonicState=self.CurrHarmonicState):
                                curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                            # expecting appoggiatura on strong beats
                            elif self.tryGetBeatStrength() >= 0.5 and self.verifyPACGrouping(self.CurrHarmonicState):
                                curr_state = self.checkAppoggiaturaOrAvoidance('PAC' if curr_state==CDCadentialStates.CadInevitable else 'IAC')
                            # appogiatura can also not be detected as I
                        elif self.tryGetBeatStrength() >= 0.5 and self.verifyPACGrouping(self.CurrHarmonicState):
                            # expecting appogiaturas only on strongest beats (TBD - this might be overfit to haydn)
                            curr_state = self.checkAppoggiaturaOrAvoidance('PAC' if curr_state==CDCadentialStates.CadInevitable else 'IAC')
                    # on strong beat: going from V to anything other than V or I is avoiding the cadence or bass appoggiatura
                    elif self.tryGetBeatStrength() >= 0.5 and self.verifyPACGrouping(self.CurrHarmonicState) and self.verifySopranoVoiceLeading(cadence_type='PAC'):
                        # expecting bass appogiaturas only on strongest beats
                        curr_state = self.checkBassAppoggiatura(curr_state)
                    elif not self.isDominantBass():
                        if self.tryGetBeatStrength() >= 0.5:
                            curr_state = CDCadentialStates.CadAvoided
                        else:
                            curr_state = CDCadentialStates.CadExpected
                # on weaker beat (but not completely weak) leave this state if not dominant bass:
                elif self.tryGetBeatStrength() >= 0.1 and not self.isDominantBass() and not self.isLeadingToneBass():
                    # if we left dominant but not to I then cadence avoided, but could be HC so wait for V again - TBD, perhaps this avoidance goes further back
                    curr_state = CDCadentialStates.HCArrivalExpected

        # =============================================================================================
        # ====HC expected, V on strong beat = HC, V on weak beat, return to cadence inevitable ========
        # =============================================================================================

        elif curr_state == CDCadentialStates.HCArrivalExpected:

            if self.isDominantBass(favor_by_part=True) and self.harmonyHasSeventh(self.CurrHarmonicState):
                curr_state = CDCadentialStates.CadInevitable
            elif self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio:
                if self.isDominantBass(favor_by_part=True, HarmonicState=self.LastNonAlbertiHarmonicState) and\
                        self.harmonyHasSeventh(self.CurrHarmonicState) and\
                        not self.isDominantEmbellishment():
                    curr_state = CDCadentialStates.CadInevitable
                else:
                    curr_state = curr_state
            elif self.tryGetBeatStrength() < 0.25 and\
                    self.isDominantBass(favor_by_part=True) and \
                    self.harmonyHasSeventh(self.CurrHarmonicState) and \
                    self.isDominantHarmony(HarmonicState=self.CurrHarmonicState):#weak beat returning to dominant, return to cad inevitable
                curr_state = CDCadentialStates.CadInevitable
            elif self.CurrHarmonicState.ChordWithBassRests.isRest:
                if self.verifyHCGrouping(HarmonicState=self.PrevHarmonicState) and self.verifyHCHarmony(HarmonicState=self.PrevHarmonicState):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                else:
                    curr_state = curr_state
            elif self.tryGetBeatStrength() >= 0.25: #strong beats
                if self.isDominantBass(favor_by_part=True) and\
                        (self.verifyHCGrouping(self.CurrHarmonicState, start_stop='any') or self.tryGetBeatStrength()==1) and\
                        not self.isI64(HarmonicState=self.CurrHarmonicState) and\
                        self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState) and\
                        self.verifySopranoVoiceLeading(cadence_type='HC'):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                # appoggiatura on strongest beat, or if V64
                elif self.isDominantBass(favor_by_part=True) and\
                        (self.isI64(HarmonicState=self.CurrHarmonicState) and not self.isBassPartRest()) and\
                        self.verifyHCGrouping(self.CurrHarmonicState, start_stop='any'):
                    curr_state = CDCadentialStates.HCAppoggExpected
                elif self.isTonicBass() and self.tryGetBeatStrength() >= 0.5 and \
                        self.verifyPACGrouping(HarmonicState=self.CurrHarmonicState) and \
                        self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState) and\
                        self.isDominantHarmony(HarmonicState=self.PrevHarmonicState):
                    if self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state)
                    elif self.isSopranoOnDegree([3, 5]) and self.verifySopranoVoiceLeading(cadence_type='IAC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                    else:
                        curr_state = self.checkAppoggiaturaOrAvoidance('PAC')
                elif self.isDominantBass(favor_by_part=False) and\
                        ((self.harmonyHasSeventh(self.CurrHarmonicState) and not self.isDominantEmbellishment()) or\
                         not (self.verifyHCGrouping(self.CurrHarmonicState, start_stop='any') or self.tryGetBeatStrength()==1)): #V7 or V without grouping return to cad inevitable
                    curr_state = CDCadentialStates.CadInevitable
                elif self.isDominantBass(favor_by_part=True) and self.tryGetBeatStrength() == 1.0:#appoggiatura on strongest beat, or if V64
                    curr_state = CDCadentialStates.HCAppoggExpected
                    # HC bass appoggiatura
                elif self.tryGetBeatStrength() == 1 and self.isSopranoOnDegree([5]) and self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState) and not self.harmonyHasSeventh(self.CurrHarmonicState):
                    curr_state = CDCadentialStates.HCBassAppoggExpected
                elif not (self.isDominantBass() or self.isTonicBass() or self.isDominantEmbellishment()): #strong beat and not dominant or embellishment, cadence avoided
                    curr_state = CDCadentialStates.CadAvoided
                elif self.isDominantBass(favor_by_part=True) and self.verifyHCGrouping(HarmonicState=self.CurrHarmonicState, start_stop='any') and not self.harmonyHasSeventh(self.CurrHarmonicState):
                    curr_state = CDCadentialStates.HCAppoggExpected


        elif curr_state == CDCadentialStates.PACAppoggExpected or curr_state == CDCadentialStates.BassAppoggExpected:

            if self.CurrHarmonicState.ChordWithBassRests.isRest or (self.tryGetBeatStrength() == 1): # and not self.isTonicBass()): # rest or new measure not on tonic, exit appoggiatura:
                if self.isDominantBass():
                    if (self.verifyHCGrouping(self.CurrHarmonicState, start_stop='any') or self.tryGetBeatStrength()==1) and\
                            self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState) and\
                            self.verifySopranoVoiceLeading(cadence_type='HC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                    elif self.isI64(self.CurrHarmonicState):  # I64 can be HC appoggiaturra on dominant bass
                        curr_state = CDCadentialStates.HCArrivalExpected
                    else:
                        curr_state = CDCadentialStates.CadInevitable
                elif self.isTonicBass() and\
                        (self.CurrHarmonicState.Chord.isConsonant() or self.isTonicHarmony(HarmonicState=self.CurrHarmonicState)) and\
                        not self.harmonyContainsPitchDegree(HarmonicState=self.CurrHarmonicState, degree=6):
                    if self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC') and\
                            (not self.IsChallenger or self.verifyPACGrouping(self.CurrHarmonicState)):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state)
                    elif self.isSopranoOnDegree([3, 5]) and self.verifySopranoVoiceLeading(cadence_type='IAC') and\
                            self.verifyIACGrouping(HarmonicState=self.CurrHarmonicState):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                    else:
                        curr_state = CDCadentialStates.CadExpected
                else:
                    curr_state = CDCadentialStates.CadExpected
            else:
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
            # ==for bass appoggiatura check  that soprano is still on tonic and that bass is also.
            # ==grouping is not required becuase it was verified on the appoggiatura entrance
            # ==in case of alberti or arppeggio the original bass on entrance remains, so tonic bass verification is not required.
                if curr_state == CDCadentialStates.BassAppoggExpected and not self.isTonicBass() and (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                    curr_state = curr_state
                elif self.isTonicBass() or\
                        (curr_state == CDCadentialStates.PACAppoggExpected and (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio)) and\
                        self.CurrHarmonicState.Chord.isConsonant() and\
                        not self.harmonyContainsPitchDegree(HarmonicState=self.CurrHarmonicState, degree=6):
                    if self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC') and\
                            (not self.IsChallenger or self.verifyPACGrouping(self.CurrHarmonicState)):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state, verify_beat_strength=False)
                    elif self.isSopranoOnDegree(3) and self.verifySopranoVoiceLeading(cadence_type='IAC') and \
                            self.verifyIACGrouping(HarmonicState=self.CurrHarmonicState):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state, verify_beat_strength=False)
                elif self.isDominantBass(favor_by_part=True) and\
                        (self.verifyHCGrouping(self.CurrHarmonicState, start_stop='any') or self.tryGetBeatStrength()==1) and\
                        self.verifyHCHarmony(HarmonicState=self.CurrHarmonicState) and\
                        self.verifySopranoVoiceLeading(cadence_type='HC'):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                elif not (self.isSopranoOnDegree(1) or self.isDominantBass() or self.isMediantBass()):#continue the appogiattura if dominant or mediant bass
                    curr_state = CDCadentialStates.CadAvoided
                elif (self.IsChallenger and self.verifyPACGrouping(self.CurrHarmonicState)):
                    curr_state = CDCadentialStates.CadAvoided


        elif curr_state == CDCadentialStates.IACAppoggExpected:
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
            if self.isDominantEmbellishment() or (self.isI64(HarmonicState=self.CurrHarmonicState) and not self.isBassPartRest()):
                curr_state = CDCadentialStates.HCArrivalExpected
            elif self.CurrHarmonicState.ChordWithBassRests.isRest or self.tryGetBeatStrength() == 1: # rest or new measure, exit appoggiatura
                curr_state = CDCadentialStates.CadExpected
            else:
                if self.isTonicBass():
                    if ((self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC')) or
                        (self.isSopranoOnDegree([3, 5]) and self.verifySopranoVoiceLeading(cadence_type='IAC'))) and\
                            (not self.IsChallenger or self.verifyPACGrouping(self.CurrHarmonicState)):
                        if self.CurrHarmonicState.Chord.isConsonant() and not self.harmonyContainsPitchDegree(HarmonicState=self.CurrHarmonicState, degree=6):
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                elif self.isDominantBass(): # dominant bass, go to PAC appogiatura
                    curr_state = self.checkAppoggiaturaOrAvoidance('PAC')
                elif not (self.isSopranoOnDegree(1) or self.isMediantBass()):#continue the appogiattura if dominant or mediant bass
                    curr_state = CDCadentialStates.CadAvoided


        elif curr_state == CDCadentialStates.HCAppoggExpected or curr_state == CDCadentialStates.HCBassAppoggExpected:
            # ==HC with appoggiatura, don't exit as long as bass is dominant
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                if self.verifySopranoVoiceLeading(cadence_type='HC') and\
                        self.verifyHCHarmony(HarmonicState=self.PrevHarmonicState) and\
                        self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                elif not self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState):
                    curr_state = CDCadentialStates.CadExpected
            else:
                if (self.isI64(HarmonicState=self.CurrHarmonicState) and not self.isBassPartRest()) or self.isDominantEmbellishment(): # stay in HC appogg as long as I64 or dominant embellishment
                    curr_state = curr_state
                elif self.isDominantBass(favor_by_part=True) and\
                        self.verifyHCHarmony(self.CurrHarmonicState) and\
                        self.verifySopranoVoiceLeading(cadence_type='HC'):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.HCArrival, curr_state)
                #elif self.isDominantBass(favor_by_part=True) and\
                #        (self.harmonyHasSeventh(self.CurrHarmonicState) or self.tryGetBeatStrength() >= 0.5): #V7 or strong beat, return to cad inevitable
                #    curr_state = CDCadentialStates.CadInevitable
                #elif self.harmonyContainsPitchDegree(HarmonicState=self.CurrHarmonicState, degree=4): #also V7
                #    curr_state = CDCadentialStates.CadInevitable
                elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                    # V7 in alberti
                    if self.isDominantBass(favor_by_part=True, HarmonicState=self.LastNonAlbertiHarmonicState) and\
                            self.harmonyHasSeventh(self.CurrHarmonicState) and\
                            not self.isDominantEmbellishment():
                        curr_state = CDCadentialStates.CadInevitable
                    else:
                        curr_state = curr_state
                elif self.isTonicBass() and self.tryGetBeatStrength() >= 0.5 and\
                        self.verifyPACGrouping(HarmonicState=self.CurrHarmonicState) and\
                        self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState) and\
                        self.isDominantHarmony(HarmonicState=self.PrevHarmonicState):
                    if self.isSopranoOnDegree(1) and self.verifySopranoVoiceLeading(cadence_type='PAC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state)
                    elif self.isSopranoOnDegree([3, 5]) and self.verifySopranoVoiceLeading(cadence_type='IAC'):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                    else:
                        curr_state = self.checkAppoggiaturaOrAvoidance('PAC')
                elif self.isDominantBass(favor_by_part=True) and self.isDominantHarmony(HarmonicState=self.CurrHarmonicState):
                    curr_state = CDCadentialStates.CadInevitable
                # Mozart does use V7 in his HC appoggiatura - see K331-1
                elif self.tryGetBeatStrength() >= 0.25 and self.isDominantBass(favor_by_part=True) and (self.harmonyHasSeventh(self.CurrHarmonicState) or self.tryGetBeatStrength() >= 0.5): #V7 or strong beat, return to cad inevitable
                    curr_state = CDCadentialStates.CadInevitable
                elif curr_state == CDCadentialStates.HCAppoggExpected and not self.isDominantBass():
                    curr_state = CDCadentialStates.CadAvoided
                elif curr_state == CDCadentialStates.HCBassAppoggExpected and not self.isSopranoOnDegree([5]):
                    curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.PACArrival or curr_state == CDCadentialStates.PCCArrival:
            #conditions for exiting PAC state:
            #1. complete rest
            #2. new measure
            #3. bass not on tonic
            #4. no soprano (TBD - what about non voiced works such as piano?), or lowered soprano
            if self.CurrHarmonicState.ChordWithBassRests.isRest or\
                    self.tryGetBeatStrength()>0.5 or\
                    not self.isTonicBass() or\
                    not self.isPartInChord(self.CurrHarmonicState.Chord,'MySoprano') or\
                    self.getCurrSopranoPitch().midi < self.SopranoOfLastCadence.midi:
                self.exitPACState()
                self.updateCadentialState()
                return
            else:
                # soprano still on tonic
                if self.isSopranoOnDegree(1):
                    self.PACPending = False
                    self.exitPACState()
                    self.updateCadentialState()
                    return
                elif self.tryGetBeatStrength() >= 0.25 and\
                        (self.isSopranoOnDegree(3)) and\
                        (self.CurrHarmonicState.Chord.isTriad() or
                         self.CurrHarmonicState.Chord.isIncompleteMajorTriad() or
                         self.CurrHarmonicState.Chord.isIncompleteMinorTriad()):
                    currSopranoPitch = self.getCurrSopranoPitch()
                    lastSopranoPitch = self.SopranoOfLastCadence
                    # a higher third in soprano following a PAC causes it retroactively to become a IAC!
                    print(currSopranoPitch,lastSopranoPitch)
                    if currSopranoPitch != 0 and lastSopranoPitch != 0:
                        if currSopranoPitch.midi > lastSopranoPitch.midi:
                            # moving up to 3, retroactively weakens the PAC to a IAC
                            self.PACPending = True
                        else:
                            # moving down to 3, confirms the PAC, move to idle and call update state again
                            self.PACPending = False
                            self.exitPACState()
                            self.updateCadentialState()
                            return


        elif curr_state == CDCadentialStates.HCArrival or curr_state == CDCadentialStates.PCHArrival:
            if self.CurrHarmonicState.ChordWithBassRests.isRest or self.PrevHarmonicState.ChordWithBassRests.isRest:# a full rest confirms the cadence
                curr_state = CDCadentialStates.Idle if self.MinPostCadenceMeasures > 0 else CDCadentialStates.CadInevitable
            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio):
                # if alberti and weak beat verify still not V7
                if self.harmonyContainsPitchDegree(HarmonicState=self.CurrHarmonicState, degree=4) and\
                        self.isDominantBass(HarmonicState=self.LastNonAlbertiHarmonicState):
                    curr_state = CDCadentialStates.CadInevitable
                    self.RevertLastHC = True
                    self.PostHCMeasureCounter = self.MinPostCadenceMeasuresHC
                else: # stay in state for an other Alberti or arpeggio
                    curr_state = curr_state
            else:
                # == After HC we are still expecting a cadence, but we need to see how this does not create false positives
                if self.isDominantBass() and self.harmonyHasSeventh(self.CurrHarmonicState): #V7, return to cad inevitable (and cancel the previous HC?)
                    curr_state = CDCadentialStates.CadInevitable
                    #if self.tryGetBeatStrength() <= 0.25: # this causes HC misses - example Haydn op.55,2,2 mm.34
                    #    self.RevertLastHC = True
                    #    self.PostHCMeasureCounter = self.MinPostCadenceMeasuresHC
                #elif self.isSubDominantBass(): # V2, cancel previous HC
                #    self.RevertLastHC = True
                #    self.PostHCMeasureCounter = self.MinPostCadenceMeasuresHC
                #    curr_state = CDCadentialStates.CadAvoided
                # === very strict condition from HC to PAC
                elif (self.isTonicBass() or self.isSopranoOnDegree(1)) and\
                        (self.tryGetBeatStrength() > self.WeightOfLastCadence or self.tryGetBeatStrength() > 0.25) and\
                        self.verifyPACGrouping(HarmonicState=self.CurrHarmonicState) and\
                        self.verifySopranoVoiceLeading(cadence_type='PAC'):
                    if self.isTonicBass():
                        if self.isSopranoOnDegree(1):
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival, curr_state)
                        elif self.isSopranoOnDegree(3):
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival, curr_state)
                        else:
                            curr_state = self.checkAppoggiaturaOrAvoidance('PAC')
                    elif self.isDominantBass() and self.isI64(HarmonicState=self.CurrHarmonicState):
                        curr_state = CDCadentialStates.HCArrivalExpected
                    else:
                        curr_state = self.checkBassAppoggiatura(curr_state=curr_state)
                elif not self.isDominantBass():#bass has left domninant, go back to cad expected
                    curr_state = CDCadentialStates.CadExpected
                else:
                    curr_state = curr_state

        #====set output to state and then set cadential arrivals back to idle state
        self.CurrCadentialOutput = curr_state
        self.CurrCadentialState = curr_state
        #print(self.CurrCadentialState)
        #==must check for change for flow debugging
        self.checkStateChanged()

    def checkAppoggiaturaOrAvoidance(self, app_type='PAC'):
        if app_type == 'PAC' and \
                ((self.CurrHarmonicState.Key.mode == 'major' and self.isSopranoOnSemitonesFromTonic([11, 2, 4])) or
                 (self.CurrHarmonicState.Key.mode == 'minor' and self.isSopranoOnSemitonesFromTonic([10, 11, 2, 3]))):
            curr_state = CDCadentialStates.PACAppoggExpected
        elif app_type in ['IAC', 'PAC'] and self.isSopranoOnSemitonesFromTonic([3, 5]) and self.verifyIACGrouping(HarmonicState=self.CurrHarmonicState):
            curr_state = CDCadentialStates.IACAppoggExpected
        elif app_type == 'HC' and \
                ((self.CurrHarmonicState.Key.mode == 'major' and self.isSopranoOnSemitonesFromTonic([0, 1, 4, 6, 9])) or
                 (self.CurrHarmonicState.Key.mode == 'minor' and self.isSopranoOnSemitonesFromTonic([0, 1, 3, 6, 8]))):
            curr_state = CDCadentialStates.HCAppoggExpected
        else:
            curr_state = CDCadentialStates.CadAvoided
        return curr_state

    def checkBassAppoggiatura(self, curr_state):
        if self.isDominantBass(favor_by_part=True) or self.isMediantBass(favor_by_part=True) or self.isBassPartRest():
            if (curr_state in [CDCadentialStates.CadInevitable, CDCadentialStates.HCArrival, CDCadentialStates.PCHArrival]) and self.isSopranoOnDegree(1):
                curr_state = CDCadentialStates.BassAppoggExpected
            elif curr_state == CDCadentialStates.IACArrivalExpected and (self.isSopranoOnDegree([1, 2, 3]) or self.isLeadingToneSoprano()):
                curr_state = CDCadentialStates.IACAppoggExpected
            elif curr_state == CDCadentialStates.IACArrivalExpected and (self.isSopranoAtSemitoneFromDegree(1, 3)):
                curr_state = CDCadentialStates.IACAppoggExpected
            elif self.isDominantBass(favor_by_part=True):
                curr_state = CDCadentialStates.CadInevitable
            else:
                curr_state = CDCadentialStates.CadAvoided
        else:
            curr_state = CDCadentialStates.CadAvoided
        return curr_state

    def exitPACState(self):
        if self.PACPending:
            self.CurrCadentialState = CDCadentialStates.CadExpected
            self.RevertLastPAC = True
            self.PostPACMeasureCounter = self.MinPostCadenceMeasures #set the counter high to catch the next cadence
        else:
            # move to idle (confirming the PAC) and call update state again
            if self.MinPostCadenceMeasures > 0:
                self.CurrCadentialState = CDCadentialStates.Idle
            # if no minimum post cadence measures required, expect post cadential cadences
            else:
                self.CurrCadentialState = CDCadentialStates.CadExpected
            self.RevertLastPAC = False
        self.PACPending = False

    def updateCounters(self):
        #beat strenth==1 means new measure
        if self.tryGetBeatStrength() == 1:
            self.PostPACMeasureCounter += 1
            self.PostHCMeasureCounter += 1
            self.MeasureCounter += 1

    def setCadenceOrPostCadence(self, cadence=None, state=None, verify_beat_strength=True):
        if not verify_beat_strength or self.tryGetBeatStrength() >= 0.125:
            if self.MeasureCounter >= self.MinInitialMeasures[cadence]:
                if cadence == CDCadentialStates.PACArrival and self.PostPACMeasureCounter < self.MinPostCadenceMeasures:
                    state = CDCadentialStates.PCCArrival
                elif cadence == CDCadentialStates.HCArrival and self.PostHCMeasureCounter < self.MinPostCadenceMeasuresHC:
                    state = CDCadentialStates.PCHArrival
                else:
                    state = cadence
            else: # too early, return to cadence expected again
                state = CDCadentialStates.CadExpected
            if state == CDCadentialStates.HCArrival or state == CDCadentialStates.PCHArrival:
                self.WeightOfLastCadence = self.tryGetBeatStrength()
            self.SopranoOfLastCadence = self.getCurrSopranoPitch()
            self.HarmonicStateOfLastCadence = copy.deepcopy(self.CurrHarmonicState)
        else:
            state = state
        return state

    def getCadentialOutput(self):
        return self.CurrCadentialOutput

    def getCadentialOutputString(self):
        Lyric = str("")
        if self.ChangeFlagOneShot == 1:
            if self.getCadentialOutput() == CDCadentialStates.PACArrival:
                Lyric = str("PAC")
            elif self.getCadentialOutput() == CDCadentialStates.PCCArrival:
                Lyric = str("PCC")
            elif self.getCadentialOutput() == CDCadentialStates.IACArrival:
                Lyric = str("IAC")
            elif self.getCadentialOutput() == CDCadentialStates.HCArrival:
                Lyric = str("HC")
            elif self.getCadentialOutput() == CDCadentialStates.PCHArrival:
                Lyric = str("PCH")
            elif self.getCadentialOutput() == CDCadentialStates.CadAvoided:
                Lyric = str("CA")
            elif not (self.getCadentialOutput() == CDCadentialStates.Idle):
                Lyric = Lyric + self.TriggerString

        if self.KeyChangeOneShot == 1 or self.FirstKeyDetectionDone == 0 or self.CadentialKeyChange == 1:
            Lyric = Lyric + str("\nKey: ") + str(self.CurrHarmonicState.Key)
            self.FirstKeyDetectionDone = 1
            self.CadentialKeyChange = 0

        #debug arpeggios and alberti
        #if self.CurrHarmonicState.Alberti:
        #    Lyric = Lyric + ' Al'
        #elif self.CurrHarmonicState.Arpeggio:
        #    Lyric = Lyric + ' Ar'

        #Lyric = Lyric + " " + str(self.CurrHarmonicState.ChordDegree) + " " + str()
        return Lyric

    def getRevertLastPACAndReset(self):
        retVal = self.RevertLastPAC
        self.RevertLastPAC = False
        return retVal

    def getRevertLastHCAndReset(self):
        retVal = self.RevertLastHC
        self.RevertLastHC = False
        return retVal

    def getRevertLastIACAndReset(self):
        retVal = self.RevertLastIAC
        self.RevertLastIAC = False
        return retVal


