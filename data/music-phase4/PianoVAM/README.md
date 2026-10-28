---
license: cc-by-nc-sa-4.0
language:
- en
pretty_name: "PianoVAM: A Multimodal Piano Performance Dataset"
annotations_creators:
- expert-generated
- machine-generated
source_datasets:
- original
tags:
- music-information-retrieval
- automatic-music-transcription
- piano-performance
- piano-fingering
- multimodal
modalities:
- audio
- video
- structured-data
configs:
- config_name: midi_notes
  data_files: "TSV/*.tsv"
  sep: "\t"
  comment: "#"
  column_names: ["onset", "key_offset", "frame_offset", "note", "velocity"]
  default: true
- config_name: fingering
  data_files: "Fingering/*.tsv"
  sep: "\t"
- config_name: fingering_gt
  data_files: "Fingering_GT/*.tsv"
  sep: "\t"
---

# PianoVAM v1.2: A Multimodal Piano Performance Dataset

## Version History

* **v1.2 (current).** Adds `Fingering/` (per-note fingering labels for 106 recordings) and `Fingering_GT/` (manual fingering annotations for 11 recordings). All other files are unchanged from v1.1.
* **v1.1.** `metadata.json` is the canonical split file. Video files for the `'Sep 04-05'` recordings are the sync-corrected versions, and files previously found to have video-MIDI synchronization issues have been relocated across splits; the current splits reflect these corrections.
* **v1.0.** Initial release (ISMIR 2025).

## Summary

This repository contains the **PianoVAM (Video, Audio, Midi and Metadata)** dataset, a multi-modal collection of piano performances designed for research in Music Information Retrieval (MIR).

The dataset features synchronized recordings of various piano pieces, providing rich data across several modalities. Our goal is to provide a comprehensive resource for developing and evaluating models that can understand the complex relationship between the visual, auditory, and symbolic aspects of music performance.

## How to Cite

If you use the PianoVAM dataset in your research, please cite it as follows:

```bibtex
@inproceedings{kim2025pianovam,
  title={PianoVAM: A Multimodal Piano Performance Dataset},
  author={Kim, Yonghyun and Park, Junhyung and Bae, Joonhyung and Kim, Kirak and Kwon, Taegyun and Lerch, Alexander and Nam, Juhan},
  booktitle={Proceedings of the 26th International Society for Music Information Retrieval Conference (ISMIR)},
  year={2025}
}
```

## Usage Guide

### 0. How to Download the Entire Dataset

The recommended way to download the entire dataset (including all large video files) is to use the `huggingface-cli` command line tool.

1.  **Install the Hugging Face Hub library**:
    If you don't have it installed, open your terminal and run:

    ```bash
    pip install huggingface_hub
    ```

2.  **Download the dataset**:
    Run the following command in your terminal. This will download all repository files, including LFS data, into a folder named `PianoVAM_v1.2`.

    ```bash
    huggingface-cli download PianoVAM/PianoVAM_v1 --repo-type dataset --local-dir ./PianoVAM_v1.2
    ```

    (The repo was previously named `PianoVAM_v1.0`; Hugging Face automatically redirects the old URL to `PianoVAM_v1`.)

### 1. Load and Prepare the Dataset

This initial script loads the dataset, constructs the necessary file URLs, and prepares the audio for direct access.

```python
from datasets import load_dataset, Audio
import requests
import os
import numpy as np
from scipy.io.wavfile import write

# Load dataset from the Hub
dataset = load_dataset("PianoVAM/PianoVAM_v1")

# Construct full URLs for all media files
def create_full_media_urls(example):
    base_url = "https://huggingface.co/datasets/PianoVAM/PianoVAM_v1/resolve/main/"
    example["audio_url"] = base_url + example["audio_path"]
    example["video_url"] = base_url + example["video_path"]
    example["midi_url"] = base_url + example["midi_path"]
    return example

dataset = dataset.map(create_full_media_urls)

# Cast the audio_url column for automatic audio decoding
dataset = dataset.cast_column("audio_url", Audio())

# Prepare a sample example from the training set
example = dataset["train"][0]
```

