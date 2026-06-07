# run_tubi.py

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import logging

# Import your scraper class
from tubi_scraper import TubiScraper

# Setup basic logging to see the script progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def generate_m3u(scraper, channels, filename="tubi_playlist.m3u"):
    """Generates an M3U8 playlist file with real https:// stream URLs."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            # Look up the actual live CDN HLS URL from the scraper's cache
            real_url = scraper._url_cache.get(ch.source_channel_id)
            
            # If it's missing from the cache, use resolve() to fetch it live
            if not real_url:
                real_url = scraper.resolve(ch.stream_url)
                
            # Skip the channel if we still don't have a valid https link
            if not real_url or not real_url.startswith("https://"):
                logging.warning(f"[tubi] Skipping {ch.name} - No valid HTTPS URL found")
                continue

            # Build standard IPTV metadata tags
            tvg_id = f' tvg-id="{ch.source_channel_id}"'
            tvg_logo = f' tvg-logo="{ch.logo_url}"' if ch.logo_url else ""
            group_title = f' group-title="{ch.category}"' if ch.category else ""
            
            # Format: #EXTINF:-1 tvg-id="..." tvg-logo="..." group-title="...", Channel Name
            f.write(f'#EXTINF:-1{tvg_id}{tvg_logo}{group_title},{ch.name}\n')
            f.write(f'{real_url}\n')
            
    print(f"[Success] M3U Playlist saved to: {filename}")

def generate_xmltv(channels, programs, filename="tubi_epg.xml"):
    """Generates an XMLTV standard EPG file from the scraped channels and programs."""
    root = ET.Element("tv")
    root.set("generator-info-name", "Tubi FastChannels Scraper")

    # 1. Add <channel> definitions
    for ch in channels:
        channel_elem = ET.SubElement(root, "channel", id=ch.source_channel_id)
        
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.text = ch.name
        
        if ch.logo_url:
            ET.SubElement(channel_elem, "icon", src=ch.logo_url)

    # 2. Add <programme> schedules
    for p in programs:
        # Format datetimes to XMLTV compliance (YYYYMMDDhhmmss +0000)
        start_str = p.start_time.strftime("%Y%m%dd%H%M%S +0000").replace('d', '')
        end_str = p.end_time.strftime("%Y%m%dd%H%M%S +0000").replace('d', '')
        
        prog_elem = ET.SubElement(
            root, "programme", 
            start=start_str, 
            stop=end_str, 
            channel=p.source_channel_id
        )

        title_elem = ET.SubElement(prog_elem, "title")
        title_elem.text = p.title

        if p.episode_title:
            ep_title_elem = ET.SubElement(prog_elem, "sub-title")
            ep_title_elem.text = p.episode_title

        if p.description:
            desc_elem = ET.SubElement(prog_elem, "desc")
            desc_elem.text = p.description

        if p.poster_url:
            ET.SubElement(prog_elem, "icon", src=p.poster_url)

        if p.rating:
            rating_elem = ET.SubElement(prog_elem, "rating", system="MPAA")
            value_elem = ET.SubElement(rating_elem, "value")
            value_elem.text = p.rating

        # XMLTV standard episode numbering (xmltv_ns format)
        if p.season is not None or p.episode is not None:
            s = int(p.season) - 1 if p.season else 0
            e = int(p.episode) - 1 if p.episode else 0
            episode_num = ET.SubElement(prog_elem, "episode-num", system="xmltv_ns")
            episode_num.text = f"{s}.{e}."

    # Write prettified XML to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"[Success] XMLTV EPG saved to: {filename}")

if __name__ == "__main__":
    # If using authentication, fill these out. Otherwise, leave empty strings for anonymous access.
    config_mock = {"username": "", "password": ""} 
    scraper = TubiScraper(config=config_mock)

    print("Step 1: Fetching Tubi Channels...")
    channels = scraper.fetch_channels()

    if not channels:
        print("[Error] No channels scraped. Exiting.")
    else:
        print(f"Step 2: Scraped {len(channels)} channels. Generating M3U...")
        # We pass the scraper instance here to read its internal url cache
        generate_m3u(scraper, channels)

        print("Step 3: Fetching EPG data for channels...")
        programs = scraper.fetch_epg(channels)

        print(f"Step 4: Scraped {len(programs)} program events. Generating XMLTV...")
        generate_xmltv(channels, programs)
