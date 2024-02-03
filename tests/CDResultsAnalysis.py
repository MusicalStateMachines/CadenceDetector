import copy
import os
from datetime import datetime
import subprocess
import matplotlib.pyplot as plt
import numpy as np

class LabeledData:
    def __init__(self):
        self.DataPath = ''
        self.DataFileEnding = ''
        self.OutputSubpath = ''
        self.LabelFileEnding = ''
        self.PACMeasureIndex = -1
        self.RowSearchString = ''
        self.TotalNumMeasures = 0
        self.Name = ''
        self.isLabelled = False
        self.Composer = ''

def write_table_to_latex(table, file_full_path, comment=None):
    text_file_results = open(file_full_path, "w")
    print(f"% {comment}\n", file=text_file_results)
    print(" \\\\\n".join([" & ".join(map(str, line)).replace('[', '').replace(']', '') for line in table])+" \\\\", file=text_file_results)
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
    F1 = 2 * (Precision * Recall) / (Precision + Recall)
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
    ClassificationResultsTable.append(["F1", "{0:0.2f}".format(F1)])
    print('========Classification Scores:==========')
    for row in ClassificationResultsTable:
        print(row)
    return ClassificationResultsTable

def diachronic_sort(input_table):
    table_diachronically_sorted = []
    mov_str= []
    if TestData == SearsData:
        table_diachronically_sorted = sorted([[int(row[0].split(' ')[1].split('op')[1]),
                                               int(row[0].split(' ')[2].split('no')[1]),
                                               int(row[0].split(' ')[3].split('mv')[1].split('.')[0]),
                                               row[1], row[2], row[3]] for row in input_table])
        mov_str = [str(row[:3]) for row in table_diachronically_sorted]
    elif TestData == DCMData:
        table_diachronically_sorted = sorted([[int(row[0].split('-')[0].split('K')[1]),
                                               int(row[0].split('-')[1].split('.')[0]),
                                               row[1], row[2], row[3]] for row in input_table])
        mov_str = [str(row[:2]) for row in table_diachronically_sorted]
    elif TestData == ABCData:
        table_diachronically_sorted = sorted([[int(row[0].split(' ')[0].split('op')[1]),
                                               int(row[0].split(' ')[1].split('no')[1]),
                                               int(row[0].split(' ')[2].split('mov')[1].split('.')[0]),
                                               row[1], row[2], row[3]] for row in input_table])
        mov_str = [str(row[:3]) for row in table_diachronically_sorted]
    elif TestData == WTCData:
        table_diachronically_sorted = sorted([[int(row[0].split('BWV ')[1].split(' ')[0]),
                                               row[1], row[2], row[3]] for row in input_table])
        mov_str = [str(row[0]) for row in table_diachronically_sorted]

    print('========Diachronically Sorted Table:==========')
    for row in table_diachronically_sorted:
        print(row)
    return mov_str, table_diachronically_sorted

def plot_diachronic_analysis(mov_str, table_diachronically_sorted):
    PAC_density_per_mov = [row[-2] * 100 for row in table_diachronically_sorted]
    x = range(len(PAC_density_per_mov))
    coef = np.polyfit(x, PAC_density_per_mov, 1)
    poly1d_fn = np.poly1d(coef)
    # poly1d_fn is now a function which takes in x and returns an estimate for y
    _, ax = plt.subplots(figsize=(15, 8))
    ax.plot(PAC_density_per_mov)
    ax.plot(x, poly1d_fn(x), '--k')
    ax.locator_params(nbins=len(PAC_density_per_mov), axis='x')
    ax.xaxis.set_ticks(x)
    ax.set_xticklabels(mov_str, rotation=45, size=8)
    plt.ylim(0, 25)
    if TestData == SearsData or TestData == ABCData:
        plt.xlabel('Op. No. Mv.', size=12)
    elif TestData == DCMData:
        plt.xlabel('K. Mv.', size=12)
    plt.ylabel('PAC Density %', size=12)
    plt.title(f'{CadenceString} Density per Movement in {TestData.Name} Diachronically Sorted', size=14)
    plt.show(block=False)
    plt.savefig(f'{CadenceString} Density Per Movement {TestData.Name}.png')

def plot_temporal_historgam(temporal_cadence_list):
    _, ax = plt.subplots(figsize=(15, 8))
    bins = np.arange(0, 1, 0.03)  # fixed bin size with resolution
    counts, bins, _ = ax.hist(temporal_cadence_list, bins=bins, rwidth=0.8)
    bin_centers = bins[:-1] + np.diff(bins) / 2
    smooth_counts = np.convolve(counts, np.blackman(5), mode='same')
    bins_high_res = np.arange(0, 1, 0.01)
    smooth_counts = np.interp(bins_high_res, bin_centers, smooth_counts)
    ax.plot(bins_high_res, smooth_counts, '--k')
    plt.xlim([0,1])
    plt.title(f'Temporal Position Distribution of {CadenceString}s in {TestData.Name}', size=14)
    plt.xlabel('Time % in Movement', size=12)
    plt.ylabel('Cadence Count', size=12)
    plt.savefig(f'Temporal Position Distribution of {CadenceString}s {TestData.Name}.png')
    plt.show(block=False)

