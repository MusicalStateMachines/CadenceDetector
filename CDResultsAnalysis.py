import os
from datetime import datetime
import subprocess


class LabeledData:
    def __init__(self):
        self.DataPath = []
        self.FileEnding = []
        self.PACMeasureIndex = []
        self.RowSearchString = []
        self.TotalNumMeasures = []
        self.Label = []

def write_table_to_latex(table, file_full_path):
    text_file_results = open(file_full_path, "w")
    print(" \\\\\n".join([" & ".join(map(str, line)) for line in table]), file=text_file_results)
    text_file_results.close()

def compute_classification_scores():
    ClassificationResultsTable = []
    TP = len(TotalCommonPacs)
    FP = len(TotalFP)
    TN = TestData.TotalNumMeasures - len(TotalTest) - FP
    FN = len(TotalFN)
    Precision = TP / (FP + TP)
    Recall = TP / (FN + TP)
    Accuracy = (TP + TN) / (TP + TN + FP + FN)
    Specificity = TN / (FP + TN)
    False_Positive_Rate = FP / (FP + TN)
    ClassificationResultsTable.append(["Total Measures Analyzed", TestData.TotalNumMeasures])
    ClassificationResultsTable.append([f"{CadenceString} Detected:", f"{TP} out of {len(TotalTest)}"])
    ClassificationResultsTable.append(["TP", TP])
    ClassificationResultsTable.append(["FP", FP])
    ClassificationResultsTable.append(["TN", TN])
    ClassificationResultsTable.append(["FN", FN])
    ClassificationResultsTable.append(["Precision", "{0:0.2f}".format(Precision)])
    ClassificationResultsTable.append(["Recall", "{0:0.2f}".format(Recall)])
    ClassificationResultsTable.append(["Accuracy", "{0:0.2f}".format(Accuracy)])
    ClassificationResultsTable.append(["Specificity", "{0:0.2f}".format(Specificity)])
    ClassificationResultsTable.append(["False Positive Rate", "{0:0.2f}".format(False_Positive_Rate)])
    for row in ClassificationResultsTable:
        print(row)
    return ClassificationResultsTable

SearsData = LabeledData()
SearsData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
SearsData.FileEnding = ".txt"
SearsData.PACMeasureIndex = 2
SearsData.RowSearchString = "Cadence Category"
SearsData.TotalNumMeasures = 2864
SearsData.Label = "Sears_HaydnQuartets"

DCMData = LabeledData()
DCMData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/cadences'
DCMData.FileEnding = '.tsv'
DCMData.PACMeasureIndex = 1
DCMData.RowSearchString = "cadence"
DCMData.TotalNumMeasures = 12360
DCMData.Label = "DCM_MozartSonatas"

# set which database to compare to
TestData = DCMData
optimize_false_positives = False

# set state machine data
StateMachineData = LabeledData()
StateMachineData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
StateMachineData.PACMeasureIndex = 1
StateMachineData.FileEnding = "_xml_Analyzed.txt"


CombinedTable = []
CombinedTableExtended = []
LabelsTable = []
PredictionsTable = []
TotalTest = []
TotalStateMachine = []
TotalCommonPacs = []
TotalFP = []
TotalFN = []
CadenceString = "PAC"

