from flask import Flask, jsonify, request
import requests
import re

app = Flask(__name__)

def parse_m3u(m3u_content):
    """Fungsi untuk memparsing teks mentah M3U menjadi list JSON"""
    channels = []
    # Split berdasarkan baris baru
    lines = m3u_content.split('\n')
    current_channel = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('#EXTINF:'):
            # Mengambil info logo, grup, dan nama channel menggunakan Regex
            tvg_id = re.search(r'tvg-id="([^"]*)"', line)
            tvg_name = re.search(r'tvg-name="([^"]*)"', line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
            group_title = re.search(r'group-title="([^"]*)"', line)
            
            # Nama channel biasanya ada di akhir baris setelah tanda koma
            channel_name = line.split(',')[-1].strip()
            
            current_channel = {
                "name": channel_name,
                "tvg_id": tvg_id.group(1) if tvg_id else "",
                "tvg_name": tvg_name.group(1) if tvg_name else "",
                "logo": tvg_logo.group(1) if tvg_logo else "",
                "group": group_title.group(1) if group_title else "Uncategorized"
            }
        elif line.startswith('http://') or line.startswith('https://'):
            # Jika baris berisi URL, pasangkan dengan info channel sebelumnya
            if current_channel:
                current_channel["url"] = line
                channels.append(current_channel)
                current_channel = {} # Reset untuk channel berikutnya
                
    return channels

@app.route('/api/iptv', methods=['GET'])
def get_channels():
    # Mengambil parameter ?url= dari frontend
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Parameter URL m3u tidak ditemukan"}), 400
        
    try:
        # Mengambil file M3U dari internet
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Proses parsing data M3U mentah menjadi struktur JSON
        parsed_data = parse_m3u(response.text)
        
        # Kembalikan hasil dalam bentuk JSON terstruktur
        return jsonify({
            "status": "success",
            "total_channels": len(parsed_data),
            "channels": parsed_data
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Gagal mengambil file M3U: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

# Vercel akan membaca objek 'app' ini secara otomatis
