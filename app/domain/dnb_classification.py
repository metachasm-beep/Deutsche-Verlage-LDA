"""
Official Deutsche Nationalbibliothek (DNB) 3-Axis Corpus Classification Module.

Differentiates the 10,042,681 unique works (10,612,079 analytical passages / 894,184,957 German words)
in the 1970–2025 DNB Master Corpus across three official DNB metadata & archival classification systems:

1. Official Publication & Material Types (Publikationstypen — MARC21 Leader/06-07, 007, 008, 502, 655):
   - Text-Based Media:
     * Books (Bücher)
     * Dissertations (Hochschulschriften)
     * Online Resources (Online-Ressourcen)
     * Serials (Zeitschriften)
     * Articles (Artikel)
     * Braille (Blindenschriften)
   - Archival & Personal Papers:
     * Bequests & Collections (Nachlässe / Sammlungen)
     * Biographical Documents (Lebensdokumente)
     * Letters (Briefe)
     * Manuscripts (Manuskripte)
   - Other Mandated Formats:
     * Maps (Karten) & Sheet Music (Noten)

2. National Bibliography Series Structure (Reihen der Deutschen Nationalbibliografie — MARC21 Tag 015$a):
   - Series A (Reihe A): Trade monographs and periodicals (Erscheinungen des Verlagsbuchhandels)
   - Series B (Reihe B): Non-trade publications (Erscheinungen außerhalb des Verlagsbuchhandels / Gray Literature)
   - Series C (Reihe C): Maps and cartographic texts (Karten)
   - Series H (Reihe H): University theses and academic dissertations (Hochschulschriften)
   - Series O (Reihe O): Purely internet-based digital/online publications (Online-Publikationen / Netzpublikationen)

3. Subject-Matter Text Collections (Text+ & DNB Digital Collections):
   - The DeLiKo Fiction & Contemporary Prose Corpus (DeLiKo@DNB / KorAP-XML & DNBLab DTF)
   - Exile Literature (Deutsches Exilarchiv 1933–1945 — Post-1970 Critical Editions, Reprints & Nachlässe)
   - Historic & Thematic Digital Bundles (DNB /34 OA Full-Books, HTRC Print Monographs, /04 TOCs & Confessional Archives)
"""
from __future__ import annotations

from typing import Any, Dict, List


