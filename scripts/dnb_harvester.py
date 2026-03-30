import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import os

def harvest_dnb(publisher_names, max_records=50):
    """
    Harvests bibliographic data from the German National Library (DNB) SRU API.
    """
    base_url = "https://services.dnb.de/sru/dnb"
    records = []
    
    # Namespaces for MARC21 XML
    ns = {
        'zs': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim'
    }

    for publisher in publisher_names:
        print(f"Harvesting records for: {publisher}...")
        params = {
            'operation': 'searchRetrieve',
            'version': '1.1',
            'query': f'publisher="{publisher}"',
            'recordSchema': 'MARC21-xml',
            'maximumRecords': max_records
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            tree = ET.fromstring(response.content)
            srw_records = tree.findall('.//zs:record', ns)
            
            for srw_rec in srw_records:
                marc_data = srw_rec.find('.//marc:record', ns)
                if marc_data is None: continue
                
                # Extract fields
                # 245 $a: Title
                # 100 $a: Author
                # 260 $c: Date / $b: Publisher
                title = ""
                author = ""
                date = ""
                
                for field in marc_data.findall('marc:datafield', ns):
                    tag = field.get('tag')
                    # Title
                    if tag == '245':
                        sub = field.find("marc:subfield[@code='a']", ns)
                        if sub is not None: title = sub.text
                    # Author
                    elif tag == '100':
                        sub = field.find("marc:subfield[@code='a']", ns)
                        if sub is not None: author = sub.text
                    # Date/Publisher
                    elif tag == '260' or tag == '264':
                        sub_date = field.find("marc:subfield[@code='c']", ns)
                        if sub_date is not None: date = sub_date.text

                records.append({
                    'title': title,
                    'author': author,
                    'date': date,
                    'publisher': publisher,
                    'text': f"{title}. {author}." # Simple text for LDA
                })
            
            # Simple rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"Error harvesting {publisher}: {e}")

    return pd.DataFrame(records)

if __name__ == "__main__":
    publishers = ["Bertelsmann", "Suhrkamp"]
    df = harvest_dnb(publishers)
    
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        
    output_path = 'data/dnb_metadata.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Harvest completed. Saved {len(df)} records to {output_path}")
