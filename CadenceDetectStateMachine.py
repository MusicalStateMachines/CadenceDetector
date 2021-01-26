from CadenceDetectData import *
from music21 import *

class CDStateMachine:
    PrevCadentialState = CDCadentialStates.Idle
    CurrCadentialState = CDCadentialStates.Idle
    CurrCadentialOutput = CDCadentialStates.Idle
    CurrHarmonicState = CDHarmonicState(chord.Chord(), key.Key(), 0, 0, 0)
    ChangeFlagOneShot = 0
    KeyChangeOneShot = 0
    TriggerString = str("")
    MeasureCounter = 0
    PostCadenceMeasureCounter = MinPostCadenceMeasures
    CheckBassPartFromChord = False

    def __int__(self):
        # initiliaze with invalid states
        self.CurrCadentialState = CDCadentialStates.Idle
        self.CurrHarmonicState = CDHarmonicState(chord.Chord(), key.Key() ,0, 0, 0)

    def updateHarmonicState(self, Key, Chord, ChordDegree, ChordInversion, ChordFigure):

        self.KeyChangeOneShot = 0
        if (self.CurrHarmonicState.Key != Key):
            self.KeyChangeOneShot = 1
        self.CurrHarmonicState.Key = Key
        self.CurrHarmonicState.Chord = Chord
        self.CurrHarmonicState.ChordDegree = ChordDegree
        self.CurrHarmonicState.ChordInversion = ChordInversion
        self.CurrHarmonicState.ChordFigure = ChordFigure
        self.updateCadentialState()

    def checkStateChanged(self):
        self.ChangeFlagOneShot = 0
        if self.PrevCadentialState != self.CurrCadentialState:
            self.ChangeFlagOneShot = 1
            self.TriggerString = str("T") + str(self.PrevCadentialState.value) + str(u'\u208B') + str(self.CurrCadentialState.value)
            self.TriggerString = self.TriggerString.translate(SUB)
            self.PrevCadentialState = self.CurrCadentialState

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

    def isDominantBass(self):
        dominantPitchClass = self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass
        # chordify may miss the correct bass, check all notes by frequency ascending
        retVal = self.CurrHarmonicState.Chord.bass().pitchClass == dominantPitchClass or self.CurrHarmonicState.Chord.sortFrequencyAscending().pitches[0].pitchClass == dominantPitchClass
        if self.CheckBassPartFromChord:
            #also checking the bass part (even if it is not the loweset note in the chord)
            for p in self.CurrHarmonicState.Chord.pitches:
                if p.pitchClass == dominantPitchClass and 'MyBasso' in p.groups:
                    retVal = 1
                    break

        return retVal

    def isTonicBass(self):
        return self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass

    def harmonyHasThird(self):
        return not (self.CurrHarmonicState.Chord.third is None)

    def harmonyHasSeventh(self):
        return not (self.CurrHarmonicState.Chord.seventh is None)

    def isLeadingToneSoprane(self):
        return self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(7).pitchClass

    def isRootedHarmony(self):
        return self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Chord.root().pitchClass

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

        # ====on key change, we must init the states
        if self.KeyChangeOneShot==1:
            curr_state = CDCadentialStates.Idle

        # ===============================================
        # ====idle state, wait for IV or II6 or I6=======
        # ===============================================
        if curr_state == CDCadentialStates.Idle:
            #if self.tryGetBeatStrength()<0.5:
                #do nothing
                #curr_state = curr_state
            if self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(4).pitchClass:
                #== bass in 4th degree - IV or II6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(6).pitchClass:
                #== bass in 6th degree - VI or IV6 go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            # check I6 on strong beat
            # elif self.CurrHarmonicState.Chord.beatStrength >= 0.5:
            #     if self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass:
            #         curr_state = CDCadentialStates.CadExpected

        # ==========================================
        # ====expecting cadence, wait for V=========
        # ==========================================
        elif curr_state == CDCadentialStates.CadExpected or curr_state == CDCadentialStates.CadAvoided or curr_state == CDCadentialStates.IACArrival:
            # only stay in CadAvoided once (currently for display purposes)
            if curr_state == CDCadentialStates.CadAvoided or CDCadentialStates.IACArrival:
                curr_state = CDCadentialStates.CadExpected

            #verify chord has third to be dominant
            #if self.harmonyHasThird() or self.isUnison():

            if self.isDominantBass():
                if (self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value or self.tryGetBeatStrength()>=0.5):
                    # ==using 5th degree to go to PAC expected - TBD, this includes I64 but also need to see about passing chords
                    curr_state = CDCadentialStates.CadInevitable
            #elif self.isLeadingToneSoprane():
                # ==using leadind tone  to go to IAC expected - TBD, need to see about passing chords
                # curr_state = CDCadentialStates.IACArrivalExpected
            #elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.I.value:
                #     curr_state = CDCadentialStates.HCArrivalExpected

            elif self.isSecondaryDominantLeadingTone() or self.isSecondaryDominantUpperLeadingTone(): #this can create false HCs, need to consider non-cadential chromatic situations
                curr_state = CDCadentialStates.HCArrivalExpected

        # ========================================================
        # ====inevitable cadence (PAC or IAC), wait for Is========
        # ========================================================
        elif curr_state==CDCadentialStates.CadInevitable: # or curr_state==CDCadentialStates.IACArrivalExpected:

            # for the case where in IAC expected and dominant appears again, the back to Cad inevitable (TBD, separate these states)
            if self.isDominantBass():
                curr_state = CDCadentialStates.CadInevitable

            # meter - look for cadences on strong beat:
            if self.tryGetBeatStrength() >= 0.5:#cadence can only occur on strong beats (TBD - syncopa?)
                # harmony  - chordal degree and bass analysis
                if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.I.value or self.isTonicBass():
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

                    # TBD - no else here, are we ignoring this or going to CAD avoided?

                    #== on strong beat: I6 (avoided cadence)
                    elif self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.First.value:
                            curr_state = CDCadentialStates.CadAvoided

                # on strong beat: going from V to anything other than V or I is avoiding the cadence (TBD could HC follow?)
                elif not self.isDominantBass():
                    curr_state = CDCadentialStates.CadAvoided

            # on weaker beat (but not completely weak) leave this state if not dominant bass:
            elif self.tryGetBeatStrength() >= 0.25 and not self.isDominantBass():
                # if we left dominant but not to I then cadence avoided, but could be HC so wait for V again - TBD, perhaps this avoidance goes further back
                curr_state = CDCadentialStates.HCArrivalExpected

        # =============================================================================================
        # ====HC expected, V on strong beat = HC, V on weak beat, return to cadence inevitable ========
        # =============================================================================================

        elif curr_state == CDCadentialStates.HCArrivalExpected:

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
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
            if self.CurrHarmonicState.Chord.pitches[0].pitchClass  == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                if self.isSopraneOnDegree(1):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                else:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACAppoggExpected)
            else:
                curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.IACAppoggExpected:
            # ==appoggiatura, check bass still on key and if soprano is root then PAC otherwise IAC
            if self.isTonicBass():
                if self.isSopraneOnDegree(1):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                elif self.isSopraneOnDegree(3) or self.isSopraneOnDegree(5):
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                else:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACAppoggExpected)
            else:
                curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.HCAppoggExpected:
            # ==HC with appoggiatura, don't exit as long as bass is dominant
            if self.isDominantBass():
                if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.harmonyHasSeventh(): #V7, return to cad inevitable
                    curr_state = CDCadentialStates.CadInevitable
                elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.isRootedHarmony() and self.harmonyHasThird():
                    curr_state = CDCadentialStates.HCArrival
                else: #leave appogiaturra state and go to V
                    curr_state = CDCadentialStates.CadInevitable

            else:
                curr_state = CDCadentialStates.CadAvoided


        #====set output to state and then set cadential arrivals back to idle state
        self.CurrCadentialOutput = curr_state
        #=========================================
        # ==========================================
        # ========Post Cadence states===============
        # ==========================================
        if curr_state == CDCadentialStates.PACArrival:
            # == cadential arrival, currently go to idle immediately - TBD - look for post cadential stuff
            curr_state = CDCadentialStates.Idle
            self.PostCadenceMeasureCounter = 0
        elif curr_state == CDCadentialStates.PCCArrival:
            # == post cadential arrival, currently go to idle immediately - TBD - look for post cadential stuff
            curr_state = CDCadentialStates.Idle
            self.PostCadenceMeasureCounter = 0
        elif curr_state == CDCadentialStates.HCArrival:
            # == After HC we are still expecting a cadence, but we need to see how this does not create false positives
            curr_state = CDCadentialStates.CadExpected

        self.CurrCadentialState = curr_state
        #print(self.CurrCadentialState)
        #==must check for change for flow debugging
        self.checkStateChanged()

        self.updateCounters()

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


        if self.KeyChangeOneShot == 1:
            Lyric = Lyric + str("\n") + str(self.CurrHarmonicState.Key)

        #Lyric = Lyric + " " + str(self.CurrHarmonicState.ChordDegree) + " " + str()
        return Lyric
