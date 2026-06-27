"""
Network Printer moduli - ESC/POS protokol orqali
POS thermal printerlarga IP orqali chek yuborish
"""
import socket
from database import get_connection


# ESC/POS buyruqlar
ESC = b'\x1b'
GS = b'\x1d'
INIT = ESC + b'@'          # Printer initialize
CUT = GS + b'V\x00'        # Qog'ozni kesish
BOLD_ON = ESC + b'E\x01'   # Qalin yozuv
BOLD_OFF = ESC + b'E\x00'  # Oddiy yozuv
CENTER = ESC + b'a\x01'    # Markazga
LEFT = ESC + b'a\x00'      # Chapga
DOUBLE_SIZE = GS + b'!\x11'  # 2x kattalik
NORMAL_SIZE = GS + b'!\x00'  # Normal
LINE_FEED = b'\n'
DRAWER_OPEN = ESC + b'p\x00\x19\xfa'  # Kassa tortmasini ochish


def send_to_printer(ip, port, data):
    """
    Printerga ma'lumot yuborish (socket orqali)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        sock.sendall(data)
        sock.close()
        return True, "Muvaffaqiyatli yuborildi"
    except socket.timeout:
        return False, f"Printer javob bermayapti: {ip}:{port}"
    except ConnectionRefusedError:
        return False, f"Printerga ulanib bo'lmadi: {ip}:{port}"
    except Exception as e:
        return False, f"Xatolik: {str(e)}"


def format_chek_for_printer(chek_matn):
    """
    Chek matnini ESC/POS formatiga o'girish
    """
    data = INIT  # Initialize

    lines = chek_matn.strip().split('\n')

    for line in lines:
        stripped = line.strip()

        # Sarlavha (RESTORAN POS)
        if 'RESTORAN POS' in stripped:
            data += CENTER + DOUBLE_SIZE
            data += stripped.encode('utf-8') + LINE_FEED
            data += NORMAL_SIZE + LEFT
        # Chiziqlar
        elif stripped.startswith('===') or stripped.startswith('---'):
            data += b'-' * 32 + LINE_FEED
        # JAMI
        elif 'JAMI:' in stripped:
            data += BOLD_ON
            data += stripped.encode('utf-8') + LINE_FEED
            data += BOLD_OFF
        # Bo'lim nomi
        elif 'BO\'LIMI CHEKI' in stripped or 'UMUMIY HISOB' in stripped:
            data += CENTER + BOLD_ON
            data += stripped.encode('utf-8') + LINE_FEED
            data += BOLD_OFF + LEFT
        # Oddiy satr
        else:
            data += stripped.encode('utf-8') + LINE_FEED

    # Qog'ozni surish va kesish
    data += LINE_FEED * 3
    data += CUT

    return data


def print_chek(printer_id, chek_matn):
    """
    Chekni printerga yuborish (printer ID bo'yicha)
    """
    conn = get_connection()
    printer = conn.execute("SELECT * FROM printerlar WHERE id=?", (printer_id,)).fetchone()
    conn.close()

    if not printer:
        return False, "Printer topilmadi"

    if not printer['faol']:
        return False, f"Printer '{printer['nomi']}' o'chirilgan"

    data = format_chek_for_printer(chek_matn)
    return send_to_printer(printer['ip_manzil'], printer['port'], data)


def print_buyurtma_cheklari(buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar):
    """
    Buyurtma cheklrini tegishli printerlarga yuborish
    Har bir bo'lim cheki o'sha bo'limning printeriga chiqadi
    """
    from chek import barcha_cheklar

    cheklar = barcha_cheklar(buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar)
    natijalar = []

    conn = get_connection()
    printerlar = conn.execute("SELECT * FROM printerlar WHERE faol=1").fetchall()
    conn.close()

    for printer in printerlar:
        bolim = printer['bolim']

        # Bu bo'limga tegishli chek bormi?
        if bolim in cheklar:
            chek_matn = cheklar[bolim]['matn']
            success, xabar = print_chek(printer['id'], chek_matn)
            natijalar.append({
                'printer': printer['nomi'],
                'bolim': bolim,
                'ip': printer['ip_manzil'],
                'success': success,
                'xabar': xabar
            })

    return natijalar


def test_printer(ip, port=9100):
    """
    Printer ulanishini tekshirish
    """
    test_data = INIT + CENTER + BOLD_ON
    test_data += "*** TEST CHEK ***\n".encode('utf-8')
    test_data += BOLD_OFF + LEFT
    test_data += "Printer ishlayapti!\n".encode('utf-8')
    test_data += f"IP: {ip}:{port}\n".encode('utf-8')
    test_data += LINE_FEED * 3 + CUT

    return send_to_printer(ip, port, test_data)
