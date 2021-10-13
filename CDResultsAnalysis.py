import os
class LabeledData:
    def __init__(self):
        self.DataPath = []
        self.FileEnding = []
        self.PACMeasureIndex = []
        self.RowSearchString = []
        self.TotalNumMeasures = []
        self.Label = []


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
TestData = SearsData

# set state machine data
StateMachineData = LabeledData()
StateMachineData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
StateMachineData.PACMeasureIndex = 1
StateMachineData.FileEnding = "_xml_Analyzed.txt"


CombinedTable = []
CombinedTableExtended = []
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

for row in CombinedTableExtended:
    print(row)

# write table1 in latex format
FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_FullClassificationsLatexTable.txt")
text_file_results = open(FullPathResults, "w")
print(" \\\\\n".join([" & ".join(map(str, line)) for line in CombinedTable]), file=text_file_results)
text_file_results.close()

# write table2 in latex format
FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_ScoresLatexTable.txt")
text_file_results = open(FullPathResults, "w")
ClassificationResultsTable = []


TP = len(TotalCommonPacs)
FP = len(TotalFP)
TN = TestData.TotalNumMeasures - len(TotalTest) - FP
FN = len(TotalFN)

Precision = TP/(FP+TP)
Recall = TP/(FN+TP)
Accuracy = (TP+TN)/(TP+TN+FP+FN)
Specificity = TN/(FP+TN)

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

print(" \\\\\n".join([" & ".join(map(str, line)) for line in ClassificationResultsTable]), file=text_file_results)
text_file_results.close()

for row in ClassificationResultsTable:
    print(row)
