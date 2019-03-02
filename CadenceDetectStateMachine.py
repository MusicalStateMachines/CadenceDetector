from CadenceDetectData import *
from music21 import *

class CDStateMachine:
    PrevCadentialState = CDCadentialStates.Idle
    CurrCadentialState = CDCadentialStates.Idle
    CurrHarmonicState = CDHarmonicState(chord.Chord(), key.Key(), 0, 0, 0)
    ChangeFlagOneShot = 0
    KeyChangeOneShot = 0
    TriggerString = str("")
    MeasureCounter = 0
    PostCadenceMeasureCounter = MinPostCadenceMeasures

    def __int__(self):
        # initiliaze with invalid states
        self.CurrCadentialState = CDCadentialStates.Idle
        self.CurrHarmonicState = CDHarmonicState(chord.Chord(), key.Key(),0, 0, 0)

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

    def isDominantBass(self):
        return self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass

    def harmonyHasThird(self):
        return not (self.CurrHarmonicState.Chord.third is None)

    def isLeadingToneSoprane(self):
        return self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(7).pitchClass

    def isRootedHarmony(self):
        return self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Chord.root().pitchClass

    def updateCadentialState(self):

        curr_state = self.CurrCadentialState #set to temp variable for clean code

        # ====on key change, we must init the states
        # if self.KeyChangeOneShot==1:
        #     curr_state = CDCadentialStates.Idle

        # ==========================================
        # ====idle state, wait for IV or II6 =======
        # ==========================================
        if curr_state == CDCadentialStates.Idle:

            if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.IV.value:
                # ==IV- go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif (self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.II.value and self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.First.value):
                # ==II6 - go to expecting cadence
                curr_state = CDCadentialStates.CadExpected
            elif self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(4).pitchClass:
                #== bass in 4th degree - go to expecting cadence (TBD, are we sure here?, it makes the line above redundant)
                curr_state = CDCadentialStates.CadExpected

        # ==========================================
        # ====expecting cadence, wait for V=========
        # ==========================================
        elif curr_state == CDCadentialStates.CadExpected or curr_state == CDCadentialStates.CadAvoided:
            # only stay in CadAvoided once (currently for display purposes)
            if curr_state == CDCadentialStates.CadAvoided:
                curr_state = CDCadentialStates.CadExpected

            #verify chord has third to be dominant
            if self.harmonyHasThird():
                if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value:
                    # ==V after IV or II6 - go to cadence inevitable
                    curr_state = CDCadentialStates.CadInevitable
                elif self.isDominantBass():
                     # ==using 5th degree to go to PAC expected - TBD, this includes I64 but also need to see about passing chords
                     curr_state = CDCadentialStates.CadInevitable
                elif self.isLeadingToneSoprane():
                    # ==using leadind tone  to go to IAC expected - TBD, need to see about passing chords
                     curr_state = CDCadentialStates.IACArrivalExpected
