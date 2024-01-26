import music21 as m21
import os
import time
import multiprocessing as mp
import copy
import tqdm

HomeDir = os.path.expanduser("~") if os.name != 'nt' else os.environ['USERPROFILE']
InputPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml')
OutputPath = os.path.join(HomeDir,'Dropbox/PhD/CadencesResearch/DCMLab/mozart_piano_sonatas/scores_xml/PitchShifted')
if not os.path.exists(OutputPath):
    os.mkdir(OutputPath)
XMLFileEnding = '.xml'
DoParallelProcessing = 1

def processFile(file):
    if file.endswith(XMLFileEnding):
        # define path
        FullInputPath = os.path.join(InputPath, file)
        print('processing ', FullInputPath)
        NoteStream = m21.converter.parse(FullInputPath)
        for i in range(-6, 6):
            TransposedNoteStream = copy.deepcopy(NoteStream)
            TransposedNoteStream.transpose(i, inPlace=True)
            fileNoEnd = os.path.splitext(file)[0]
            FullOutputPath = os.path.join(OutputPath,fileNoEnd+"ps"+str(i)+".xml")
            TransposedNoteStream.write(fp=FullOutputPath)

if __name__ == '__main__':
    fileList = sorted(os.listdir(InputPath))
    start = time.time()
    if DoParallelProcessing:
        print("Parallel Processing On")
        print("Number of processors: ", mp.cpu_count())
        pool = mp.Pool(mp.cpu_count())
        tqdm.tqdm(pool.map_async(processFile, [file for file in fileList]).get(), total=len(fileList))
        pool.close()
    else:
        print("Parallel Processing Off")
        for file in fileList:
            processFile(file)

    end = time.time()
    total_time = end - start
    print("Elapsed time",total_time/60,"minutes")