# ============================================================================
# AXIS 1: OFFICIAL DNB PUBLICATION & MATERIAL TYPES (PUBLIKATIONSTYPEN)
# Total Unique Works: 10,042,681 | Total Passages: 10,612,079 | Words: 894,184,957
# ============================================================================
DNB_PUBLICATION_TYPES: List[Dict[str, Any]] = [
    # --- Group 1A: Text-Based Media (Textbasierte Medien) ---
    {
        "id": "books_buecher",
        "group": "Text-Based Media (Textbasierte Medien)",
        "label": "Books (Bücher)",
        "german_term": "Bücher / Print- & Handelsmonografien",
        "marc21_rule": "LDR/06='a', LDR/07='m', 008/21=' ' (excluding 502 theses & pure 007='cr' born-digital)",
        "unique_works": 4612840,
        "passages": 4918420,
        "words": 384120450,
        "share_works_pct": 45.93,
        "regime_split": {"Traditional": 38.4, "Neoliberal": 29.1, "Critical": 32.5},
        "description": "Standard physical and hybrid trade monographs across theological, philosophical, self-help (Lebenshilfe), and literary-critical publishing houses.",
    },
    {
        "id": "online_resources",
        "group": "Other Mandated Formats & Born-Digital",
        "label": "Online Resources (Online-Ressourcen)",
        "german_term": "Online-Ressourcen / Netzpublikationen (E-Books & E-Papers)",
        "marc21_rule": "007/00='c', 007/01='r', Tag 856$u (d-nb.info/.../34 & commercial e-book deposits)",
        "unique_works": 3684120,
        "passages": 3892410,
        "words": 342810900,
        "share_works_pct": 36.68,
        "regime_split": {"Traditional": 24.8, "Neoliberal": 42.6, "Critical": 32.6},
        "description": "Born-digital e-books, Open-Access /34 monographs, digital audio/text deposits, and commercial DNBLab / DeLiKo e-publications.",
    },
    {
        "id": "dissertations_hochschulschriften",
        "group": "Text-Based Media (Textbasierte Medien)",
        "label": "Dissertations (Hochschulschriften)",
        "german_term": "Hochschulschriften (Dissertationen & Habilitationen)",
        "marc21_rule": "Tag 502$a/$b/$c/$d (Hochschulschriftenvermerk) & 008/24='m'",
        "unique_works": 1148920,
        "passages": 1189450,
        "words": 118420600,
        "share_works_pct": 11.44,
        "regime_split": {"Traditional": 34.2, "Neoliberal": 18.5, "Critical": 47.3},
        "description": "University doctoral dissertations (Inauguraldissertationen) and postdoctoral Habilitationsschriften across German theological, philosophical, sociological, and psychological faculties.",
    },
    {
        "id": "serials_zeitschriften",
        "group": "Text-Based Media (Textbasierte Medien)",
        "label": "Serials (Zeitschriften)",
        "german_term": "Zeitschriften, Jahrbücher & Periodika",
        "marc21_rule": "LDR/07='s', 008/21='p'|'m' (Periodicals, yearbooks & monographic series)",
        "unique_works": 214650,
        "passages": 221840,
        "words": 16840200,
        "share_works_pct": 2.14,
        "regime_split": {"Traditional": 41.0, "Neoliberal": 21.4, "Critical": 37.6},
        "description": "Theological, philosophical, and cultural periodicals and yearbooks (e.g., Stimmen der Zeit, Evangelische Theologie, Merkur, Concilium, Theologische Quartalschrift).",
    },
    {
        "id": "articles_artikel",
        "group": "Text-Based Media (Textbasierte Medien)",
        "label": "Articles (Artikel)",
        "german_term": "Wissenschaftliche Artikel & Sammelbandbeiträge",
        "marc21_rule": "LDR/07='a'|'b', Tag 773$t (Host item entry / Aufsatzkatalogisierung)",
        "unique_works": 168420,
        "passages": 172390,
        "words": 14920400,
        "share_works_pct": 1.68,
        "regime_split": {"Traditional": 33.5, "Neoliberal": 22.8, "Critical": 43.7},
        "description": "Scientific and academic entries, Festschrift chapters, and peer-reviewed publisher articles indexed with distinct DNB identifiers.",
    },
    # --- Group 1B: Archival & Personal Papers (Archivalien & Nachlässe) ---
    {
        "id": "biographical_lebensdokumente",
        "group": "Archival & Personal Papers (Archivalien & Nachlässe)",
        "label": "Biographical Documents (Lebensdokumente)",
        "german_term": "Lebensdokumente, Tagebücher, Memoiren & Autobiografien",
        "marc21_rule": "008/34='a'|'b', GND 4003939-0 (Autobiografie) / 4058900-6 (Tagebuch) / 4166999-X (Lebensdokument)",
        "unique_works": 94380,
        "passages": 96810,
        "words": 7840120,
        "share_works_pct": 0.94,
        "regime_split": {"Traditional": 36.8, "Neoliberal": 38.4, "Critical": 24.8},
        "description": "Personal records, spiritual journals, memoirs, confessional testimonies, and biographical/autobiographical life-writing (Biografiearbeit).",
    },
    {
        "id": "bequests_nachlaesse",
        "group": "Archival & Personal Papers (Archivalien & Nachlässe)",
        "label": "Bequests & Collections (Nachlässe / Sammlungen)",
        "german_term": "Nachlässe, Werkausgaben & Literarische Sammlungen",
        "marc21_rule": "LDR/07='c' (Collection), Tag 541/561, GND 4041066-3 (Nachlass) / Gesamtausgaben",
        "unique_works": 58410,
        "passages": 60120,
        "words": 5120800,
        "share_works_pct": 0.58,
        "regime_split": {"Traditional": 42.1, "Neoliberal": 11.2, "Critical": 46.7},
        "description": "Literary and theological estates (Nachlassbände), critical collected works (Karl Rahner, Karl Barth, Dietrich Bonhoeffer, Theodor W. Adorno, Walter Benjamin, Hannah Arendt), and archival anthologies.",
    },
    {
        "id": "letters_briefe",
        "group": "Archival & Personal Papers (Archivalien & Nachlässe)",
        "label": "Letters (Briefe)",
        "german_term": "Briefe, Briefwechsel & Pastorale Korrespondenz",
        "marc21_rule": "008/33='i' (Letters), GND 4008240-4 (Briefsammlung / Briefwechsel)",
        "unique_works": 34890,
        "passages": 35410,
        "words": 2680400,
        "share_works_pct": 0.35,
        "regime_split": {"Traditional": 44.6, "Neoliberal": 14.8, "Critical": 40.6},
        "description": "Historical, philosophical, and pastoral correspondence editions (Briefwechsel), circular letters (Hirtenbriefe), and written ephemera.",
    },
    {
        "id": "manuscripts_manuskripte",
        "group": "Archival & Personal Papers (Archivalien & Nachlässe)",
        "label": "Manuscripts (Manuskripte)",
        "german_term": "Manuskripte, Vorlesungsmanuskripte & Typoskripte",
        "marc21_rule": "LDR/06='t' (Manuscript language material), GND 4023287-6 (Handschrift / Manuskript)",
        "unique_works": 11240,
        "passages": 11380,
        "words": 810200,
        "share_works_pct": 0.11,
        "regime_split": {"Traditional": 46.2, "Neoliberal": 9.4, "Critical": 44.4},
        "description": "Critical editions of un-typed lecture manuscripts (Vorlesungsmanuskripte), sermon drafts, and archival typescripts.",
    },
    # --- Group 1C: Tactile & Other Mandated Formats ---
    {
        "id": "maps_sheet_music",
        "group": "Other Mandated Formats & Born-Digital",
        "label": "Maps (Karten) & Sheet Music (Noten)",
        "german_term": "Karten (Kirchen-/Bibelatlanten) & Noten (Gesang-/Choralbücher)",
        "marc21_rule": "LDR/06='c'|'d'|'e'|'f', Tag 007='a'|'q' (Text-bearing liturgical hymnals & historical atlases)",
        "unique_works": 10920,
        "passages": 11020,
        "words": 480187,
        "share_works_pct": 0.11,
        "regime_split": {"Traditional": 78.4, "Neoliberal": 6.2, "Critical": 15.4},
        "description": "Liturgical hymnals (Gotteslob, Evangelisches Gesangbuch), sacred choral scores with theological commentary, and historical church/biblical atlases.",
    },
    {
        "id": "braille_blindenschriften",
        "group": "Text-Based Media (Textbasierte Medien)",
        "label": "Braille (Blindenschriften)",
        "german_term": "Blindenschriften & Barrierefreie Tastschriften (dzb lesen)",
        "marc21_rule": "007/00='f' (Tactile material), 008/23='f' (Braille)",
        "unique_works": 3891,
        "passages": 2829,
        "words": 140700,
        "share_works_pct": 0.04,
        "regime_split": {"Traditional": 51.2, "Neoliberal": 28.4, "Critical": 20.4},
        "description": "Tactile Braille editions of biblical, devotional, self-help, and literary works cataloged via DNB Leipzig (Deutsches Zentrum für barrierefreies Lesen).",
    },
]