#                elif self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.I.value:
#                     curr_state = CDCadentialStates.HCArrivalExpected

        # ========================================================
        # ====inevitable cadence (PAC or IAC), wait for Is========
        # ========================================================
        elif curr_state==CDCadentialStates.CadInevitable or curr_state==CDCadentialStates.IACArrivalExpected:

            # on strong beat:
            if self.CurrHarmonicState.Chord.beatStrength >= 0.5:#cadence can only occur on strong beats (TBD - syncopa?)

                if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.I.value and len(self.CurrHarmonicState.Chord.pitches)>1:
                    if self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.Root.value or self.isRootedHarmony():
                        # ==I after V after IV or II6, cadential arrival - check if soprano is root then PAC otherwise IAC
                        if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                            if curr_state==CDCadentialStates.CadInevitable:
                                curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                            else:
                                curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                        #sporano not on 1, either IAC or appoggiatura
                        elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass:
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                        elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass:
                            curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                        #expecting appogiaturas only on strongest beats (TBD - this might be overfit to haydn)
                        elif  self.CurrHarmonicState.Chord.beatStrength == 1.0:
                            if curr_state==CDCadentialStates.CadInevitable:
                                curr_state = CDCadentialStates.PACAppoggExpected
                            else:
                                curr_state = CDCadentialStates.IACAppoggExpected

                    # TBD - no else here, are we ignoring this or going to CAD avoided?

                    #== on strong beat: I6 (avoided cadence)
                    elif self.CurrHarmonicState.ChordInversion == CDHarmonicChordInversions.First.value:
                            curr_state = CDCadentialStates.CadAvoided

                elif self.CurrHarmonicState.Chord.bass().pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass and len(self.CurrHarmonicState.Chord.pitches)>1:
                    #sometimes bass arrival on the first is not really I, but it is cadential - need to decide what to do here
                    #currently, if soprano on 1 then PAC, otherwise IAC
                    if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                    # sporano not on 1, either IAC or appoggiatura
                    elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass:
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                    elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass:
                        curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                    # expecting appogiaturas only on strongest beats (TBD - this might be overfit to haydn)
                    elif self.CurrHarmonicState.Chord.beatStrength == 1.0:
                        if curr_state == CDCadentialStates.CadInevitable:
                            curr_state = CDCadentialStates.PACAppoggExpected
                        else:
                            curr_state = CDCadentialStates.IACAppoggExpected

                    # TBD - no else here, are we ignoring this or going to CAD avoided?

                    # on strong beat: going from V to anything other than V or I is avoiding the cadence (TBD could HC follow?)
                elif not self.isDominantBass():
                    curr_state = CDCadentialStates.CadAvoided
            # on weak beat:
            elif not self.isDominantBass():
                # if we left dominant but not to I then cadence avoided, but could be HC so wait for V again - TBD, perhaps this avoidance goes further back
                curr_state = CDCadentialStates.HCArrivalExpected

        # ==================================================
        # ====HC expected, wait for V on strong beat========
        # ==================================================

        elif curr_state == CDCadentialStates.HCArrivalExpected:

            if self.CurrHarmonicState.Chord.beatStrength >= 0.5:  # cadence can only occur on strong beats (TBD - syncopa?)

                if self.CurrHarmonicState.ChordDegree == CDHarmonicChordDegrees.V.value and self.isRootedHarmony() and self.harmonyHasThird():
                    curr_state = CDCadentialStates.HCArrival

            elif not self.isDominantBass():
                    curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.PACAppoggExpected:
            # ==appoggiatura, check ass still on key and if soprano is root then PAC otherwise IAC
            if self.CurrHarmonicState.Chord.pitches[0].pitchClass  == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACArrival)
                elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                else:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.PACAppoggExpected)
            else:
                curr_state = CDCadentialStates.CadAvoided

        elif curr_state == CDCadentialStates.IACAppoggExpected:
            # ==appoggiatura, check ass still on key and if soprano is root then PAC otherwise IAC
            if self.CurrHarmonicState.Chord.pitches[0].pitchClass  == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                if self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(1).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(3).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                elif self.CurrHarmonicState.Chord.pitches[-1].pitchClass == self.CurrHarmonicState.Key.pitchFromDegree(5).pitchClass:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACArrival)
                else:
                    curr_state = self.setCadenceOrPostCadence(CDCadentialStates.IACAppoggExpected)
            else:
                curr_state = CDCadentialStates.CadAvoided


        # ==========================================
        # ========Post Cadence states===============
        # ==========================================
        elif curr_state == CDCadentialStates.PACArrival:
            # == cadential arrival, currently go to idle - TBD - look for post cadential stuff
            curr_state = CDCadentialStates.Idle
            self.PostCadenceMeasureCounter = 0
        elif curr_state == CDCadentialStates.IACArrival:
            # == cadential arrival, currently waiting for PAC - TBD - it might need to go to idle sometimes(?)
                curr_state = CDCadentialStates.CadExpected
        elif curr_state == CDCadentialStates.HCArrival:
            # == cadential arrival, currently go to idle - TBD - look for post cadential stuff
            curr_state = CDCadentialStates.Idle
        elif curr_state == CDCadentialStates.PCCArrival:
            # == post cadential arrival, currently go to idle - TBD - look for post cadential stuff
            curr_state = CDCadentialStates.Idle
            self.PostCadenceMeasureCounter = 0

        self.CurrCadentialState = curr_state
        #print(self.CurrCadentialState)
        #==must check for change for flow debugging
        self.checkStateChanged()

        self.updateCounters()

    def updateCounters(self):
        #beat strenth==1 means new measure
        if self.CurrHarmonicState.Chord.beatStrength==1:
            self.PostCadenceMeasureCounter = self.PostCadenceMeasureCounter + 1
            self.MeasureCounter = self.MeasureCounter + 1

    def setCadenceOrPostCadence(self,Cadence):
        if self.PostCadenceMeasureCounter <= MinPostCadenceMeasures:
            state = CDCadentialStates.PCCArrival
        elif self.MeasureCounter <= MinInitialMeasures:
            state = CDCadentialStates.IACArrival
        else:
            state = Cadence
        return state

    def getCadentialState(self):
        return self.CurrCadentialState

    def getCadentialStateString(self):
        Lyric = str("")
        if self.ChangeFlagOneShot == 1:

            #returning to idle should not require a chord display
            #if not (self.getCadentialState() == CDCadentialStates.Idle):
                #Lyric = Lyric + str(self.CurrHarmonicState.ChordFigure)

            if self.getCadentialState() == CDCadentialStates.PACArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":PAC")
            elif self.getCadentialState() == CDCadentialStates.PCCArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":PCC")
            elif self.getCadentialState() == CDCadentialStates.IACArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":IAC")
            elif self.getCadentialState() == CDCadentialStates.HCArrival:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":HC")
            elif self.getCadentialState() == CDCadentialStates.CadAvoided:
                Lyric = str(self.CurrHarmonicState.ChordFigure) + str(":CA")
            elif not (self.getCadentialState() == CDCadentialStates.Idle):
                Lyric = Lyric + self.TriggerString

        if self.KeyChangeOneShot == 1:
            Lyric = Lyric + str("\n") + str(self.CurrHarmonicState.Key)

        #Lyric = Lyric + " " + str(self.CurrHarmonicState.ChordDegree) + " " + str()
        return Lyric
