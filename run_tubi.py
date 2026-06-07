import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import logging

# Import your scraper class
from tubi_scraper import TubiScraper

# Setup basic logging to see the script progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def generate_m3u(channels, filename="tubi_playlist.m3u"):
    """Generates an M3U8 playlist file from the scraped channels."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            # Build metadata tags (tvg-id, logo, group/category)
            tvg_id = f' tvg-id="{ch.source_channel_id}"'
            tvg_logo = f' tvg-logo="{ch.logo_url}"' if ch.logo_url else ""
            group_title = f' group-title="{ch.category}"' if ch.category else ""
            
            # Format: #EXTINF:-1 tvg-id="..." tvg-logo="..." group-title="...", Channel Name
            f.write(f'#EXTINF:-1{tvg_id}{tvg_logo}{group_title},{ch.name}\n')
            
            # Use the actual cached stream URL if available, otherwise fall back to the internal URI
            f.write(f'{ch.stream_url}\n')
            
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
            logo_elem = ET.SubElement(channel_elem, "icon", src=ch.logo_url)

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
            icon_elem = ET.SubElement(prog_elem, "icon", src=p.poster_url)

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
    ET.indent(tree, space="  ", level=0)  # Make XML human-readable
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"[Success] XMLTV EPG saved to: {filename}")

if __name__ == "__main__":
    # Initialize the scraper (Pass username/password dict here if you want authenticated mode)
    config_mock = {"username": "", "password": ""} 
    scraper = TubiScraper(config=config_mock)

    print("Step 1: Fetching Tubi Channels...")
    channels = scraper.fetch_channels()

    if not channels:
        print("[Error] No channels scraped. Exiting.")
    else:
        print(f"Step 2: Scraped {len(channels)} channels. Generating M3U...")
        generate_m3u(channels)

        print("Step 3: Fetching EPG data for channels...")
        programs = scraper.fetch_epg(channels)

        print(f"Step 4: Scraped {len(programs)} program events. Generating XMLTV...")
        generate_xmltv(channels, programs)
