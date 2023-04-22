# cadence_detector
A python package for cadence detection on music xml scores. 
The scan returns files with measure and offset locations of PACs, IACs, and HCs, as well as a musicxml file with cadence labels on the score.
# Installation 
`pip install cadence_detector`
# Running on single file
`from cadence_detector import cadence_detector`  
`cadence_detector.detect_cadences_in_file(full_path=<your_file_path>,output_path=<your_output_path>)`
# Running on folder
`from cadence_detector import cadence_detector`  
`cadence_detector.detect_cadences_in_folder(input_dir=<your_folder_path>, file_ending=<your_file_endings>, output_dir=<your_output_path>, do_parallel=True)`