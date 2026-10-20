import os
import re
import time
import unicodedata
import urllib3
import requests
import xml.etree.ElementTree as ET
import pandas as pd

# Suppress InsecureRequestWarning when falling back on Windows SSL cert stores
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Namespaces for DNB SRU & MARC21 XML
NS = {
    'zs': 'http://www.loc.gov/zing/srw/',
    'marc': 'http://www.loc.gov/MARC21/slim'
}


def normalize_german_text(text: str) -> str:
    """
    Normalizes MARC21 NFD combining diacritics (e.g., 'a' + '\\u0308') into
    canonical NFC German characters ('ä', 'ö', 'ü', 'ß') and cleans whitespace.
    """
    if not text:
        return ""
    normalized = unicodedata.normalize('NFC', str(text))
    return re.sub(r'\s+', ' ', normalized).strip()


def fetch_url_with_ssl_fallback(url: str, params: dict = None, timeout: int = 15):
    """
    Executes a GET request with standard SSL verification first, falling back to
    verify=False if the local Windows certificate store lacks the DNB issuer CA.
    """
    try:
        return requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.SSLError:
        return requests.get(url, params=params, timeout=timeout, verify=False)


def fetch_dnb_blurb(blurb_url: str) -> str:
    """
    Fetches and strips HTML from a DNB Inhaltstext (Tag 856) publisher blurb URL.
    """
    if not blurb_url:
        return ""
    try:
        resp = fetch_url_with_ssl_fallback(blurb_url, timeout=8)
        if resp.status_code == 200:
            # Strip HTML tags and decode entities
            raw_html = resp.text
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', raw_html, flags=re.DOTALL | re.IGNORECASE)
            content = " ".join(p_matches) if p_matches else raw_html
            clean = re.sub(r'<[^>]+>', ' ', content)
            clean = clean.replace('&#xa0;', ' ').replace('&nbsp;', ' ').replace('&quot;', '"')
            return normalize_german_text(clean)
    except Exception:
        pass
    return ""


def parse_marc_record(marc_data, canonical_publisher: str = None, fetch_blurbs: bool = True) -> dict:
    """
    Extracts rich bibliographic and discursive fields from a MARC21 XML record:
    - Tag 245 ($a, $b): Main title and subtitle
    - Tag 100 / 700 ($a): Primary author or editor
    - Tag 260 / 264 ($b, $c): Publisher imprint and publication year
    - Tag 520 ($a): Embedded abstract / summary note
    - Tag 650 / 653 / 689 ($a): Controlled GND Schlagwörter & subject keywords
    - Tag 856 ($u where $3='Inhaltstext'): Full publisher blurb text
    """
    title_main = ""
    subtitle = ""
    author = ""
    editor = ""
    date = ""
    publisher = ""
    abstracts = []
    keywords = []
    blurb_url = ""

    for field in marc_data.findall('marc:datafield', NS):
        tag = field.get('tag')

        if tag == '245':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_a is not None and sub_a.text:
                title_main = normalize_german_text(sub_a.text)
            if sub_b is not None and sub_b.text:
                subtitle = normalize_german_text(sub_b.text)

        elif tag == '100':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                author = normalize_german_text(sub_a.text)

        elif tag == '700' and not editor:
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                editor = normalize_german_text(sub_a.text)

        elif tag in ('260', '264'):
            sub_c = field.find("marc:subfield[@code='c']", NS)
            sub_b = field.find("marc:subfield[@code='b']", NS)
            if sub_c is not None and sub_c.text and not date:
                year_match = re.search(r'(\d{4})', sub_c.text)
                date = year_match.group(1) if year_match else normalize_german_text(sub_c.text)
            if sub_b is not None and sub_b.text and not publisher:
                publisher = normalize_german_text(sub_b.text)

        elif tag == '520':
            sub_a = field.find("marc:subfield[@code='a']", NS)
            if sub_a is not None and sub_a.text:
                abstracts.append(normalize_german_text(sub_a.text))

        elif tag in ('650', '653', '689'):
            for sub_a in field.findall("marc:subfield[@code='a']", NS):
                if sub_a.text:
                    kw = normalize_german_text(sub_a.text)
                    # Filter out technical product-form tags in 653
                    if kw.startswith("(Produktform)") or kw.startswith("(ISIL)"):
                        continue
                    if kw.startswith("(VLB-WN)"):
                        # Keep only the descriptive subject path after the colon
                        parts = kw.split(":", 1)
                        if len(parts) > 1:
                            kw = parts[1].replace("Hardcover, Softcover /", "").strip()
                    if kw and kw not in keywords:
                        keywords.append(kw)

        elif tag == '856':
            sub_3 = field.find("marc:subfield[@code='3']", NS)
            sub_u = field.find("marc:subfield[@code='u']", NS)
            if sub_3 is not None and sub_u is not None and sub_3.text and sub_u.text:
                if "inhaltstext" in sub_3.text.lower() and not blurb_url:
                    blurb_url = sub_u.text.strip()

    full_title = f"{title_main}: {subtitle}" if subtitle else title_main
    creator = author if author else editor
    final_publisher = canonical_publisher if canonical_publisher else (publisher or "Unknown")

    blurb_text = fetch_dnb_blurb(blurb_url) if (fetch_blurbs and blurb_url) else ""
    abstract_str = " ".join(abstracts)
    keyword_str = ", ".join(keywords)

    # Synthesize dense discursive text for LDA modeling
    text_segments = [s for s in [full_title, abstract_str, blurb_text, keyword_str] if s]
    combined_text = ". ".join(text_segments)

    return {
        'title': full_title,
        'author': creator,
        'date': date,
        'publisher': final_publisher,
        'raw_imprint': publisher,
        'keywords': keyword_str,
        'abstract': blurb_text or abstract_str,
        'text': combined_text
    }