### 2. Access Decoded Data

After preparation, you can directly access metadata and the decoded audio array.

```python
# Access metadata
print(f"Piece: {example['piece']} by {example['composer']}")
print(f"Performer: {example['P1_name']}")

# Access the decoded audio data object
audio_data = example["audio_url"]
print(f"Audio sampling rate: {audio_data['sampling_rate']}")
print(f"Audio array shape: {audio_data['array'].shape}")
```

**Output:**

```
Piece: Piano Concerto by E. Grieg
Performer: Yonghyun
Audio sampling rate: 44100
Audio array shape: (32876256,)
```

### 3. Download Source Files

Use the following methods to download the original source files to your local machine.

```python
# --- Download Audio File (.wav) ---
audio_array = example["audio_url"]['array']
sampling_rate = example["audio_url"]['sampling_rate']
local_filename = os.path.basename(example['audio_path'])
write(local_filename, sampling_rate, audio_array.astype(np.float32))
print(f"Audio saved as '{local_filename}'")

# --- Download Video File (.mp4) ---
video_url = example['video_url']
local_filename = os.path.basename(video_url)
response = requests.get(video_url)
response.raise_for_status()
with open(local_filename, 'wb') as f:
    f.write(response.content)
print(f"Video saved as '{local_filename}'")

# --- Download MIDI File (.mid) ---
midi_url = example['midi_url']
local_filename = os.path.basename(midi_url)
response = requests.get(midi_url)
response.raise_for_status()
with open(local_filename, 'wb') as f:
    f.write(response.content)
print(f"MIDI saved as '{local_filename}'")
```

## Dataset Description

The dataset consists of various piano pieces performed by multiple pianists. The data was captured simultaneously from a digital piano and high-resolution cameras to ensure precise synchronization between the audio, video, and MIDI streams. The collection is designed to cover a range of musical complexities and styles.

### Note on Video Data

Please be aware that all video performances by the pianist named "jiwoo" have had a blur effect applied to the performer's upper body. This was done at the request of the performer to protect their privacy. The keyboard and hands remain fully visible and unaffected.

## Directory Structure

The dataset repository is organized into the following directories:

```
PianoVAM_v1.2/
├── Audio/
├── Fingering/
├── Fingering_GT/
├── Handskeleton/
├── MIDI/
├── TSV/
├── Video/
├── metadata.json
└── README.md
```

