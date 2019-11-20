from music21 import *
from enum import Enum

#consts
MaxNumMeasures = 200
MinInitialMeasures = 3
MinPostCadenceMeasures = 3

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
    IACArrivalExpected = 8
    HCArrivalExpected = 9
    PCCArrival = 10
    PACAppoggExpected = 11
    IACAppoggExpected = 12

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


class CDHarmonicState:
    def __init__(self, Key, Chord, ChordDegree, ChordInversion, ChordFigure):
        self.Key = Key
        self.Chord = Chord
        self.ChordDegree = ChordDegree
        self.ChordInversion = ChordInversion
        self.ChordFigure = ChordFigure



SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