def harvest_dnb(
    publisher_names=None,
    start_year: int = 2005,
    max_records_per_publisher: int = 25,
    fetch_blurbs: bool = True
) -> pd.DataFrame:
    """
    Harvests bibliographic & discursive data from the DNB SRU API v1.1, focusing on
    DDC Subject Group 200/230 (Religion & Theology) across target German publishers.
    """
    base_url = "https://services.dnb.de/sru/dnb"
    records = []

    # Valid DNB SRU CQL query for Religion & Theology (DDC 200 / 230 / Hauptsachgruppe)
    subject_cql = "(dcs=200* or dcs=230* or hsg=200 or hsg=230)"
    year_cql = f"jhr>={start_year}"

    if not publisher_names:
        publisher_names = [
            "Herder",
            "Evangelische Verlagsanstalt",
            "Gütersloher Verlagshaus",
            "Suhrkamp",
            "Alibri",
            "Rowohlt",
            "Patmos",
            "Kösel"
        ]

    print(f"Harvesting DNB SRU records for DDC 200/230 (Religion) since {start_year}...")

    for pub in publisher_names:
        cql_query = f'{subject_cql} and vlg="{pub}" and {year_cql}'
        params = {
            'operation': 'searchRetrieve',
            'version': '1.1',
            'query': cql_query,
            'recordSchema': 'MARC21-xml',
            'maximumRecords': max_records_per_publisher
        }

        try:
            response = fetch_url_with_ssl_fallback(base_url, params=params)
            response.raise_for_status()

            tree = ET.fromstring(response.content)
            total_hits_el = tree.find('.//zs:numberOfRecords', NS)
            total_hits = int(total_hits_el.text) if (total_hits_el is not None and total_hits_el.text) else 0
            srw_records = tree.findall('.//zs:record', NS)

            pub_count = 0
            for srw_rec in srw_records:
                marc_data = srw_rec.find('.//marc:record', NS)
                if marc_data is None:
                    continue
                parsed = parse_marc_record(marc_data, canonical_publisher=pub, fetch_blurbs=fetch_blurbs)
                if parsed['title'] and parsed['date']:
                    records.append(parsed)
                    pub_count += 1

            print(f"  - [{pub}]: Retrieved {pub_count} rich records (out of {total_hits} total DNB matches)")
            time.sleep(0.4)

        except Exception as e:
            print(f"  ! Error harvesting [{pub}]: {e}")

    print(f"Total harvested records: {len(records)}")
    return pd.DataFrame(records)


if __name__ == "__main__":
    # Stratified publisher list across Traditional, Neoliberal/Self-Help, and Critical archetypes
    target_publishers = [
        "Herder",
        "Evangelische Verlagsanstalt",
        "Gütersloher Verlagshaus",
        "Kösel",
        "Suhrkamp",
        "Alibri",
        "Rowohlt",
        "Patmos"
    ]
    df = harvest_dnb(target_publishers, start_year=2005, max_records_per_publisher=20, fetch_blurbs=True)

    os.makedirs('data', exist_ok=True)
    output_path = 'data/dnb_metadata.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Saved {len(df)} enriched DNB records to {output_path}")