def plot_temporal_pos_per_mov(mov_str, table_diachronically_sorted):
    temporal_perctanges = [row[-1] * 100 for row in table_diachronically_sorted]
    _, ax = plt.subplots(figsize=(15, 8))
    colors = plt.cm.tab20b(np.linspace(0, 1, 3))
    for i, mov in enumerate(temporal_perctanges):
        ax.scatter([i] * len(mov), mov, color=colors[i % 3], alpha=0.5)
    leg=ax.legend(['mov 1', 'mov 2', 'mov 3'],loc=(1.02, 0.5))
    for lh in leg.legendHandles:
        lh.set_alpha(1)
    x = range(len(temporal_perctanges))
    ax.locator_params(nbins=len(temporal_perctanges), axis='x')
    ax.xaxis.set_ticks(x)
    ax.set_xticklabels(mov_str, rotation=45, size=8)
    if TestData == SearsData or TestData == ABCData:
        plt.xlabel('Op. No. Mv.', size=12)
    elif TestData == DCMData:
        plt.xlabel('K. Mv.', size=12)
    plt.ylabel('Cadence Temporal Position %', size=12)
    plt.title(f'{CadenceString} Temporal Positions in {TestData.Name} Diachronically Sorted', size=14)
    plt.savefig(f'{CadenceString} Temporal Positions Per Movement {TestData.Name}.png')
    plt.show()


HomeDir = os.path.expanduser("~") if os.name != 'nt' else os.environ['USERPROFILE']

#=======Main script=========
SearsData = LabeledData()
SearsData.DataPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/SearsData')
SearsData.OutputSubpath = "SearsHaydn"
SearsData.DataFileEnding = ".xml"
SearsData.LabelFileEnding = ".txt"
SearsData.PACMeasureIndex = 2
SearsData.RowSearchString = "Cadence Category"
SearsData.TotalNumMeasures = 0 # computed from files
SearsData.Name = "Haydn String Quartets"
SearsData.Composer = "Haydn"
SearsData.isLabelled = True

DCMData = LabeledData()
DCMData.DataPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/cadences')
DCMData.OutputSubpath = "DCMLabMozart"
DCMData.DataFileEnding = ".xml"
DCMData.LabelFileEnding = '.tsv'
DCMData.PACMeasureIndex = 1
DCMData.RowSearchString = "cadence"
DCMData.TotalNumMeasures = 0 # computed from files
DCMData.Name = "Mozart Piano Sonatas"
DCMData.Composer = "Mozart"
DCMData.isLabelled = True

ABCData = LabeledData()
ABCData.DataPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/ABC_DCM/ABC/data/tsv')
ABCData.OutputSubpath = "DCMLabBeethoven"
ABCData.DataFileEnding = ".mxl"
ABCData.LabelFileEnding = ".tsv"
ABCData.PACMeasureIndex = [] # no labelled cadences in beethoven path
ABCData.RowSearchString = []
ABCData.TotalNumMeasures = 0 # computed from files
ABCData.Name = "Beethoven String Quartets"
ABCData.Composer = "Beethoven"
ABCData.isLabelled = False

WTCData = LabeledData()
WTCData.DataPath = os.path.join(HomeDir,'/Dropbox/PhD/CadencesResearch/BachWTC/algomus-data-master/fugues')
WTCData.OutputSubpath = "BachWTC"
WTCData.DataFileEnding = ".mxl"
WTCData.LabelFileEnding = ""
WTCData.PACMeasureIndex = 0
WTCData.RowSearchString = "cadences"
WTCData.TotalNumMeasures = 0 # computed from files
WTCData.Name = "Bach Well Tempered Clavier Book 1 Fugues"
WTCData.Composer = "Bach"
WTCData.isLabelled = True

# ==================================
# set which database to compare to
# ==================================
TestData = SearsData
optimize_false_positives = False
CadenceString = "PAC"
filter_movements = None #['284-3','331-1','570-1']

# set state machine data
StateMachineData = LabeledData()
StateMachineData.DataPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/StateMachineData', TestData.OutputSubpath)
StateMachineData.PACMeasureIndex = 1
StateMachineData.LabelFileEnding = f"{TestData.DataFileEnding.replace('.', '_')}_Analyzed.txt"

