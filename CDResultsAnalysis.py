import copy
import os
from datetime import datetime
import subprocess
import matplotlib.pyplot as plt
import numpy as np

class LabeledData:
    def __init__(self):
        self.DataPath = []
        self.DataFileEnding = []
        self.LabelFileEnding = []
        self.PACMeasureIndex = []
        self.RowSearchString = []
        self.TotalNumMeasures = []
        self.Label = []
        self.Composer = []

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
    print('========Classification Scores:==========')
    for row in ClassificationResultsTable:
        print(row)
    return ClassificationResultsTable

def diachronic_sort(input_table):
    if TestData == SearsData:
        table_diachronically_sorted = sorted([[int(row[0].split(' ')[1].split('op')[1]),
                                               int(row[0].split(' ')[2].split('no')[1]),
                                               int(row[0].split(' ')[3].split('mv')[1].split('.')[0]),
                                               row[1], row[2]] for row in input_table])
        mov_str = [str(row[:3]) for row in table_diachronically_sorted]
    elif TestData == DCMData:
        table_diachronically_sorted = sorted([[int(row[0].split('-')[0].split('K')[1]),
                                               int(row[0].split('-')[1].split('.')[0]),
                                               row[1], row[2]] for row in input_table])
        mov_str = [str(row[:2]) for row in table_diachronically_sorted]
    elif TestData == ABCData:
        table_diachronically_sorted = sorted([[int(row[0].split(' ')[0].split('op')[1]),
                                               int(row[0].split(' ')[1].split('no')[1]),
                                               int(row[0].split(' ')[2].split('mov')[1].split('.')[0]),
                                               row[1], row[2]] for row in input_table])
        mov_str = [str(row[:3]) for row in table_diachronically_sorted]
    print('========Diachronically Sorted Table:==========')
    for row in table_diachronically_sorted:
        print(row)
    return mov_str, table_diachronically_sorted

def plot_diachronic_analysis(mov_str, table_diachronically_sorted):
    PAC_density_per_mov = [row[-1] * 100 for row in table_diachronically_sorted]
    x = range(len(PAC_density_per_mov))
    coef = np.polyfit(x, PAC_density_per_mov, 1)
    poly1d_fn = np.poly1d(coef)
    # poly1d_fn is now a function which takes in x and returns an estimate for y
    fig, ax = plt.subplots()
    ax.plot(PAC_density_per_mov)
    ax.plot(x, poly1d_fn(x), '--k')
    ax.locator_params(nbins=len(PAC_density_per_mov), axis='x')
    ax.xaxis.set_ticks(x)
    ax.set_xticklabels(mov_str, rotation=45, size=8)
    plt.ylim(0, 25)
    if TestData == SearsData or TestData == ABCData:
        plt.xlabel('Op. No. Mv.', size=10)
    elif TestData == DCMData:
        plt.xlabel('K. Mv.', size=10)
    plt.ylabel('PAC Density %', size=10)
    plt.title(f'PAC Density per Movement in {TestData.Label} Diachronically Sorted', size=12)
    plt.show()

#=======Main script=========
SearsData = LabeledData()
SearsData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
SearsData.DataFileEnding = ".xml"
SearsData.LabelFileEnding = ".txt"
SearsData.PACMeasureIndex = 2
SearsData.RowSearchString = "Cadence Category"
SearsData.TotalNumMeasures = 0 # computed from files
SearsData.Label = "Haydn String Quartets"
SearsData.Composer = "Haydn"

DCMData = LabeledData()
DCMData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/cadences'
DCMData.DataFileEnding = ".xml"
DCMData.LabelFileEnding = '.tsv'
DCMData.PACMeasureIndex = 1
DCMData.RowSearchString = "cadence"
DCMData.TotalNumMeasures = 0 # computed from files
DCMData.Label = "Mozart Piano Sonatas"
DCMData.Composer = "Mozart"

ABCData = LabeledData()
ABCData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/ABC_DCM/ABC/data/tsv'
ABCData.DataFileEnding = ".mxl"
ABCData.LabelFileEnding = ".tsv"
ABCData.PACMeasureIndex = [] # no labelled cadences in beethoven path
ABCData.RowSearchString = []
ABCData.TotalNumMeasures = 0 # computed from files
ABCData.Label = "Beethoven String Quartets"
ABCData.Composer = "Beethoven"

# set which database to compare to
TestData = DCMData
optimize_false_positives = False

# set state machine data
StateMachineData = LabeledData()
StateMachineData.DataPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'
StateMachineData.PACMeasureIndex = 1
StateMachineData.LabelFileEnding = f"{TestData.DataFileEnding.replace('.', '_')}_Analyzed.txt"

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
NumMeasuresString = "NumMeasures"
NumMeasuresIndex = 1

def get_full_list_with_ending(root_dir, file_ending, string_filter = None):
    full_list = [os.path.join(root_dir, subdir, file)
                 for subdir, dirs, files in os.walk(root_dir)
                 for file in files
                 if os.path.splitext(file)[-1] in file_ending and (not string_filter or string_filter in file)]
    return full_list

