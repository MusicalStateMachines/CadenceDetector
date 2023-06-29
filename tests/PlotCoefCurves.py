import pickle
from matplotlib import pyplot as plt
import pandas as pd
import os
import numpy as np
from itertools import cycle

cadence_sensitive_string = 'Cadence Sensitive'
coefs_file = f"/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/K332-2_xml_Coefs_CDKeyDetectionModes.KSWithSmoothing{cadence_sensitive_string.replace(' ','')}.txt"
with open(coefs_file, 'rb') as f:
    coefs = pickle.load(f)

df = pd.DataFrame(coefs)
plt.figure(1, figsize=(20, 12))
colors = plt.cm.tab20b(np.linspace(0,1,len(df.keys())))
lines = ["-","--","-.",":"]
linecycler = cycle(lines)
measure_from = 1
measure_to = len(df['C'])
plot_keys = ['B-','b-','F']
labels=[]
for i,key in enumerate(df.keys()):
    if 'all' in plot_keys or key in plot_keys:
        plt.plot(range(measure_from, measure_to+1), df[key][measure_from-1:measure_to],label=key, color=colors[i % len(colors)], linestyle = lines[i % len(lines)], linewidth=3)
        labels.append(key)
plt.legend([key for key in labels], loc=5, prop={'size': 12})
split_name = os.path.split(coefs_file)
split_name2 = split_name[-1].split('_')
plt.title(f'{split_name2[0]} Measures {measure_from} to {measure_to} {cadence_sensitive_string}', size=14)
plt.xlabel('measure', size=12)
plt.ylabel('K-S correlaton coef per key', size=12)
plt.show(block=False)
plt.savefig(f'{split_name2[0]} Measures {measure_from} to {measure_to} {cadence_sensitive_string}.png')

