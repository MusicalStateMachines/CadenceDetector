import os
SearsPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
FileEnding = ".txt"
SearCadenceViolinMeasureIndex = 2
MyPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
MyCadenceMeasureIndex = 1
CombinedTable = []
CombinedTableExtended = []
TotalSears = []
TotalMyCadences = []
TotalCommonPacs = []
TotalFP = []
TotalFN = []
CadenceString = "PAC"

for SearsFile in sorted(os.listdir(SearsPath)):
    if SearsFile.endswith(FileEnding):
        # define path for Sears
        FullPath = os.path.join(SearsPath, SearsFile)
        print(f"Analyzing {FullPath}")

        CurrSearsCadences = []
        CurrMyCadences = []
        CurrFalsePositives = []
        CurrFalseNegatives = []

        # find sears cadences
        with open(FullPath, 'r') as f:
            lines = f.readlines()

            FoundRow = 0
            for line in lines:
                if FoundRow == 0:
                    if "Cadence Category" in line:
                        FoundRow = 1
                        continue
                else:
                    if CadenceString in line:
                        elements = line.strip().split("\t")
                        print(elements, len(elements))
                        CurrSearsCadences.append(str(elements[SearCadenceViolinMeasureIndex]))
                        # print(line, file=text_file_reduced)

        # find equivalent in MyPath
        MyFile = SearsFile.replace(".txt", "_xml_Analyzed.txt")
        MyFullPath = os.path.join(MyPath, MyFile)

        with open(MyFullPath,'r') as f:
            lines = f.readlines()
            for line in lines:
                if CadenceString in line:
                    elements = line.strip().split(" ")
                    print(elements, len(elements))
                    CurrMyCadences.append(str(elements[MyCadenceMeasureIndex]))

        FileNameForText = SearsFile.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")

        for item in list(set(CurrSearsCadences).intersection(CurrMyCadences)):
            TotalCommonPacs.append(item)

        for item in CurrSearsCadences:
            TotalSears.append(CurrSearsCadences)

        for item in CurrMyCadences:
            TotalMyCadences.append(CurrMyCadences)

        for item in list(set(CurrMyCadences).symmetric_difference(CurrSearsCadences)):
            if item in CurrMyCadences:
                CurrFalsePositives.append(item)
            else:
                CurrFalseNegatives.append(item)

        for item in CurrFalsePositives:
            TotalFP.append(CurrFalsePositives)

        for item in CurrFalseNegatives:
            TotalFN.append(CurrFalseNegatives)

        CombinedTable.append([FileNameForText, ",".join(CurrSearsCadences), ",".join(CurrMyCadences)])
        CombinedTableExtended.append([FileNameForText, ",".join(CurrSearsCadences), ",".join(CurrMyCadences),
                                      ",".join(CurrFalsePositives), ",".join(CurrFalseNegatives)])

for row in CombinedTableExtended:
    print(row)

# write table1 in latex format
FullPathResults = os.path.join(MyPath,"../Results/ResultsLatexTable.txt")
text_file_results = open(FullPathResults, "w")
print(" \\\\\n".join([" & ".join(map(str, line)) for line in CombinedTable]), file=text_file_results)
text_file_results.close()

# write table2 in latex format
FullPathResults = os.path.join(MyPath, "../Results/ClassificationResultsLatexTable.txt")
text_file_results = open(FullPathResults, "w")
ClassificationResultsTable = []
TotalNumMeasures = 2864

TP = len(TotalCommonPacs)
FP = len(TotalFP)
TN = TotalNumMeasures - len(TotalSears) - FP
FN = len(TotalFN)

Precision = TP/(FP+TP)
Recall = TP/(FN+TP)
Accuracy = (TP+TN)/(TP+TN+FP+FN)
Specificity = TN/(FP+TN)

ClassificationResultsTable.append(["Total Measures Analyzed", TotalNumMeasures])
ClassificationResultsTable.append([f"{CadenceString} Detected:", f"{TP} out of {len(TotalSears)}"])
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