CombinedTable = []
CombinedTableExtended = []
LabelsTable = []
PredictionsTable = []
TotalTest = []
TotalStateMachine = []
TotalStateMachineTemporalPercent = []
TotalCommonPacs = []
TotalFP = []
TotalFN = []
NumMeasuresString = "NumMeasures"
NumMeasuresIndex = 1

def get_full_list_with_ending(root_dir, file_ending, string_filter = None):
    full_list = [os.path.join(root_dir, subdir, file)
                 for subdir, dirs, files in os.walk(root_dir)
                 for file in files
                 if os.path.splitext(file)[-1] in file_ending and (not string_filter or not any(s in file for s in string_filter))]
    return full_list


import re
def parse_cadences_from_work(analysis_text):
    cadences = []
    in_cadences_section = False
    for line in analysis_text.split('\n'):
        line = line.strip()
        # Check if it's the start of the cadences section
        if line.startswith('== cadences'):
            in_cadences_section = True
        elif in_cadences_section and line.startswith('*'):
            # Process cadence lines
            matches = re.finditer(r'(\d+(\.\d+)?)\s+\(([^)]+)\)', line)
            for match in matches:
                measure, _, cadence_type = match.groups()
                cadences.append({'measure': float(measure), 'cadence': cadence_type})
    return cadences


def parse_bach_fugue_cadences_from_file(file_path):
    all_data = []
    with open(file_path, 'r') as file:
        current_data = None
        current_occurrence = ''
        for line in file:
            line = line.strip()
            # Check if it's the start of a new occurrence
            if line.startswith('==== wtc-i'):
                if current_data:
                    current_data['cadences'] = parse_cadences_from_work(current_occurrence)
                    all_data.append(current_data)
                current_data = {'work': line[4:].strip()}
                current_occurrence = line + '\n'
            elif current_data is not None:
                # Check for the end of the current occurrence
                if line.startswith('=='):
                    current_occurrence += line + '\n'
                else:
                    current_occurrence += line + '\n'
    # Process the last occurrence after the loop
    if current_data:
        current_data['cadences'] = parse_cadences_from_work(current_occurrence)
        all_data.append(current_data)

    return all_data


if TestData == WTCData:
    file_path = r"/Users/matanba/Dropbox/PhD/CadencesResearch/BachWTC/algomus-data-master/fugues/fugues.ref"  # Replace with your actual file path
    full_list = parse_bach_fugue_cadences_from_file(file_path)
else:
    full_list = sorted(get_full_list_with_ending(TestData.DataPath, TestData.LabelFileEnding, string_filter=filter_movements))

for labelled_fp in full_list:
    labelled_file = os.path.split(labelled_fp)[-1] if TestData is not WTCData else labelled_fp['work']
    if labelled_file.endswith(TestData.LabelFileEnding):
        # define path for Test Data
        print(f"Analyzing {labelled_file}")
        CurrTestCadences = []
        CurrStateMachineCadences = []
        CurrStateMachineCadencesTemporalPercent = []
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
                            CurrTestCadences.append(int(elements[TestData.PACMeasureIndex]))
                            # print(line, file=text_file_reduced)

        else:
            data = labelled_fp['cadences']
            for cad in data:
                if CadenceString in cad['cadence']:
                    CurrTestCadences.append(int(cad['measure']))

        # find equivalent in MyPath
        if TestData is not WTCData:
            MyFile = labelled_file.replace(TestData.LabelFileEnding, StateMachineData.LabelFileEnding)
        else:
            match = re.search(r'BWV (\d+)', labelled_fp['work'])
            if match:
                bwv_number = match.group(1)
            MyFile = f"BWV_0{bwv_number}b_mxl_Analyzed.txt"
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
                    CurrStateMachineCadences.append(int(elements[StateMachineData.PACMeasureIndex]))
            for cad_measure in CurrStateMachineCadences:
                CurrStateMachineCadencesTemporalPercent.append(cad_measure/CurrNumMeasures)
            TestData.TotalNumMeasures = TestData.TotalNumMeasures + CurrNumMeasures
            PAC_density = len(CurrStateMachineCadences)/CurrNumMeasures
            print("PAC density: ", PAC_density)

        FileNameForText = labelled_file.replace(".txt", " ")
        FileNameForText = FileNameForText.replace("_", " ")
        FileNameForText = FileNameForText.replace('.tsv', '')

        # *set(l) removes duplicates from lists
        CurrTestCadences = sorted([*set(CurrTestCadences)])
        CurrStateMachineCadences = sorted([*set(CurrStateMachineCadences)])
        CurrStateMachineCadencesTemporalPercent = sorted([*set(CurrStateMachineCadencesTemporalPercent)])

        for item in list(set(CurrTestCadences).intersection(set(CurrStateMachineCadences))):
            TotalCommonPacs.append(item)
        TotalCommonPacs = sorted(TotalCommonPacs)

        for item in CurrTestCadences:
            TotalTest.append(item)
        TotalTest = sorted(TotalTest)

        for item in CurrStateMachineCadences:
            TotalStateMachine.append(item)
        TotalStateMachine = sorted(TotalStateMachine)

        for item in CurrStateMachineCadencesTemporalPercent:
            TotalStateMachineTemporalPercent.append(item)

        for item in list(set(CurrStateMachineCadences).symmetric_difference(set(CurrTestCadences))):
            if item in CurrStateMachineCadences:
                CurrFalsePositives.append(item)
            else:
                CurrFalseNegatives.append(item)
        CurrFalsePositives = sorted(CurrFalsePositives)
        CurrFalseNegatives = sorted(CurrFalseNegatives)

        for item in CurrFalsePositives:
            TotalFP.append(item)

        for item in CurrFalseNegatives:
            TotalFN.append(item)

        if len(TotalCommonPacs) + len(TotalFN) != len(TotalTest):
            raise Exception('Something is wrong with this computation, len(TotalCommonPacs) + len(TotalFN) != len(TotalTest)')

        if len(TotalCommonPacs) + len(TotalFP) != len(TotalStateMachine):
            raise Exception('Something is wrong with this computation, len(TotalCommonPacs) + len(TotalFP) != len(TotalStateMachine)')

        CombinedTable.append([FileNameForText, CurrTestCadences, CurrStateMachineCadences])
        CombinedTableExtended.append([FileNameForText, CurrTestCadences, CurrStateMachineCadences, CurrFalsePositives, CurrFalseNegatives])
        LabelsTable.append([FileNameForText, CurrTestCadences])
        PredictionsTable.append([FileNameForText, CurrStateMachineCadences, PAC_density, CurrStateMachineCadencesTemporalPercent])

