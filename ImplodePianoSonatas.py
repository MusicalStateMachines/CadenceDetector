import music21 as m21
fileString = r'/Users/matanba/Downloads/Sonate_No._8_Pathetique_3rd_Movement.xml'
NoteStream = m21.converter.parse(fileString)
NoteStream.partsToVoices()
NoteStream.write(fp=r'/Users/matanba/Downloads/Sonate_No._8_Pathetique_3rd_Movement2.xml')


