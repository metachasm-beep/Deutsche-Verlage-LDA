import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import os

def harvest_dnb(publisher_names=None, subject_group="200", max_records=100):
    """
    Harvests bibliographic data from the DNB SRU API, focusing on 'Voices on Religion'.
    """
    base_url = "https://services.dnb.de/sru/dnb"
    records = []
    
    # Namespaces for MARC21 XML
    ns = {
        'zs': 'http://www.loc.gov/zing/srw/',
        'marc': 'http://www.loc.gov/MARC21/slim'
    }

    # Query structure focusing on subject (dcs=200* for Religion)
    # and optional publisher filtering
    base_query = f'dcs={subject_group}*'
    
    # Restrict to last 20 years for "The Computational Turn" context
    current_year = 2026
    year_filter = f' and ddc.year > "{current_year - 20}"'
    
    print(f"Harvesting records for Subject Group {subject_group} (Religion)...")
    
    # We can query all of subject 200 or filter by publishers
    if publisher_names:
        pub_query = " or ".join([f'publisher="{p}"' for p in publisher_names])
        full_query = f'({base_query}) and ({pub_query}){year_filter}'
    else:
        full_query = f'{base_query}{year_filter}'

    params = {
        'operation': 'searchRetrieve',
        'version': '1.1',
        'query': full_query,
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
            title = ""
            author = ""
            date = ""
            publisher = ""
            
            for field in marc_data.findall('marc:datafield', ns):
                tag = field.get('tag')
                if tag == '245':
                    sub = field.find("marc:subfield[@code='a']", ns); title = sub.text if sub is not None else ""
                elif tag == '100':
                    sub = field.find("marc:subfield[@code='a']", ns); author = sub.text if sub is not None else ""
                elif tag == '260' or tag == '264':
                    sub_date = field.find("marc:subfield[@code='c']", ns); date = sub_date.text if sub_date is not None else ""
                    sub_pub = field.find("marc:subfield[@code='b']", ns); publisher = sub_pub.text if sub_pub is not None else ""

            records.append({
                'title': title,
                'author': author,
                'date': date,
                'publisher': publisher,
                'text': f"{title}. {author}."
            })
            
        print(f"✅ Received {len(records)} records for Subject Group {subject_group}.")
        
    except Exception as e:
        print(f"Error harvesting DNB: {e}")

    return pd.DataFrame(records)

if __name__ == "__main__":
    # Expanded list based on PhD objective: Mainstream, Specialized, and Critical
    target_publishers = [
        "Bertelsmann", "Suhrkamp", "Herder", 
        "Gütersloher Verlagshaus", "EVA", "Alibri"
    ]
    df = harvest_dnb(target_publishers)
    
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        
    output_path = 'data/dnb_metadata.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Harvest completed. Saved {len(df)} records to {output_path}")