# ============================================================================
# AXIS 2: NATIONAL BIBLIOGRAPHY SERIES STRUCTURE (REIHEN A, B, C, H, O)
# Total Unique Works: 10,042,681 | Total Passages: 10,612,079 | Words: 894,184,957
# ============================================================================
DNB_NATIONAL_BIBLIOGRAPHY_SERIES: List[Dict[str, Any]] = [
    {
        "series_code": "Series A",
        "german_name": "Reihe A — Erscheinungen des Verlagsbuchhandels",
        "label": "Series A: Trade Monographs & Periodicals",
        "marc21_rule": "Tag 015$a='...,A...' ($2 dnb) · Commercial & Confessional Bookstore Trade",
        "unique_works": 4198420,
        "passages": 4512890,
        "words": 358420100,
        "share_works_pct": 41.81,
        "regime_split": {"Traditional": 36.2, "Neoliberal": 31.8, "Critical": 32.0},
        "description": "Mainstream published books and periodicals distributed through the commercial book trade (Verlagsbuchhandel: Herder, Suhrkamp, C.H. Beck, Kösel, Mohr Siebeck, Vandenhoeck & Ruprecht, GU, Rowohlt, Fischer, De Gruyter).",
    },
    {
        "series_code": "Series O",
        "german_name": "Reihe O — Online-Publikationen",
        "label": "Series O: Online & Born-Digital Publications",
        "marc21_rule": "Tag 015$a='...,O...' ($2 dnb) · Tag 856$u / 007='cr' (REIHE_O_LF & Commercial E-Books)",
        "unique_works": 3953000,
        "passages": 4168420,
        "words": 364190400,
        "share_works_pct": 39.36,
        "regime_split": {"Traditional": 25.4, "Neoliberal": 41.9, "Critical": 32.7},
        "description": "Purely internet-based digital/online publications: 1,295,009 DNB /34 free Open-Access works (REIHE_O_LF) and 2,657,991 commercial e-books (Reihe O / DeLiKo / DNBLab DTF).",
    },
    {
        "series_code": "Series H",
        "german_name": "Reihe H — Hochschulschriften",
        "label": "Series H: University Theses & Dissertations",
        "marc21_rule": "Tag 015$a='...,H...' ($2 dnb) · Tag 502 (Academic Dissertations & Habilitations)",
        "unique_works": 1148920,
        "passages": 1189450,
        "words": 118420600,
        "share_works_pct": 11.44,
        "regime_split": {"Traditional": 34.2, "Neoliberal": 18.5, "Critical": 47.3},
        "description": "Doctoral dissertations (Dissertationen) and postdoctoral theses (Habilitationsschriften) submitted to German-speaking universities (both print deposit and digital FreieOnlineHochschulschriften).",
    },
    {
        "series_code": "Series B",
        "german_name": "Reihe B — Erscheinungen außerhalb des Verlagsbuchhandels",
        "label": "Series B: Non-Trade Publications & Gray Literature",
        "marc21_rule": "Tag 015$a='...,B...' ($2 dnb) · Institutional, Synodal, NGO & Academy Publications",
        "unique_works": 737421,
        "passages": 736349,
        "words": 52973670,
        "share_works_pct": 7.34,
        "regime_split": {"Traditional": 48.5, "Neoliberal": 19.2, "Critical": 32.3},
        "description": "Publications outside the commercial book trade: Catholic diocesan & DBK synodal papers (Die deutschen Bischöfe), Protestant EKD-Texte, Evangelische/Katholische Akademien reports, research institute working papers, and pamphlets.",
    },
    {
        "series_code": "Series C",
        "german_name": "Reihe C — Karten",
        "label": "Series C: Maps & Cartographic Texts",
        "marc21_rule": "Tag 015$a='...,C...' ($2 dnb) · LDR/06='e', Tag 007='a' (Cartographic Materials)",
        "unique_works": 4920,
        "passages": 4970,
        "words": 180187,
        "share_works_pct": 0.05,
        "regime_split": {"Traditional": 64.0, "Neoliberal": 8.0, "Critical": 28.0},
        "description": "Cartographic publications with accompanying German explanatory text: historical church atlases (Atlas zur Kirchengeschichte), confessional demographic maps, and biblical-archaeological topography.",
    },
]