for LabeledFile in sorted(os.listdir(TestData.DataPath)):
    if LabeledFile.endswith(TestData.FileEnding):
        # define path for Test Data
        FullPath = os.path.join(TestData.DataPath, LabeledFile)
        print(f"Analyzing {FullPath}")

        CurrTestCadences = []
        CurrStateMachineCadences = []
        CurrFalsePositives = []
        CurrFalseNegatives = []

        # find test cadences
        with open(FullPath, 'r') as f:
            lines = f.readlines()

            FoundRow = 0
            for line in lines:
                if FoundRow == 0:
                    if TestData.RowSearchString in line:
                        FoundRow = 1
                        continue
                else:
                    if CadenceString in line:
                        elements = line.strip().split("\t")
                        print(elements, len(elements))
                        CurrTestCadences.append(str(elements[TestData.PACMeasureIndex]))
                        # print(line, file=text_file_reduced)

        # find equivalent in MyPath
        MyFile = LabeledFile.replace(TestData.FileEnding, StateMachineData.FileEnding)
        MyFullPath = os.path.join(StateMachineData.DataPath, MyFile)

        with open(MyFullPath,'r') as f:
            lines = f.readlines()
            for line in lines:
                if CadenceString in line:
                    elements = line.strip().split(" ")
                    print(elements, len(elements))
                    CurrStateMachineCadences.append(str(elements[StateMachineData.PACMeasureIndex]))

        FileNameForText = LabeledFile.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")

        for item in list(set(CurrTestCadences).intersection(CurrStateMachineCadences)):
            TotalCommonPacs.append(item)

        for item in CurrTestCadences:
            TotalTest.append(CurrTestCadences)

        for item in CurrStateMachineCadences:
            TotalStateMachine.append(CurrStateMachineCadences)

        for item in list(set(CurrStateMachineCadences).symmetric_difference(CurrTestCadences)):
            if item in CurrStateMachineCadences:
                CurrFalsePositives.append(item)
            else:
                CurrFalseNegatives.append(item)

        for item in CurrFalsePositives:
            TotalFP.append(CurrFalsePositives)

        for item in CurrFalseNegatives:
            TotalFN.append(CurrFalseNegatives)

        CombinedTable.append([FileNameForText, ",".join(CurrTestCadences), ",".join(CurrStateMachineCadences)])
        CombinedTableExtended.append([FileNameForText, ",".join(CurrTestCadences), ",".join(CurrStateMachineCadences),
                                      ",".join(CurrFalsePositives), ",".join(CurrFalseNegatives)])
        LabelsTable.append([FileNameForText, ",".join(CurrTestCadences)])
        PredictionsTable.append([FileNameForText, ",".join(CurrStateMachineCadences)])

for row in CombinedTableExtended:
    print(row)


now = datetime.now()
current_time = now.strftime("%Y_%m_%d_%H_%M_%S")

# write full table in latex format
FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_FullClassificationsLatexTable_{current_time}.txt")
write_table_to_latex(CombinedTable, FullPathResults)

# write partial tables latex format
FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_LabelsLatexTable_{current_time}.txt")
write_table_to_latex(LabelsTable, FullPathResults)

FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_PredictionsLatexTable_{current_time}.txt")
write_table_to_latex(PredictionsTable, FullPathResults)

# write summary table in latex format
FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_ScoresLatexTable_{current_time}.txt")
ClassificationResultsTable = compute_classification_scores()
write_table_to_latex(ClassificationResultsTable, FullPathResults)

max_misses = 0
max_false = 0
min_misses = 0
min_false = 0

for row in CombinedTableExtended:
    missed_cadences = 0 if row[4] == '' else len(row[4].split(','))
    if missed_cadences >= max_misses:
        max_misses = missed_cadences
        max_row_misses = row
    if missed_cadences <= min_misses:
        min_misses = missed_cadences
        min_row_misses = row
    false_cadences = 0 if row[3] == '' else len(row[3].split(','))
    if false_cadences >= max_false:
        max_false = false_cadences
        max_row_false = row
    if false_cadences <= min_false:
        min_false = missed_cadences
        min_row_false = row

print('---best cases:---')
print(min_row_misses[0])
print('missed cadences:', min_row_misses[4])
print(min_row_false[0])
print('false cadences:', min_row_false[3])
print('---worst cases:---')
print(max_row_misses[0])
print('missed cadences:', max_row_misses[4])
print(max_row_false[0])
print('false cadences:', max_row_false[3])
path = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'

file_to_open = max_row_false[0] if optimize_false_positives else max_row_misses[0]
full_path = os.path.join(path, file_to_open.replace('.tsv','_').replace(' ','_')) + 'xml_Analyzed.xml'
subprocess.call(('open', full_path))





