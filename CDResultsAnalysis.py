import os
SearsPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/5387755/'
FileEnding = ".txt"
SearCadenceViolinMeasureIndex = 2
MyPath ='/Users/matanba/Dropbox/PhD/CadencesResearch/ResultsAndFiles/'
MyCadenceMeasureIndex = 1
CombinedTable = []
CommonPacs = []
TotalSears = []
TotalMyCadences = []

for SearsFile in os.listdir(SearsPath):
    if SearsFile.endswith(FileEnding):
        #define path for Sears
        FullPath = os.path.join(SearsPath, SearsFile)
        print(f"Analyzing {FullPath}")

        SearsCadences = []
        MyCadences = []

        #find sears cadences
        with open(FullPath,'r') as f:
            lines = f.readlines()

            FoundRow = 0
            for line in lines:
                if FoundRow==0:
                    if "Cadence Category" in line:
                        FoundRow = 1
                        continue
                else:
                    if "PAC" in line:
                        elements = line.strip().split("\t")
                        print(elements, len(elements))
                        SearsCadences.append(str(elements[SearCadenceViolinMeasureIndex]))
                        #print(line, file=text_file_reduced)

        # find equivalent in MyPath
        MyFile = SearsFile.replace(".txt", "_xml_Analyzed.txt")
        MyFullPath = os.path.join(MyPath, MyFile)

        with open(MyFullPath,'r') as f:
            lines = f.readlines()
            for line in lines:
                if "PAC" in line:
                    elements = line.strip().split(" ")
                    print(elements, len(elements))
                    MyCadences.append(str(elements[MyCadenceMeasureIndex]))

        FileNameForText = SearsFile.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")

        for item in list(set(SearsCadences).intersection(MyCadences)):
            CommonPacs.append(item)

        for item in SearsCadences:
            TotalSears.append(SearsCadences)

        for item in MyCadences:
            TotalMyCadences.append(MyCadences)

        CombinedTable.append([FileNameForText,",".join(SearsCadences),",".join(MyCadences)])

TotalNumMeasures = 2864
TP = len(CommonPacs)
FP = len(TotalMyCadences)-len(CommonPacs)
TN = TotalNumMeasures - len(TotalSears) + FP
FN = len(TotalSears) - len(CommonPacs)
print(CombinedTable)
print("PACs Detected (TP) = ", TP, "out of", len(TotalSears))
print("Precision = " , TP/(FP+TP))
print("Recall = " , TP/(FN+TP))
print("Accuracy = " , (TP+TN)/(TP+TN+FP+FN))
print("Specificity = " , TN/(FP+TN))

#write table in latex format
fileNameResults = "ResultsLatexTable.txt"
FullPathResults = os.path.join(MyPath, fileNameResults)
text_file_results = open(FullPathResults, "w")
print(" \\\\\n".join([" & ".join(map(str, line)) for line in CombinedTable]), file=text_file_results)
text_file_results.close()