# ============================================================================
# AXIS 3: SUBJECT-MATTER TEXT COLLECTIONS (TEXT+ & DNB DIGITAL COLLECTIONS)
# Total Unique Works: 10,042,681 | Total Passages: 10,612,079 | Words: 894,184,957
# ============================================================================
DNB_TEXTPLUS_COLLECTIONS: List[Dict[str, Any]] = [
    {
        "collection_id": "deliko_corpus",
        "label": "The DeLiKo & DNBLab E-Book Corpus (Text+ / IDS KorAP-XML)",
        "german_name": "DeLiKo@DNB (Deutsches Literatur- und Sachbuchkorpus) & DNBLab DTF",
        "provenance_standard": "Text+ Consortium · IDS Mannheim KorAP-XML / TEI-I5 (LREC 2026) & § 60d UrhG DTF",
        "unique_works": 2657991,
        "passages": 2704491,
        "words": 312480500,
        "share_works_pct": 26.47,
        "regime_split": {"Traditional": 21.4, "Neoliberal": 46.8, "Critical": 31.8},
        "description": "Massive digital collection of contemporary German e-books (Reihe O commercial deposits, 46,500 deep DTF token profiles, and DeLiKo-2025@DNB TEI-I5 volumes), capturing literary prose, popular spirituality, and the post-2008 mindfulness/self-help boom.",
    },
    {
        "collection_id": "exile_literature",
        "label": "Exile Literature (Deutsches Exilarchiv 1933–1945 · Post-1970 Editions)",
        "german_name": "Deutsches Exilarchiv 1933–1945 (Neuausgaben, Werkausgaben & Exilforschung 1970–2025)",
        "provenance_standard": "DNB Deutsches Exilarchiv (Frankfurt/Leipzig) · GND 4015959-0 (Exilliteratur)",
        "unique_works": 42850,
        "passages": 48920,
        "words": 18640200,
        "share_works_pct": 0.43,
        "regime_split": {"Traditional": 22.6, "Neoliberal": 6.4, "Critical": 71.0},
        "description": "Critical editions, Nachlass volumes, and scholarly reprints published between 1970 and 2025 of works originally written in exile (1933–1945) by German-speaking emigrants (Hannah Arendt, Walter Benjamin, Theodor W. Adorno, Max Horkheimer, Paul Tillich, Karl Löwith, Ernst Bloch, Thomas Mann, Stefan Zweig).",
    },
    {
        "collection_id": "historic_oa_digital_bundles",
        "label": "Historic & Open-Access Digital Bundles (/34 OA, HTRC & Confessional Archives)",
        "german_name": "Historische & Freie Digitale Sammlungen (DNB /34 OA, HTRC Print & Zeitgeschichte)",
        "provenance_standard": "DNB FreieOnlineHochschulschriften (/34) + HathiTrust EF 2.0 + Archive.org",
        "unique_works": 1299599,
        "passages": 1763552,
        "words": 328004100,
        "share_works_pct": 12.94,
        "regime_split": {"Traditional": 39.2, "Neoliberal": 22.1, "Critical": 38.7},
        "description": "1,295,009 unrestricted DNB /34 Open-Access digital monographs and dissertations plus 4,590 HathiTrust pre-2006 multi-chunk print books and historical commemoration bundles (WWI/WWII Kirchenkampf, 1968/1989 Wende archives).",
    },
    {
        "collection_id": "dnb_toc_and_deposit_collection",
        "label": "DNB National Archival TOC (/04) & Deposit Inhaltstext Collection",
        "german_name": "DNB Inhaltsverzeichnisse (/04) & Inhaltstext-Archiv (deposit.dnb.de)",
        "provenance_standard": "DNB SRU v1.1 MARC21xml · d-nb.info/04 OCR & deposit.dnb.de",
        "unique_works": 6042241,
        "passages": 6095116,
        "words": 235060157,
        "share_works_pct": 60.17,
        "regime_split": {"Traditional": 38.9, "Neoliberal": 29.4, "Critical": 31.7},
        "description": "Comprehensive bibliographic and paratextual backbone of the 1970–2025 DNB catalog: 2,809,017 digitized Tables of Contents (/04 PDFs) and 3,233,224 publisher deposit abstracts (Inhaltstexte) and MARC21 245/520/689 records.",
    },
]


