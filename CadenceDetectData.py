from music21 import *
from enum import Enum

#consts
MaxNumMeasures = 400
MinInitialMeasures = 3
MinPostCadenceMeasures = 0


# class MyChord(chord.Chord):
#     def __init__(self, Chord, Key):
#         self.Chord = Chord
#         self.Key = Key

class CDCadentialStates(Enum):
    Idle = 1
    CadExpected = 2
    CadInevitable = 3
    PACArrival = 4
    CadAvoided = 5
    IACArrival = 6
    HCArrival = 7
    HCArrivalExpected = 8
    PCCArrival = 9
    PACAppoggExpected = 10
    IACAppoggExpected = 11
    IACArrivalExpected = 12
    HCAppoggExpected = 13

class CDHarmonicChordDegrees(Enum):
    I = 1
    II = 2
    III = 3
    IV = 4
    V = 5
    VI = 6
    VII = 7


class CDHarmonicChordInversions(Enum):
    Root = 0
    First = 1
    Second = 2
    Third = 3

class CDKeyDetectionModes(Enum):
    FromFile = 0
    KSRaw = 1
    KSWithSmoothing = 2
    KSWithSmoothingCadenceSensitive = 3


class CDHarmonicState:
    def __init__(self, Key, Chord, ChordWithRests, ChordDegree, ChordInversion, ChordFigure, Alberti, Arpeggio, TimeSig, RomanNumeral):
        self.Key = Key
        self.Chord = Chord
        self.RomanNumeral = RomanNumeral
        self.ChordWithBassRests = ChordWithRests
        self.ChordDegree = ChordDegree
        self.ChordInversion = ChordInversion
        self.ChordFigure = ChordFigure
        self.Alberti = Alberti
        self.Arpeggio = Arpeggio
        self.TimeSig = TimeSig



SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
