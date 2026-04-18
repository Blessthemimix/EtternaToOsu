# Etterna to osu!mania Auto-Converter

A lightweight Python script that automatically converts StepMania/Etterna chart packs (`.zip`) into fully playable osu!mania (`.osz`) beatmaps.

## Features
* **Smart Parsing:** Supports both `.sm` and `.ssc` file formats.
* **Top Difficulty Auto-Selector:** Automatically scans all difficulties in a chart and extracts the hardest one (based on Meter level and total note count).
* **Long Note (LN) Support:** Correctly translates Etterna holds and rolls into osu!mania Long Notes.
* **BSS Upload Ready:** Automatically fixes common osu! editor errors (adds `PreviewTime`, sets default `Normal` hitsounds, and assigns your osu! username as the creator) so you can upload the maps to the Beatmap Submission System without warnings.

## How to Use

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Blessthemimix/EtternaToOsu.git
   cd EtternaToOsu

    Configure the script:
    Open converter.py in any text editor and update the variables at the top of the file:

        SOURCE_ZIP: The path to your Etterna song pack .zip.

        OUTPUT_FOLDER: The directory where you want the compiled .osz files to be saved.

        YOUR_OSU_USERNAME: Your exact osu! username (required for uploading to BSS).

    And Run the script:
        python converter.py

    The script will extract the archive, locate the charts, convert them, and output .osz files into your designated output folder. Double-click the .osz files to import them into osu!.

2.How it Works

    Extraction: The script unzips the Etterna pack into a temporary directory.

    Data Scraping: It locates the .ssc or .sm files and uses regular expressions to extract metadata (Title, Artist, BPM, Offset).

    Difficulty Sorting: It splits the file into difficulty blocks (#NOTES or #NOTEDATA), reads the Meter value, and counts the notes. It picks the most intensive block to ensure you get the "Top Diff".

    Hit Object Translation: * It translates StepMania's 4-column coordinate system into osu!mania's x-axis values (64, 192, 320, 448).

        It reads 1 as a standard note (Rice).

        It uses a tracker to detect 2 (Hold Start) and waits for 3 (Hold End) in the same column to construct a valid osu! Long Note (Type: 128).

    Re-packaging: It writes the new .osu file syntax and packages it back up with the original audio and background files into an .osz archive.