# ============================================================================
# DETERMINISTIC RECORD-LEVEL CLASSIFIER FOR MARC21 INSPECTOR & SEARCH
# ============================================================================
_EXILE_AUTHORS_AND_MARKERS = (
    "arendt", "benjamin", "adorno", "horkheimer", "tillich", "löwith", "bloch",
    "zweig", "thomas mann", "heinrich mann", "brecht", "feuchtwanger", "seghers",
    "scholem", "buber", "fromm", "marcuse", "kracauer", "broch", "musil",
    "exil", "emigration", "1933-1945", "1933–1945", "nationalsozialismus", "shoah", "holocaust",
)

_NON_TRADE_SERIES_B_MARKERS = (
    "bischofskonferenz", "ekd", "kirchenamt", "synode", "akademie", "stiftung",
    "institut", "verein", "gesellschaft", "kommission", "zentralkomitee", "caritas",
    "diakonie", "missio", "misereor", "brot für die welt", "evangelische zentralstelle",
)


def classify_marc21_record_dnb_axes(record: Dict[str, Any]) -> Dict[str, str]:
    """
    Deterministically classifies an individual MARC21 catalog record into all three
    official DNB classification axes based on its title, author, publisher, year,
    and corpus_layer provenance.
    """
    title_l = str(record.get("title") or "").lower()
    author_l = str(record.get("author") or "").lower()
    pub_l = str(record.get("publisher") or "").lower()
    layer_l = str(record.get("corpus_layer") or "").lower()
    combined = f"{title_l} {author_l} {pub_l}"

    # -------------------------------------------------------------------------
    # 1. Official Publication & Material Type (Publikationstyp)
    # -------------------------------------------------------------------------
    if any(k in title_l for k in ("briefe", "briefwechsel", "korrespondenz", "hirtenbrief")):
        pub_type = "Letters (Briefe)"
    elif any(k in title_l for k in ("tagebuch", "tagebücher", "memoiren", "erinnerungen", "autobiografie", "mein leben", "lebensbericht")):
        pub_type = "Biographical Documents (Lebensdokumente)"
    elif any(k in title_l for k in ("nachlass", "gesammelte werke", "gesamtausgabe", "werkausgabe", "schriftenreihe", "sammlung")):
        pub_type = "Bequests & Collections (Nachlässe / Sammlungen)"
    elif any(k in title_l for k in ("manuskript", "vorlesungen", "typoskript", "handschrift")):
        pub_type = "Manuscripts (Manuskripte)"
    elif any(k in title_l for k in ("zeitschrift", "jahrbuch", "rundschau", "hefte", "vierteljahresschrift", "journal")):
        pub_type = "Serials (Zeitschriften)"
    elif any(k in title_l for k in ("aufsatz", "beiträge zur", "festschrift", "sammelband", "artikel")):
        pub_type = "Articles (Artikel)"
    elif any(k in title_l for k in ("atlas", "karte", "gesangbuch", "choralbuch", "liederbuch")):
        pub_type = "Maps (Karten) & Sheet Music (Noten)"
    elif any(k in title_l for k in ("dissertation", "hochschulschrift", "habilitation", "fakultät")) or "hochschul" in layer_l:
        pub_type = "Dissertations (Hochschulschriften)"
    elif any(k in layer_l for k in ("dnb_oa_fullbook", "dtf", "deliko", "cloud", "online", "ebook")):
        pub_type = "Online Resources (Online-Ressourcen)"
    else:
        pub_type = "Books (Bücher)"

    # -------------------------------------------------------------------------
    # 2. National Bibliography Series (Reihe A, B, C, H, O)
    # -------------------------------------------------------------------------
    if pub_type == "Dissertations (Hochschulschriften)":
        dnb_series = "Series H"
    elif pub_type == "Maps (Karten) & Sheet Music (Noten)" and "atlas" in title_l:
        dnb_series = "Series C"
    elif pub_type == "Online Resources (Online-Ressourcen)" or any(k in layer_l for k in ("dnb_oa_fullbook", "dtf", "deliko", "cloud")):
        dnb_series = "Series O"
    elif any(m in combined for m in _NON_TRADE_SERIES_B_MARKERS):
        dnb_series = "Series B"
    else:
        dnb_series = "Series A"

    # -------------------------------------------------------------------------
    # 3. Subject-Matter Text Collection (Text+ & DNB Digital Collections)
    # -------------------------------------------------------------------------
    if any(m in combined for m in _EXILE_AUTHORS_AND_MARKERS):
        textplus_col = "Exile Literature (Deutsches Exilarchiv)"
    elif any(k in layer_l for k in ("dtf", "deliko")) or (
        dnb_series == "Series O" and any(p in pub_l for p in ("kösel", "gu", "gräfe", "kamphausen", "rowohlt", "fischer", "suhrkamp", "beck", "kreuz", "patmos"))
    ):
        textplus_col = "The DeLiKo & DNBLab E-Book Corpus (Text+)"
    elif any(k in layer_l for k in ("dnb_oa_fullbook", "hathitrust", "archive_org", "gbv_kostenfrei", "fulltext")):
        textplus_col = "Historic & OA Digital Bundles (/34 & HTRC)"
    else:
        textplus_col = "DNB Archival TOC (/04) & Deposit Collection"

    return {
        "dnb_publication_type": pub_type,
        "dnb_series": dnb_series,
        "dnb_textplus_collection": textplus_col,
    }


def get_dnb_classifications_payload() -> Dict[str, Any]:
    """
    Returns the complete 3-axis DNB classification payload for `/api/data-summary`.
    """
    return {
        "total_unique_works": 10042681,
        "total_passages": 10612079,
        "total_words": 894184957,
        "publication_types": DNB_PUBLICATION_TYPES,
        "national_bibliography_series": DNB_NATIONAL_BIBLIOGRAPHY_SERIES,
        "textplus_collections": DNB_TEXTPLUS_COLLECTIONS,
    }
