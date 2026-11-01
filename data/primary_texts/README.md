# Layer 1: Primary Full-Text Corpus Directory (`data/primary_texts/`)

Place full-length German books, chapters, pamphlets, or articles (`.pdf`, `.epub`, `.docx`, `.txt`) in this folder.

## Recommended Filename Convention
`Year_Publisher_Author_Title.ext`
- Example 1: `1978_Suhrkamp_Tilmann Moser_Gottesvergiftung.pdf`
- Example 2: `2005_Alibri_Michael Schmidt-Salomon_Manifest des evolutionären Humanismus.epub`
- Example 3: `2012_Gütersloher Verlagshaus_Achtsamkeit und Selbstoptimierung.txt`

Then run:
```powershell
python scripts/fulltext_ingester.py --chunk-words 1000 --merge-dnb
```
