from CadenceDetectData import *
from music21 import *
import copy

class CDStateMachine(object):
    def __init__(self):
        # initiliaze with invalid states
        self.PrevCadentialState = CDCadentialStates.Idle
        self.CurrCadentialState = CDCadentialStates.Idle
        self.CurrHarmonicState = CDHarmonicState([], [], [], 0, 0, 0, 0, 0, 0, [])
        self.PrevHarmonicState = self.CurrHarmonicState
        self.CurrCadentialOutput = CDCadentialStates.Idle
        self.CurrHarmonicState = CDHarmonicState([], chord.Chord(), chord.Chord(), 0, 0, 0, 0, 0, meter.TimeSignature(),[])
        self.ChangeFlagOneShot = 0
        self.KeyChangeOneShot = 0
        self.FirstKeyDetectionDone = 0
        self.CadentialKeyChange = 0
        self.TriggerString = str("")
        self.MeasureCounter = 0
        self.PostCadenceMeasureCounter = MinPostCadenceMeasures
        self.CheckBassPartFromChord = False
        self.PACPending = False
        self.RevertLastPAC = False
        self.ChordOfLastCadence = 0
        self.SopranoOfLastCadence = 0

    def updateHarmonicState(self, Key, Chord, ChordWithRests, ChordDegree, ChordInversion, ChordFigure, Alberti, Arpeggio, RomamNumeral):

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
        self.updateCadentialState()

    def checkStateChanged(self):
        self.ChangeFlagOneShot = 0
        if self.PrevCadentialState != self.CurrCadentialState:
            self.ChangeFlagOneShot = 1
            self.TriggerString = str("T") + str(self.PrevCadentialState.value) + str(u'\u208B') + str(self.CurrCadentialState.value)
            self.TriggerString = self.TriggerString.translate(SUB)
            self.PrevCadentialState = self.CurrCadentialState
            if self.CurrCadentialState == CDCadentialStates.PACArrival or self.CurrCadentialState == CDCadentialStates.PCCArrival:
                self.PostCadenceMeasureCounter = 0

    def getBassFromChord(self, chord):
        retVal = 0
        if not retVal:
            # also checking the bass part (even if it is not the lowest note in the chord)
            for p in chord:
                if 'MyBasso' in p.groups:
                    if retVal == 0 or p.pitch.midi < retVal.midi:
                        retVal = p.pitch

        # sometimes the labeling fails, then try lowest pitch while verifying an octave below soprano
        if not retVal:
            sorted_pitches = chord.sortFrequencyAscending().pitches
            lowestPitch = sorted_pitches[0]
            highestPitch = sorted_pitches[-1]
            if 'MySoprano' not in lowestPitch.groups and ((highestPitch.midi-lowestPitch.midi) > 11 or lowestPitch.midi <= 72):
                retVal = lowestPitch
        return retVal

    def compareBassWithPitch(self,pitchClass):
        #first try music21
        #retVal = self.CurrHarmonicState.Chord.bass().pitchClass == pitchClass
        retVal = False
        #then try part labeling
        if not retVal:
            bassPitch = self.getBassFromChord(self.CurrHarmonicState.Chord)
            if bassPitch:
                retVal = bassPitch.pitchClass==pitchClass
        return retVal

    def isSopraneOnDegree(self,deg):
        retVal = 0
        if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(deg).pitchClass:
             retVal = 1
             #check for voice crossing of other voices
        elif self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(deg).pitchClass:
             retVal = 1
        else:
            for p in self.CurrHarmonicState.Chord.pitches:
                if p.pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(deg).pitchClass and 'MySoprano' in p.groups:
                    retVal = 1
                    break
        return retVal

    def getCurrSopranoPitch(self):
        retVal  = 0
        for p in self.CurrHarmonicState.Chord.pitches:
            if 'MySoprano' in p.groups:
                retVal = p
                break
        #soprano may be removed by chordify
        if retVal == 0:
            retVal = self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[-1]
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

    def isDominantBass(self):
        dominantPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.compareBassWithPitch(dominantPitchClass)
        return retVal

    def isMediantBass(self):
        dominantPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.compareBassWithPitch(dominantPitchClass)
        return retVal

    def isTonicBass(self):
        tonicPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass
        retVal = self.compareBassWithPitch(tonicPitchClass)
        return retVal

    def harmonyHasThird(self):
        return not (self.CurrHarmonicState.Chord.third is None)

    def isMatchingQuality(self):
        return not self.harmonyHasThird() or\
               (self.CurrHarmonicState.RomanNumeral.quality == self.CurrHarmonicState.Key.mode)

    def harmonyHasSeventh(self):
        return not (self.CurrHarmonicState.Chord.seventh is None)

    def isLeadingToneSoprane(self):
        return self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(7).pitchClass

    def isLeadingToneBass(self):
        return self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(7).pitchClass)

    def isRootedHarmony(self):
        return self.compareBassWithPitch(self.CurrHarmonicState.Chord.root().pitchClass)

    def isSecondaryDominantLeadingTone(self):
        retVal= 0
        Fourth = self.CurrHarmonicState.Key.pitchFromDegree(4)
        RaisedFourth = pitch.Pitch(midi=Fourth.midi+1)
        pSecondaryLeadingTone = RaisedFourth.pitchClass
        for p in self.CurrHarmonicState.Chord.pitches:
            if p.pitchClass == pSecondaryLeadingTone:
                retVal = 1
                break
        return retVal

    def isSecondaryDominantUpperLeadingTone(self):
        retVal= 0
        Fifth = self.CurrHarmonicState.Key.pitchFromDegree(5)
        RaisedFifth = pitch.Pitch(midi=Fifth.midi+1)
        pSecondaryDominantUpperLeadingTone = RaisedFifth.pitchClass
        for p in self.CurrHarmonicState.Chord.pitches:
            if p.pitchClass == pSecondaryDominantUpperLeadingTone:
                retVal = 1
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


    def updateCadentialState(self):

        curr_state = self.CurrCadentialState #set to temp variable for clean code

        # ====on key change, return to Cadence expected, not idle since the key change itself creates the initial tension
        if self.KeyChangeOneShot==1:
            curr_state = CDCadentialStates.CadExpected

        # ===============================================
        # ====idle state, wait for IV or II6 or I6=======
        # ===============================================
        #if self.tryGetBeatStrength() < 0.5:
        #do nothing
            #curr_state = curr_state
        if curr_state == CDCadentialStates.Idle:
            if self.CurrHarmonicState.ChordWithBassRests.isRest and not self.PrevHarmonicState.Chord.isRest:
                #if sudden rest, check if previous harmony was dominant
                if isinstance(self.PrevHarmonicState.Key, key.Key):
                    dominantPitchClass = self.PrevHarmonicState.Key.pitchFromDegree(5).pitchClass
                    bassPitch = self.getBassFromChord(self.PrevHarmonicState.Chord)
                    if bassPitch and bassPitch.pitchClass == dominantPitchClass:
                        curr_state = CDCadentialStates.HCArrival
            elif self.isSecondaryDominantLeadingTone():# or (self.CurrHarmonicState.Key.mode=='major' and self.isSecondaryDominantUpperLeadingTone()): #this can create false HCs, need to consider non-cadential chromatic situations
                curr_state = CDCadentialStates.HCArrivalExpected

            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio) and self.tryGetBeatStrength() < 0.5:
                #if alberti and weak beat do nothing
                curr_state = curr_state
            elif self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = curr_state
            elif self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(4).pitchClass):
                #== bass in 4th degree - IV or II6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif self.compareBassWithPitch(self.CurrHarmonicState.Key.pitchFromDegree(6).pitchClass):
                #== bass in 6th degree - VI or IV6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected

        # ==========================================
        # ====expecting cadence, wait for V=========
        # ==========================================
        elif curr_state == CDCadentialStates.CadExpected or curr_state == CDCadentialStates.CadAvoided or curr_state == CDCadentialStates.IACArrival:
            # only stay in CadAvoided once (currently for display purposes)
            if curr_state == CDCadentialStates.CadAvoided or curr_state == CDCadentialStates.IACArrival:
                curr_state = CDCadentialStates.CadExpected

            #verify chord has third to be dominant
            #if self.harmonyHasThird() or self.isUnison():
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = curr_state
            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio) and self.tryGetBeatStrength() < 0.5:
                #if alberti and weak beat do nothing
                curr_state = curr_state
            elif self.isDominantBass():
                if (self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value or self.tryGetBeatStrength()>=0.5):
                    # ==using 5th degree to go to PAC expected - TBD, this includes I64 but also need to see about passing chords
                    curr_state = CDCadentialStates.CadInevitable
            elif self.isLeadingToneSoprane() or self.isLeadingToneBass():
                # ==using leadind tone  to go to IAC expected - TBD, need to see about passing chords
                curr_state = CDCadentialStates.IACArrivalExpected
            #elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.I.value:
                #     curr_state = CDCadentialStates.HCArrivalExpected

            elif self.isSecondaryDominantLeadingTone():# or (self.CurrHarmonicState.Key.mode=='major' and self.isSecondaryDominantUpperLeadingTone()): #this can create false HCs, need to consider non-cadential chromatic situations
                curr_state = CDCadentialStates.HCArrivalExpected

        # ========================================================
        # ====inevitable cadence (PAC or IAC), wait for Is========
        # ========================================================
        elif curr_state==CDCadentialStates.CadInevitable or curr_state==CDCadentialStates.IACArrivalExpected:

            #on dominant and then a complete rest --> HC
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.HCArrival
            elif (self.CurrHarmonicState.Alberti or self.CurrHarmonicState.Arpeggio) and self.tryGetBeatStrength() < 0.5:
                #if alberti and weak beat do nothing
                curr_state = curr_state
            else:
                # for the case where in IAC expected and dominant appears again, the back to Cad inevitable (TBD, separate these states)
                if self.isDominantBass():
                    curr_state = CDCadentialStates.CadInevitable
                elif self.isSecondaryDominantLeadingTone():# or (self.CurrHarmonicState.Key.mode=='major' and self.isSecondaryDominantUpperLeadingTone()): #this can create false HCs, need to consider non-cadential chromatic situations
                    curr_state = CDCadentialStates.HCArrivalExpected
                # meter - look for cadences on strong beat:
                elif self.tryGetBeatStrength() >= 0.25:#cadence can only occur on strong beats (TBD - syncopa?)
                    # harmony  - chordal degree and bass analysis
                    # bass rest on strong beat --> HC
                    if self.getBassFromChord(self.CurrHarmonicState.ChordWithBassRests)==0:
                        curr_state = CDCadentialStates.HCArrival
                    elif self.isTonicBass():
                        # harmony  - chordal inversion
                        if self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.Root.value or self.isRootedHarmony():
                            # ==I after V after IV or II6, cadential arrival
                            # melody  - soprano degree
                            if self.isSopraneOnDegree(1):
                                if curr_state==CDCadentialStates.CadInevitable:
                                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                                else:
                                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                            #sporano not on 1, either IAC or appoggiatura
                            elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                                curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)

                            # expecting appogiaturas only on strongest beats (TBD - this might be overfit to haydn)
                            elif self.tryGetBeatStrength() == 1.0:
                                if curr_state == CDCadentialStates.CadInevitable:
                                    curr_state = CDCadentialStates.PACAppoggExpected
                                else:
                                    curr_state = CDCadentialStates.IACAppoggExpected
                            # appogiatura can also not be detected as I
                        elif self.isTonicBass():
                            # expecting appogiaturas only on strongest beats (TBD - this might be overfit to haydn)
                            if self.tryGetBeatStrength() == 1.0:
                                if curr_state == CDCadentialStates.CadInevitable:
                                    curr_state = CDCadentialStates.PACAppoggExpected
                                else:
                                    curr_state = CDCadentialStates.IACAppoggExpected

                        #== on strong beat: check for I6 (avoided cadence or bass appogiatura)
                        else:
                            thirdPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass
                            if self.compareBassWithPitch(thirdPitchClass):
                                curr_state = CDCadentialStates.PACAppoggExpected
                    # on strong beat: going from V to anything other than V or I is avoiding the cadence (TBD could HC follow?)
                    elif not self.isDominantBass():
                        curr_state = CDCadentialStates.CadAvoided

                # on weaker beat (but not completely weak) leave this state if not dominant bass:
                elif self.tryGetBeatStrength() > 0.25 and not self.isDominantBass():
                    # if we left dominant but not to I then cadence avoided, but could be HC so wait for V again - TBD, perhaps this avoidance goes further back
                    curr_state = CDCadentialStates.HCArrivalExpected

        # =============================================================================================
        # ====HC expected, V on strong beat = HC, V on weak beat, return to cadence inevitable ========
        # =============================================================================================

        elif curr_state == CDCadentialStates.HCArrivalExpected:

            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.Idle

            else:
                if self.tryGetBeatStrength() < 0.5:
                    if self.isDominantBass():#weak beat returning to dominant, return to cad inevitable
                        curr_state = CDCadentialStates.CadInevitable

                else: #strong beats (TBD - syncopa?)

                    if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.harmonyHasSeventh(): #V7, return to cad inevitable
                        curr_state = CDCadentialStates.CadInevitable

                    elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.isRootedHarmony() and self.harmonyHasThird():# V on strong beat while expecting - HC
                        curr_state = CDCadentialStates.HCArrival

                    elif self.isDominantBass() and self.tryGetBeatStrength() == 1.0: #appoggiatura only on strongest beat?
                         curr_state = CDCadentialStates.HCAppoggExpected

                    elif not self.isDominantBass(): #strong beat and not dominant, cadence avoided
                        curr_state = CDCadentialStates.CadAvoided


        elif curr_state == CDCadentialStates.PACAppoggExpected:

            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.Idle
            else:
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
                if self.isTonicBass():
                    if self.isSopraneOnDegree(1):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                    elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                    #else:
                    #    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACAppoggExpected)
                elif not (self.isSopraneOnDegree(1) or self.isDominantBass() or self.isMediantBass()):#continue the appogiattura if dominant or mediant bass
                    curr_state = CDCadentialStates.CadAvoided


        elif curr_state == CDCadentialStates.IACAppoggExpected:
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.Idle
            else:
                if self.isTonicBass():
                    if self.isSopraneOnDegree(1):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                    elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                    #else:
                    #    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACAppoggExpected)
                elif not (self.isSopraneOnDegree(1) or self.isDominantBass() or self.isMediantBass()):#continue the appogiattura if dominant or mediant bass
                    curr_state = CDCadentialStates.CadAvoided


        elif curr_state == CDCadentialStates.HCAppoggExpected:
            # ==HC with appoggiatura, don't exit as long as bass is dominant
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.Idle
            else:
                if self.isDominantBass():
                    if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.harmonyHasSeventh(): #V7, return to cad inevitable
                        curr_state = CDCadentialStates.CadInevitable
                    elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.isRootedHarmony() and self.harmonyHasThird():
                        curr_state = CDCadentialStates.HCArrival
                    elif self.tryGetBeatStrength() > 0.5: #leave appogiaturra state
                        curr_state = CDCadentialStates.CadInevitable
                elif self.isTonicBass() and self.tryGetBeatStrength() >= 0.5:#PAC arrival can happen here
                    if self.isSopraneOnDegree(1):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                    elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                else:
                    curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.PACArrival or curr_state == CDCadentialStates.PCCArrival:
            #conditions for exiting PAC state:
            #1. complete rest
            #2. new measure
            #3. bass not on tonic
            #4. no soprano (TBD - what about non voiced works such as piano?)
            if self.CurrHarmonicState.ChordWithBassRests.isRest or\
                    self.tryGetBeatStrength()>0.5 or\
                    not self.isTonicBass() or\
                    not self.isPartInChord(self.CurrHarmonicState.Chord,'MySoprano'):
                self.exitPACState()
                self.updateCadentialState()
                return
            else:
                if self.isSopraneOnDegree(1):
                    self.PACPending = False
                    self.exitPACState()
                    self.updateCadentialState()
                    return
                elif self.tryGetBeatStrength() >= 0.25 and\
                        self.isSopraneOnDegree(3) and\
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


        elif curr_state == CDCadentialStates.HCArrival:
            if self.CurrHarmonicState.ChordWithBassRests.isRest:
                curr_state = CDCadentialStates.CadExpected
            else:
                # == After HC we are still expecting a cadence, but we need to see how this does not create false positives
                if self.isDominantBass():
                    if self.harmonyHasSeventh(): #V7, return to cad inevitable! (TBD - and cancel the previous HC??)
                        curr_state = CDCadentialStates.CadInevitable
                else:#bass has left domninant, go back to cad expected
                    curr_state = CDCadentialStates.CadExpected

        #====set output to state and then set cadential arrivals back to idle state
        self.CurrCadentialOutput = curr_state
        #=========================================
        # ==========================================
        # ========Post Cadence states===============
        # ==========================================

        # if curr_state == CDCadentialStates.PACArrival:
        #     # == cadential arrival, currently go to idle immediately - TBD - look for post cadential stuff
        #     curr_state = CDCadentialStates.Idle
        #     self.PostCadenceMeasureCounter = 0
        # elif curr_state == CDCadentialStates.PCCArrival:
        #     # == post cadential arrival, currently go to idle immediately - TBD - look for post cadential stuff
        #     curr_state = CDCadentialStates.Idle
        #     self.PostCadenceMeasureCounter = 0
        # elif curr_state == CDCadentialStates.HCArrival:
        #     # == After HC we are still expecting a cadence, but we need to see how this does not create false positives
        #     curr_state = CDCadentialStates.CadExpected

        self.CurrCadentialState = curr_state
        #print(self.CurrCadentialState)
        #==must check for change for flow debugging
        self.checkStateChanged()

        self.updateCounters()

    def exitPACState(self):
        if self.PACPending:
            self.CurrCadentialState = CDCadentialStates.CadExpected
            self.RevertLastPAC = True
        else:
            # move to idle (confirming the PAC) and call update state again
            self.CurrCadentialState = CDCadentialStates.Idle
            self.RevertLastPAC = False
        self.PACPending = False

    def updateCounters(self):
        #beat strenth==1 means new measure
        if self.tryGetBeatStrength()==1:
            self.PostCadenceMeasureCounter = self.PostCadenceMeasureCounter + 1
            self.MeasureCounter = self.MeasureCounter + 1

    def setCadenceOrPostCadence(self,Cadence):
        if Cadence==CDCadentialStates.PACArrival and self.PostCadenceMeasureCounter <= MinPostCadenceMeasures:
            state = CDCadentialStates.PCCArrival
        elif self.MeasureCounter <= MinInitialMeasures:
            state = CDCadentialStates.IACArrival
        else:
            state = Cadence
        self.SopranoOfLastCadence = self.getCurrSopranoPitch()
        self.ChordOfLastCadence = self.CurrHarmonicState.Chord
        return state

    def getCadentialOutput(self):
        return self.CurrCadentialOutput

    def getCadentialOutputString(self):
        Lyric = str("")
        if self.ChangeFlagOneShot == 1:

            #returning to idle should not require a chord display
            #if not (self.getCadentialOutput() == CDCadentialStates.Idle):
                #Lyric = Lyric + str(self.CurrHarmonicState.ChordFigure)

            if self.getCadentialOutput() == CDCadentialStates.PACArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":PAC")
            elif self.getCadentialOutput() == CDCadentialStates.PCCArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":PCC")
            elif self.getCadentialOutput() == CDCadentialStates.IACArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":IAC")
            elif self.getCadentialOutput() == CDCadentialStates.HCArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":HC")
            elif self.getCadentialOutput() == CDCadentialStates.CadAvoided:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":CA")
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