### Folder Contents

  * **`Audio/`**: Contains the raw audio recordings of the piano performances.

      * **Format:** Uncompressed WAV (`.wav`).
      * **Sample Rate:** 44100 Hz.

  * **`Video/`**: Contains the video recordings of the piano performances.

      * **Format:** MP4 (`.mp4`).
      * **Resolution:** 1920x1080 pixels.
      * **Frame Rate:** 60 fps.
      * **Video Codec:** H.264 (AVC).
      * **Audio Codec:** AAC.

  * **`Handskeleton/`**: Contains the 3D hand landmark data for each performance.

      * **Format:** JSON (`.json`) files.
      * **Details:** Each file contains frame-by-frame coordinates for the 21 keypoints of both the left and right hands, as captured by MediaPipe Hands.

  * **`MIDI/`**: Contains the ground truth performance data recorded directly from a digital piano.

      * **Format:** Standard MIDI Files (`.mid`).
      * **Details:** These files provide the precise timing (onset, offset), pitch, and velocity for every note played.

  * **`metadata.json`**: The canonical v1.1 split file. Maps each recording to its data split (`train`, `valid`, `test`, `ext-train`, `special(blurry)`, `special(4hands)`) and provides per-recording metadata. Splits reflect the video-MIDI sync corrections.

  * **`TSV/`**: Contains pre-processed label data derived from the MIDI files for easier parsing. Each file is a tab-separated value file with 5 columns.

      * **Format:** TSV (`.tsv`).
      * **Header:** `onset`, `key_offset`, `frame_offset`, `note`, `velocity`
      * **Column Descriptions:**
          * **`onset`**: The start time of the note in seconds.
          * **`key_offset`**: The time when the finger is **physically released** from the key, in seconds. This is useful for video-based research such as fingering analysis.
          * **`frame_offset`**: The time when the sound **completely ends**, considering pedal usage. This is analogous to the 'offset' used in traditional audio-only transcription.
          * **`note`**: The MIDI note number (pitch).
          * **`velocity`**: The MIDI velocity (how hard the key was struck).

  * **`Fingering/`**: Per-note fingering labels predicted from the video.

      * **Format:** TSV (`.tsv`), one file per recording, with the same base name as in `TSV/`.
      * **Header:** `onset`, `key_offset`, `frame_offset`, `note`, `velocity`, `hand`, `finger`
      * **Column Descriptions:**
          * The first five columns are identical to the file of the same name in `TSV/`, row for row.
          * **`hand`**: `L` (left), `R` (right), or `Noinfo`.
          * **`finger`**: `1` (thumb) to `5` (pinky) within that hand, or `Noinfo`.
      * **How the labels were made:** Hand landmarks detected with MediaPipe Hands are matched frame by frame to the keys held down in the MIDI. Each note is assigned the finger that stays on its key for most of the note's duration. This is the automatic stage of the fingering method described in Section 5 of the paper. The manual step in the paper, where an annotator resolves ambiguous notes, is not applied to these files.
      * **`Noinfo` labels:** A note is marked `Noinfo` when no finger qualifies or when several fingers qualify and none clearly dominates. Across all 525,483 notes, 19.9% are `Noinfo`, and most of these are notes where no finger qualifies. The rate varies widely between recordings, from 2.7% to 81.4% (median 15.5%), so please check it for the recordings you use.
      * **Accuracy:** We compared these labels with the `Fingering_GT/` annotations on 1,800 notes from 11 recordings. 88.2% of those notes receive a label. Of the labeled notes, 95.7% have the correct hand and finger, and 99.2% have the correct hand. Most errors are between adjacent fingers. These numbers are measured on the files in this release, so per-recording values can differ from Table 3 of the paper.
      * **Coverage:** All solo recordings, 106 of the 107 recordings. The four-hands recording `2024-02-15_22-12-41` (split `special(4hands)`) has no fingering labels because they are provided for solo performances only.

  * **`Fingering_GT/`**: Manual fingering annotations, used to evaluate `Fingering/`.

      * **Format:** TSV (`.tsv`) with the same seven columns as `Fingering/`. Every note has a hand and a finger.
      * **Coverage:** The first 300 notes of `2024-02-17_22-33-45` and the first 150 notes of 10 other recordings, 1,800 notes in total. Rows are aligned with the first rows of the matching file in `TSV/`.
      * **Source:** Annotated by the authors with the GUI annotation tool described in the paper. The same annotations are available as Python lists in [`fingergt.py`](https://github.com/yonghyunk1m/PianoVAM-Code/blob/main/FingeringDetection/detection/fingergt.py) in the PianoVAM-Code repository.

    Example:

    ```python
    import pandas as pd

    fing = pd.read_csv("Fingering/2024-02-14_19-10-09.tsv", sep="\t", dtype={"finger": str})
    labeled = fing[fing["hand"] != "Noinfo"]
    print(f"{len(labeled)} of {len(fing)} notes have a fingering label")
    ```

### Planned Updates

  * **Improved fingering labels.** We are building a new fingering pipeline and plan to release more accurate labels in a future version. They will be added as a new folder. `Fingering/` will stay unchanged so that results reported on it remain reproducible.

## License

This dataset is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**. You are free to share and adapt the material for non-commercial purposes, provided you give appropriate credit and distribute your contributions under the same license.

## Contact

For any questions about the dataset, please open an issue in the Community tab of this repository or contact [Yonghyun Kim/yonghyun.kim@gatech.edu].
