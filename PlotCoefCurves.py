import pickle
from matplotlib import pyplot as plt
import pandas as pd
import os
import numpy as np
from itertools import cycle

coefs_file = '/Users/matanba/Dropbox/PhD/CadencesResearch/StateMachineData/K284-3_xml_Coefs_CDKeyDetectionModes.KSWithSmoothingCadenceSensitive.txt'
with open(coefs_file, 'rb') as f:
    coefs = pickle.load(f)

df = pd.DataFrame(coefs)
plt.figure(1)
lines = ["-","--","-.",":"]
linecycler = cycle(lines)
n_measures=260
plot_keys = ['D','A','G','d']
labels=[]
for i,key in enumerate(df.keys()):
    if key in plot_keys:
        plt.plot(df[key][:n_measures],label=key)
        labels.append(key)
plt.legend([key for key in labels], loc=5, prop={'size': 8})
split_name = os.path.split(coefs_file)
split_name2 = split_name[-1].split('_')
plt.title(f'First {n_measures} measures of {split_name2[0]}')
plt.xlabel('measure')
plt.ylabel('K-S correlaton coef per key')
plt.show()
