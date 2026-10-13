# Phase 4 licensed piano case-study material

This directory includes 12 verbatim MIDI rehearsals and the source README/LICENSE from
Rach3Project/rach3_midi_dataset at commit a9519492b086a6c039a9d0994689ca0f279186bd.
Attribution: Rach3 Project and the credited source authors; source and contributor details
remain in Rach3/README.md. Original bytes are unchanged. CC BY-NC-SA 4.0 applies to this
material, not the application's code. This is bounded noncommercial research use.

PianoVAM/PianoVAM_v1 metadata was acquired at revision
1f039ab9d6128626bff708faad6472d220b50eaa. Its dataset card is preserved in PianoVAM/README.md,
including creator/publication credit and CC BY-NC-SA 4.0 grant. The public raw metadata
contains participant names and demographics and is deliberately not redistributed here.
The application receives only participant codes, piece, source chronology and duration.

acquisition.json records pinned URLs, sizes and SHA256 receipts for every acquired file.
The raw PianoVAM metadata receipt proves acquisition but is not a bundled raw-file claim.
The sanitized derived music-case-study.json under artifacts/phase4 is adapted from both
sources; its study data is shared under CC BY-NC-SA 4.0 with these attributions. Changes:
participant codes substituted, demographics/static skill metadata omitted, descriptor
summaries and distinct-day descriptive holdouts added. No musical assessments created.
License text: Rach3/LICENSE; https://creativecommons.org/licenses/by-nc-sa/4.0/.

Reproduce into an ignored raw directory:

    python scripts/acquire_phase4_music.py
    python scripts/analyze_phase4_music.py

Network acquisition is explicit and pinned. The analyzer verifies every byte hash before
processing. MIDI parsing describes recording duration/note counts; it does not align a
score, infer errors, or create correctness labels. PianoVAM audio/video is not acquired.

For an offline Rach3-only inspection use axis7.music_case_study.rach_identity and
midi_descriptors on the bundled selected rehearsals. Complete reproduction of the combined
study requires re-fetching the pinned PianoVAM raw metadata, with its original hash verified.
