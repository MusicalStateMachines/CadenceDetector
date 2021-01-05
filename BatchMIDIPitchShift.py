from music21 import *
import os
import time
import multiprocessing as mp

InputPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/'
OutputPath = '/Users/matanba/Dropbox/PhD/CadencesResearch/SearsData/PitchShifted/'
if not os.path.exists(OutputPath):
    os.mkdir(OutputPath)
XMLFileEnding = '.xml'
DoParallelProcessing = 1

def processFile(file):
    if file.endswith(XMLFileEnding):
        # define path
        FullInputPath = os.path.join(InputPath, file)
        NoteStream = converter.parse(FullInputPath)
        for i in range(1, 12):
            for currNote in NoteStream.recurse().getElementsByClass('Note'):
                currNote.transpose(1, inPlace=True)
            fileNoEnd = os.path.splitext(file)[0]
            FullOutputPath = os.path.join(OutputPath,fileNoEnd+"ps"+str(i)+".xml")
            NoteStream.write(fp=FullOutputPath)


fileList = sorted(os.listdir(InputPath))
start = time.time()
if DoParallelProcessing:
    print("Parallel Processing On")
    print("Number of processors: ", mp.cpu_count())
    pool = mp.Pool(mp.cpu_count())
    pool.map_async(processFile, [file for file in fileList]).get()
    pool.close()
else:
    print("Parallel Processing Off")
    for file in fileList:
        processFile(file)

end = time.time()
total_time = end - start
print("Elapsed time",total_time/60,"minutes")