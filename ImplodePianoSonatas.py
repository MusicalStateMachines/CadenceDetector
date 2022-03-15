import music21 as m21
fileString = r'/Users/matanba/Downloads/ps01/ps01_01.mid'
NoteStream = m21.converter.parse(fileString)
NoteStream.partsToVoices()
NoteStream.write(fp=r'/Users/matanba/Downloads/ps01/ps01_01.xml')