# writing to console
table_to_console = copy.deepcopy(CombinedTableExtended) if TestData.isLabelled else copy.deepcopy(PredictionsTable)
print('========Detection Table:==========')
for row in table_to_console:
    print(row)

mv_str, diachronically_sorted_predictions = diachronic_sort(PredictionsTable)
# plot PAC density diachronic
plot_diachronic_analysis(mv_str, diachronically_sorted_predictions)
# plot temporal distribution of cadences
plot_temporal_historgam(TotalStateMachineTemporalPercent)
# plot temporal position per move of cadences
plot_temporal_pos_per_mov(mv_str, diachronically_sorted_predictions)

# writing to latex
now = datetime.now()
current_time = now.strftime("%Y_%m_%d_%H_%M_%S")
write_dir = os.path.join(StateMachineData.DataPath, os.pardir, 'Results', TestData.Name, CadenceString)
os.makedirs(write_dir,exist_ok=True)

# write full table in latex format
FullPathResults = os.path.join(write_dir, f"{TestData.Name}_FullClassificationsLatexTable.tex")
write_table_to_latex(CombinedTable, FullPathResults, comment=current_time)

# write partial tables latex format
FullPathResults = os.path.join(write_dir, f"{TestData.Name}_LabelsLatexTable.tex")
write_table_to_latex(LabelsTable, FullPathResults, comment=current_time)

FullPathResults = os.path.join(write_dir, f"{TestData.Name}_PredictionsLatexTable.tex")
write_table_to_latex([line[:2] for line in PredictionsTable], FullPathResults, comment=current_time)

# write summary table in latex format
if TestData.isLabelled:
    FullPathResults = os.path.join(write_dir, f"{TestData.Name}_ScoresLatexTable.tex")
    ClassificationResultsTable = compute_classification_scores()
    write_table_to_latex(ClassificationResultsTable, FullPathResults, comment=current_time)
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
            min_false = false_cadences
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
    print('missed cadences:', min_row_misses[4])
    print(min_row_false[0])
    print('false cadences:', min_row_false[3])
    print(min_row_both[0])
    print('missed:', min_row_both[4], 'false:', min_row_both[3])
    print('===worst cases:===')
    print(max_row_misses[0])
    print('missed cadences:', max_row_misses[4])
    print(max_row_false[0])
    print('false cadences:', max_row_false[3])
    print(max_row_both[0])
    print('missed:', max_row_both[4], 'false:', max_row_both[3])
    path = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/StateMachineData')

    file_to_open = max_row_false[0] if optimize_false_positives else max_row_misses[0]
    full_path = os.path.join(path, file_to_open.replace(' ', '_'))
    full_path = full_path + '_' if not full_path[-1] == '_' else full_path
    full_path = full_path + 'xml_Analyzed.xml'
    #subprocess.call(('open', full_path))