full_list = sorted(get_full_list_with_ending(TestData.DataPath, TestData.LabelFileEnding))

for labelled_fp in sorted(full_list):
    labelled_file = os.path.split(labelled_fp)[-1]
    if labelled_file.endswith(TestData.LabelFileEnding):
        # define path for Test Data
        print(f"Analyzing {labelled_file}")

        CurrTestCadences = []
        CurrStateMachineCadences = []
        CurrFalsePositives = []
        CurrFalseNegatives = []

        # find test cadences (if they exist)
        if TestData.PACMeasureIndex:
            with open(labelled_fp, 'r') as f:
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
        MyFile = labelled_file.replace(TestData.LabelFileEnding, StateMachineData.LabelFileEnding)
        MyFullPath = os.path.join(StateMachineData.DataPath, MyFile)

        with open(MyFullPath,'r') as f:
            lines = f.readlines()
            CurrNumMeasures = []
            for line in lines:
                elements = line.strip().split(" ")
                if NumMeasuresString in line:
                    CurrNumMeasures = int(elements[NumMeasuresIndex])
                elif CadenceString in line:
                    print(elements)
                    CurrStateMachineCadences.append(str(elements[StateMachineData.PACMeasureIndex]))
            TestData.TotalNumMeasures = TestData.TotalNumMeasures + CurrNumMeasures
            PAC_density = len(CurrStateMachineCadences)/CurrNumMeasures
            print("PAC density: ", PAC_density)

        FileNameForText = labelled_file.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")

        for item in list(set(CurrTestCadences).intersection(CurrStateMachineCadences)):
            TotalCommonPacs.append(item)

        for item in CurrTestCadences:
            TotalTest.append(item)

        for item in CurrStateMachineCadences:
            TotalStateMachine.append(item)

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
        PredictionsTable.append([FileNameForText, ",".join(CurrStateMachineCadences), PAC_density])

# writing to console
table_to_console = CombinedTableExtended if TestData.PACMeasureIndex else PredictionsTable
print('========Detection Table:==========')
for row in table_to_console:
    for col, item in enumerate(row):
        if col > 0 and col < len(row)-1:
            split_item = item.split(',')
            if split_item != ['']:
                item = [int(i) for i in split_item]
                row[col] = sorted(item)
    print(row)

mv_str, diachronically_sorted_predictions = diachronic_sort(PredictionsTable)
plot_diachronic_analysis(mv_str, diachronically_sorted_predictions)

# wrinting to latex
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
if TestData.PACMeasureIndex:
    FullPathResults = os.path.join(StateMachineData.DataPath, f"../Results/{TestData.Label}_ScoresLatexTable_{current_time}.txt")
    ClassificationResultsTable = compute_classification_scores()
    write_table_to_latex(ClassificationResultsTable, FullPathResults)
    max_misses = 0
    max_false = 0
    max_both = 0
    min_misses = 100
    min_false = 100
    min_both = 100
    for row in CombinedTableExtended:
        missed_cadences = len(row[4])
        if missed_cadences >= max_misses:
            max_misses = missed_cadences
            max_row_misses = row
        if missed_cadences <= min_misses:
            min_misses = missed_cadences
            min_row_misses = row
        false_cadences = len(row[3])
        if false_cadences >= max_false:
            max_false = false_cadences
            max_row_false = row
        if false_cadences <= min_false:
            min_false = missed_cadences
            min_row_false = row
        both = missed_cadences + false_cadences
        if both >= max_both:
            max_both = both
            max_row_both = row
        if both <= min_both:
            min_both = both
            min_row_both = row

    print('===best cases:===')
    print(min_row_misses[0])
    print('missed cadences:', min_row_misses[4] if len(min_row_misses[4])>0 else None)
    print(min_row_false[0])
    print('false cadences:', min_row_false[3] if len(min_row_misses[3])>0 else None)
    print(min_row_both[0])
    print('missed:', min_row_both[4] if len(min_row_both[4])>0 else None, 'false:', min_row_both[3] if len(min_row_both[3]) > 0 else None)
    print('===worst cases:===')
    print(max_row_misses[0])
    print('missed cadences:', max_row_misses[4] if len(max_row_misses[4])>0 else None)
    print(max_row_false[0])
    print('false cadences:', max_row_false[3] if len(max_row_misses[4])>0 else None)
    print(max_row_both[0])
    print('missed:', max_row_both[4] if len(max_row_both[4]) > 0 else None, 'false:', max_row_both[3] if len(max_row_both[3]) > 0 else None)
    path = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/'

    file_to_open = max_row_false[0] if optimize_false_positives else max_row_misses[0]
    full_path = os.path.join(path, file_to_open.replace('.tsv','_').replace(' ','_')) + 'xml_Analyzed.xml'
    subprocess.call(('open', full_path))



