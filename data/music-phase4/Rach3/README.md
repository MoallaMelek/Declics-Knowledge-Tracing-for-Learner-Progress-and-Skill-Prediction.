
# The Rach3 MIDI Dataset

## Introduction
The Rach3 MIDI Dataset is a collection of MIDI Recordings of piano rehearsal sessions of four different pianists collected over four years, which records the progression of pianists learning new repertoire, as well as practicing familiar pieces, all in the Western Classical tradition. There are a total of 3152 MIDI files in total, as well as the corresponding scores in MusicXML format for many of the pieces in the dataset.
The dataset also contains one recital by one of the four pianists. A recital is a live performance of a collection of selected pieces that were part of the rehearsal repertoire. The purpose of conducting recitals is to incentivise and motivate rehearsals that are catered towards the goal of a live performance.

The four pianists are labelled according to the following performer ids:

- p1 (Advanced)
- p2 (Advanced)
- p3 (Beginner)
- p4 (Advanced)

Further information, including details regarding preliminary analysis on this dataset is available [here](https://r3midi.rach3project.com/).

## Folder Structure

1. **rehearsals** (folder):
    - This folder contains all the rehearsal sessions of the four pianists. The folder is further subdivided according to the pianists' ids: p1, p2, p3 and p4. In each pianist's subfolder is a collection of MIDI files where each file corresponds to a particular piece being practised on a particular session on a particular day.

2. **scores** (folder):
    - This folder is a collection of all the available scores in MusicXML format.

3. **recitals** (folder):
    - Similar to the rehearsals folder, the recitals folder contains subfolders corresponding to each pianist's recital session. This is further divided into subfolders corresponding to each recital session. In this initial release, there is only one recital session corresponding to pianist 1 (p1) that has been recorded.

4. **List_of_pieces_with_scores.csv**:
    - This csv file provides a table of the pieces that are rehearsed in this dataset with the following columns:
        1. *Composer*: The composer of the piece.
        2. *Work Name*: The name of the piece.
        3. *Movement/Section/Piece*: Further additional information related to the movement or section or piece number of the particular work.
        4. *ID*: The special 12 alphanumeric character identifier of each piece being rehearsed in the dataset.
        5. *Score Available?*: If the score of this specific piece is available in the dataset, the corresponding entry is marked as 'Yes', otherwise 'No'.

5. **List_of_pieces_with_scores.md**:
    - A human-readable version of *List_of_pieces_with_scores.csv*

## File Naming Convention
The Rach3 MIDI Dataset follows a standardized file naming convention that allows the identification of each piece being rehearsed/performed in the dataset. This was done to allow users to easily identify the performer, date and piece from the file name.

1. Rehearsal file naming convention: Every rehearsal MIDI file contains 25 alphanumeric characters in total (excluding the '.mid' file extension) that describe all the necessary information regarding that specific rehearsal piece:

    - The first two characters refer to the pianist in the dataset: either p1, p2, p3 or p4.
    - The following 6 numeric digits correspond to the date of the rehearsal in YYMMDD format.
    - A single numeric digit follows the date that corresponds to the rehearsal session on that specific date. A rehearsal session is defined as a period of time that a pianist considers as one 'sitting', where they practice a certain number of pieces/exercises one after another. The first session on a given date is assigned the number '0', the second session - number '1', and so on.
    - The next two numeric digits corresponds to the piece number being practiced in a particular session on a particular day. The first piece is assigned the number '01', followed by '02', and so on.
    - The final 12 alphanumeric characters of the filename correspond to the piece ID, which is a unique identifier for each piece in the dataset. The first 6 characters help to identify the composer of the piece, while the last 6 characters assist in identifying the musical work and its movement/section. Each 12 alphanumeric ID is listed in the 'ID' column in *List_of_pieces_with_scores.csv*.

2. Score file naming convention: Every score file contains 12 alphanumeric characters in the file name (apart from the '.musicxml' file extension) that correspond to the piece ID that was described in *List_of_pieces_with_scores.csv*.

3. Recital file naming convention: the recital files follow the same naming convention as the rehearsal files, except that the digit corresponding to the session number (the 9th character in the file name) is replaced with the alphabet 'r'.

## Things to note
A few rehearsal pieces do not have a MusicXML score file available yet. Such files have been marked in the *List_of_pieces_with_scores.csv* file.
Some rehearsal pieces such as Mozart's 12 variations, as well as Schumann's Album For the Young contain all (or part of) the individual pieces within one MIDI file and are not separated. The respective score of all of Mozart's 12 variations in one score file (piece ID: mozart265v12) is available. 

However, the combined score of all of Schumann's Album for the Young (piece ID: schumajugn00) is not available. However, the individual score files of each of Schumann's Album for the Young are available and provided.


## Citing this work

If you use the dataset, we would appreciate if you could cite our work!

```bibtex
@inproceedings{rach3_midi_dataset,
	address = {Daejeon, South Korea},
	title = {Enabling {Empirical} {Analysis} of {Piano} {Performance} {Rehearsal} with the {Rach3} {MIDI} {Dataset}},
	language = {en},
	booktitle = {Proceedings of the 26th {International} {Society} for {Music} {Information} {Retrieval} {Conference} ({ISMIR} 2025)},
	author = {Morsi, Alia and Chiruthapudi, Suhit and Peter, Silvan and Pilkov, Ivan and Bishop, Laura and Maezawa, Akira and Serra, Xavier and Cancino-Chacón, Carlos},
	address = {Daejeon, South Korea},
	year = {2025}
}
```

## Acknowledgements
This work has been supported by the Austrian Science Fund (FWF), grant agreement PAT 8820923 (*Rach3: A Computational Approach to Study Piano Rehearsals*), by the European Research Council (ERC) under the EU’s Horizon 2020 research & innovation programme, grant agreement No.~101019375 (*Whither Music?*), and the Research Council of Norway through its Centres of Excellence scheme, project number 262762.`
