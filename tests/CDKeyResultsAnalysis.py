import os
from datetime import datetime
import pickle
from src.cadence_detector.CadenceDetectData import *

# set paths
HomeDir = os.path.expanduser("~") if os.name != 'nt' else os.environ['USERPROFILE']
DataPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/StateMachineData/')
DataFileBeginning = f"haydn_op020_no03_mv04"
DataFileBeginning = f"haydn"
LabeledFileEnding = f"{CDKeyDetectionModes.FromFile}.txt"
PredictedFileEnding = f"{CDKeyDetectionModes.KSWithSmoothingCadenceSensitive}.txt"
CombinedTable = []

for File in sorted(os.listdir(DataPath)):
    if File.startswith(DataFileBeginning) and File.endswith(PredictedFileEnding):
        # define path for Test Data
        FullPath = os.path.join(DataPath, File)
        print(f"Analyzing {FullPath}")
        with open(FullPath, 'rb') as f:
            KeyPerMeasurePredicted = pickle.load(f)

        # find labelled equivalent
        LabeledFile = File.replace(PredictedFileEnding, LabeledFileEnding)
        FullPath = os.path.join(DataPath, LabeledFile)

        # find test keys
        with open(FullPath, 'rb') as f:
            KeyPerMeasureLabeled = pickle.load(f)

        FileNameForText = LabeledFile.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")
        FileNameForText = FileNameForText.replace(" Key ", "")

        correct_count = 0
        missed_measures = []
        for i, (predicted, label) in enumerate(zip(KeyPerMeasurePredicted, KeyPerMeasureLabeled)):
            if predicted.tonicPitchNameWithCase == label.tonicPitchNameWithCase:
                correct_count = correct_count + 1
            else:
                missed_measures.append(i+1)

        CombinedTable.append((FileNameForText, correct_count, len(KeyPerMeasurePredicted), correct_count/len(KeyPerMeasurePredicted), missed_measures))

total_correct = 0
total_measures = 0
for row in CombinedTable:
    total_correct = total_correct + row[1]
    total_measures = total_measures + row[2]
    print(row)

print("Total Measures:", total_measures)
print("Total Correct:", total_correct)
print("Correct Percentage:", total_correct/total_measures)
