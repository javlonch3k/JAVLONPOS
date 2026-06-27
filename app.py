"""
Restoran POS - Web versiya (Flask)
Ofitsiantlar uchun buyurtma qabul qilish tizimi
Bo'limlar: Salatchi, Shashlikchi, Somsachi
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import init_db, get_connection
from chek import barcha_cheklar
from printer import print_buyurtma_cheklari, print_chek, test_printer

app = Flask(__name__)
app.secret_key = 'restoran_pos_secret_key_2024'


@app.route('/')
def index():
    if 'ofitsiant_id' in session:
        return redirect(url_for('stollar'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # JSON (PIN pad) yoki form
        if request.is_json:
            data = request.json
            pin = data.get('pin', '').strip()
        else:
            pin = request.form.get('pin', '').strip()

        if not pin:
            if request.is_json:
                return jsonify({'success': False, 'error': 'PIN kiriting!'})
            flash('PIN kiriting!', 'error')
            return render_template('login.html')

        conn = get_connection()
        ofitsiant = conn.execute(
            "SELECT * FROM ofitsiantlar WHERE pin=?",
            (pin,)
        ).fetchone()
        conn.close()

        if ofitsiant:
            session['ofitsiant_id'] = ofitsiant['id']
            session['ofitsiant_ism'] = ofitsiant['ism']
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('stollar')})
            return redirect(url_for('stollar'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'error': 'PIN kod noto\'g\'ri!'})
            flash('PIN kod noto\'g\'ri!', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/stollar')
def stollar():
    if 'ofitsiant_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    stollar_list = conn.execute("SELECT * FROM stollar ORDER BY raqam").fetchall()
    conn.close()

    return render_template('stollar.html', stollar=stollar_list)


@app.route('/buyurtma/<int:stol_id>')
def buyurtma(stol_id):
    if 'ofitsiant_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()

    # Stol ma'lumoti
    stol = conn.execute("SELECT * FROM stollar WHERE id=?", (stol_id,)).fetchone()
    if not stol:
        conn.close()
        return redirect(url_for('stollar'))

    # Mavjud ochiq buyurtma bormi?
    buyurtma_row = conn.execute(
        "SELECT * FROM buyurtmalar WHERE stol_id=? AND holat='ochiq'",
        (stol_id,)
    ).fetchone()

    if not buyurtma_row:
        # Yangi buyurtma yaratish
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO buyurtmalar (stol_id, ofitsiant_id) VALUES (?, ?)",
            (stol_id, session['ofitsiant_id'])
        )
        buyurtma_id = cursor.lastrowid
        conn.execute("UPDATE stollar SET holat='band' WHERE id=?", (stol_id,))
        conn.commit()
    else:
        buyurtma_id = buyurtma_row['id']

    # Kategoriyalar
    kategoriyalar = conn.execute("SELECT * FROM kategoriyalar").fetchall()

    # Menyu
    menyu = conn.execute("SELECT * FROM menyu ORDER BY bolim, nomi").fetchall()

    # Buyurtma tafsilotlari
    items = conn.execute("""
        SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        WHERE bt.buyurtma_id = ?
    """, (buyurtma_id,)).fetchall()

    # Jami summa
    jami = sum(item['soni'] * item['narx'] for item in items)

    # Xizmat haqqi foizi
    foiz_row = conn.execute("SELECT qiymat FROM sozlamalar WHERE kalit='xizmat_haqqi_foiz'").fetchone()
    foiz = float(foiz_row['qiymat']) if foiz_row else 10

    conn.close()

    # Menyu JSON (JavaScript uchun)
    import json
    menyu_json = json.dumps([dict(m) for m in menyu])

    return render_template('buyurtma.html',
                           stol=stol,
                           buyurtma_id=buyurtma_id,
                           kategoriyalar=kategoriyalar,
                           menyu=menyu,
                           menyu_json=menyu_json,
                           items=items,
                           jami=jami,
                           foiz=foiz)


@app.route('/api/qoshish', methods=['POST'])
def api_qoshish():
    """Buyurtmaga taom qo'shish"""
    if 'ofitsiant_id' not in session:
        return jsonify({'error': 'Login qiling'}), 401

    data = request.json
    buyurtma_id = data.get('buyurtma_id')
    menyu_id = data.get('menyu_id')

    conn = get_connection()

    # Menyu item olish
    menyu_item = conn.execute("SELECT * FROM menyu WHERE id=?", (menyu_id,)).fetchone()
    if not menyu_item:
        conn.close()
        return jsonify({'error': 'Taom topilmadi'}), 404

    # Mavjud item bormi?
    mavjud = conn.execute(
        "SELECT * FROM buyurtma_tafsilot WHERE buyurtma_id=? AND menyu_id=?",
        (buyurtma_id, menyu_id)
    ).fetchone()

    if mavjud:
        conn.execute(
            "UPDATE buyurtma_tafsilot SET soni = soni + 1 WHERE buyurtma_id=? AND menyu_id=?",
            (buyurtma_id, menyu_id)
        )
    else:
        conn.execute(
            "INSERT INTO buyurtma_tafsilot (buyurtma_id, menyu_id, soni, narx, bolim) VALUES (?, ?, 1, ?, ?)",
            (buyurtma_id, menyu_id, menyu_item['narx'], menyu_item['bolim'])
        )

    conn.commit()

    # Yangilangan ma'lumotlarni qaytarish
    items = conn.execute("""
        SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        WHERE bt.buyurtma_id = ?
    """, (buyurtma_id,)).fetchall()

    jami = sum(item['soni'] * item['narx'] for item in items)

    conn.execute("UPDATE buyurtmalar SET jami_summa=? WHERE id=?", (jami, buyurtma_id))
    conn.commit()
    conn.close()

    items_list = [dict(item) for item in items]
    return jsonify({'items': items_list, 'jami': jami})


@app.route('/api/kamaytirish', methods=['POST'])
def api_kamaytirish():
    """Buyurtmadan taom kamaytirish"""
    if 'ofitsiant_id' not in session:
        return jsonify({'error': 'Login qiling'}), 401

    data = request.json
    buyurtma_id = data.get('buyurtma_id')
    menyu_id = data.get('menyu_id')

    conn = get_connection()

    mavjud = conn.execute(
        "SELECT * FROM buyurtma_tafsilot WHERE buyurtma_id=? AND menyu_id=?",
        (buyurtma_id, menyu_id)
    ).fetchone()

    if mavjud:
        if mavjud['soni'] > 1:
            conn.execute(
                "UPDATE buyurtma_tafsilot SET soni = soni - 1 WHERE buyurtma_id=? AND menyu_id=?",
                (buyurtma_id, menyu_id)
            )
        else:
            conn.execute(
                "DELETE FROM buyurtma_tafsilot WHERE buyurtma_id=? AND menyu_id=?",
                (buyurtma_id, menyu_id)
            )

    conn.commit()

    # Yangilangan ma'lumotlarni qaytarish
    items = conn.execute("""
        SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        WHERE bt.buyurtma_id = ?
    """, (buyurtma_id,)).fetchall()

    jami = sum(item['soni'] * item['narx'] for item in items)

    conn.execute("UPDATE buyurtmalar SET jami_summa=? WHERE id=?", (jami, buyurtma_id))
    conn.commit()
    conn.close()

    items_list = [dict(item) for item in items]
    return jsonify({'items': items_list, 'jami': jami})


@app.route('/chek/<int:buyurtma_id>')
def chek(buyurtma_id):
    """Bo'limlar bo'yicha cheklar"""
    if 'ofitsiant_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()

    buyurtma_row = conn.execute("SELECT * FROM buyurtmalar WHERE id=?", (buyurtma_id,)).fetchone()
    if not buyurtma_row:
        conn.close()
        return redirect(url_for('stollar'))

    stol = conn.execute("SELECT * FROM stollar WHERE id=?", (buyurtma_row['stol_id'],)).fetchone()

    items = conn.execute("""
        SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        WHERE bt.buyurtma_id = ?
    """, (buyurtma_id,)).fetchall()

    conn.close()

    if not items:
        flash('Buyurtma bo\'sh!', 'error')
        return redirect(url_for('buyurtma', stol_id=stol['id']))

    tafsilotlar = [dict(item) for item in items]
    cheklar = barcha_cheklar(buyurtma_id, stol['raqam'], session['ofitsiant_ism'], tafsilotlar)

    return render_template('chek.html', cheklar=cheklar, stol=stol, buyurtma_id=buyurtma_id)


@app.route('/yopish/<int:buyurtma_id>', methods=['POST'])
def yopish(buyurtma_id):
    """Hisobni yopish"""
    if 'ofitsiant_id' not in session:
        return redirect(url_for('login'))

    conn = get_connection()
    buyurtma_row = conn.execute("SELECT * FROM buyurtmalar WHERE id=?", (buyurtma_id,)).fetchone()

    if buyurtma_row:
        conn.execute("UPDATE buyurtmalar SET holat='yopiq' WHERE id=?", (buyurtma_id,))
        conn.execute("UPDATE stollar SET holat='bosh' WHERE id=?", (buyurtma_row['stol_id'],))
        conn.commit()

    conn.close()
    flash('Hisob yopildi! Stol bo\'shatildi.', 'success')
    return redirect(url_for('stollar'))


# ===== PRINTER BOSHQARISH =====

@app.route('/printerlar')
def printerlar():
    """Printerlar ro'yxati - faqat admin"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    printerlar_list = conn.execute("SELECT * FROM printerlar ORDER BY bolim, nomi").fetchall()
    conn.close()

    return render_template('printerlar.html', printerlar=printerlar_list)


@app.route('/printer/qoshish', methods=['POST'])
def printer_qoshish():
    """Yangi printer qo'shish - faqat admin"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    nomi = request.form.get('nomi', '').strip()
    ip_manzil = request.form.get('ip_manzil', '').strip()
    port = request.form.get('port', '9100').strip()
    bolim = request.form.get('bolim', '').strip()
    joylashuv = request.form.get('joylashuv', '').strip()

    if not nomi or not ip_manzil or not bolim:
        flash('Barcha maydonlarni to\'ldiring!', 'error')
        return redirect(url_for('printerlar'))

    conn = get_connection()
    conn.execute(
        "INSERT INTO printerlar (nomi, ip_manzil, port, bolim, joylashuv) VALUES (?, ?, ?, ?, ?)",
        (nomi, ip_manzil, int(port), bolim, joylashuv)
    )
    conn.commit()
    conn.close()

    flash(f'Printer "{nomi}" qo\'shildi!', 'success')
    return redirect(url_for('printerlar'))


@app.route('/printer/ochirish/<int:printer_id>', methods=['POST'])
def printer_ochirish(printer_id):
    """Printerni o'chirish - faqat admin"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    conn.execute("DELETE FROM printerlar WHERE id=?", (printer_id,))
    conn.commit()
    conn.close()

    flash('Printer o\'chirildi!', 'success')
    return redirect(url_for('printerlar'))


@app.route('/printer/toggle/<int:printer_id>', methods=['POST'])
def printer_toggle(printer_id):
    """Printerni yoqish/o'chirish - faqat admin"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    printer = conn.execute("SELECT * FROM printerlar WHERE id=?", (printer_id,)).fetchone()
    if printer:
        new_status = 0 if printer['faol'] else 1
        conn.execute("UPDATE printerlar SET faol=? WHERE id=?", (new_status, printer_id))
        conn.commit()
    conn.close()

    return redirect(url_for('printerlar'))


@app.route('/printer/test/<int:printer_id>', methods=['POST'])
def printer_test(printer_id):
    """Printerni test qilish - faqat admin"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Admin login qiling'}), 401

    conn = get_connection()
    printer = conn.execute("SELECT * FROM printerlar WHERE id=?", (printer_id,)).fetchone()
    conn.close()

    if not printer:
        return jsonify({'success': False, 'xabar': 'Printer topilmadi'})

    success, xabar = test_printer(printer['ip_manzil'], printer['port'])
    return jsonify({'success': success, 'xabar': xabar})


@app.route('/api/print/<int:buyurtma_id>', methods=['POST'])
def api_print(buyurtma_id):
    """Buyurtma chekllarini printerlarga yuborish - faqat yangi itemlar"""
    if 'ofitsiant_id' not in session:
        return jsonify({'error': 'Login qiling'}), 401

    conn = get_connection()
    buyurtma_row = conn.execute("SELECT * FROM buyurtmalar WHERE id=?", (buyurtma_id,)).fetchone()
    if not buyurtma_row:
        conn.close()
        return jsonify({'error': 'Buyurtma topilmadi'}), 404

    stol = conn.execute("SELECT * FROM stollar WHERE id=?", (buyurtma_row['stol_id'],)).fetchone()

    # Faqat chop etilmagan itemlarni olish
    items = conn.execute("""
        SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        WHERE bt.buyurtma_id = ? AND bt.chop_etilgan = 0
    """, (buyurtma_id,)).fetchall()

    if not items:
        conn.close()
        return jsonify({'error': 'Yangi buyurtma yo\'q! Allaqachon yuborilgan.'}), 400

    tafsilotlar = [dict(item) for item in items]
    natijalar = print_buyurtma_cheklari(
        buyurtma_id, stol['raqam'], session['ofitsiant_ism'], tafsilotlar
    )

    # Muvaffaqiyatli yuborilganlarni belgilash
    muvaffaqiyatli_bolimlar = set()
    for n in natijalar:
        if n['success']:
            muvaffaqiyatli_bolimlar.add(n['bolim'])

    # Chop etilgan deb belgilash
    if muvaffaqiyatli_bolimlar:
        for item in items:
            if item['bolim'] in muvaffaqiyatli_bolimlar:
                conn.execute(
                    "UPDATE buyurtma_tafsilot SET chop_etilgan=1 WHERE id=?",
                    (item['id'],)
                )
        conn.commit()

    conn.close()
    return jsonify({'natijalar': natijalar})


# ===== ADMIN PANEL =====

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        parol = request.form.get('parol', '').strip()

        conn = get_connection()
        admin = conn.execute(
            "SELECT * FROM adminlar WHERE login=? AND parol=?",
            (login_val, parol)
        ).fetchone()
        conn.close()

        if admin:
            session['admin_id'] = admin['id']
            session['admin_ism'] = admin['ism']
            return redirect(url_for('admin_panel'))
        else:
            flash('Login yoki parol noto\'g\'ri!', 'error')

    return render_template('admin_login.html')


@app.route('/admin')
def admin_panel():
    """Admin bosh sahifa"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    stats = {
        'stollar': conn.execute("SELECT COUNT(*) FROM stollar").fetchone()[0],
        'ofitsiantlar': conn.execute("SELECT COUNT(*) FROM ofitsiantlar").fetchone()[0],
        'menyu': conn.execute("SELECT COUNT(*) FROM menyu").fetchone()[0],
        'printerlar': conn.execute("SELECT COUNT(*) FROM printerlar").fetchone()[0],
        'bugungi_buyurtmalar': conn.execute(
            "SELECT COUNT(*) FROM buyurtmalar WHERE date(sana)=date('now','localtime')"
        ).fetchone()[0],
        'bugungi_daromad': conn.execute(
            "SELECT COALESCE(SUM(jami_summa),0) FROM buyurtmalar WHERE date(sana)=date('now','localtime') AND holat='yopiq'"
        ).fetchone()[0],
    }
    conn.close()

    return render_template('admin_panel.html', stats=stats)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_ism', None)
    return redirect(url_for('admin_login'))


# --- ADMIN: Menyu boshqarish ---

@app.route('/admin/menyu')
def admin_menyu():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    menyu = conn.execute("SELECT * FROM menyu ORDER BY bolim, nomi").fetchall()
    kategoriyalar = conn.execute("SELECT * FROM kategoriyalar").fetchall()
    conn.close()

    return render_template('admin_menyu.html', menyu=menyu, kategoriyalar=kategoriyalar)


@app.route('/admin/menyu/qoshish', methods=['POST'])
def admin_menyu_qoshish():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    nomi = request.form.get('nomi', '').strip()
    narx = request.form.get('narx', '0').strip()
    kategoriya_id = request.form.get('kategoriya_id', '').strip()
    bolim = request.form.get('bolim', '').strip()

    if not nomi or not narx or not bolim:
        flash('Barcha maydonlarni to\'ldiring!', 'error')
        return redirect(url_for('admin_menyu'))

    conn = get_connection()
    conn.execute(
        "INSERT INTO menyu (nomi, narx, kategoriya_id, bolim) VALUES (?, ?, ?, ?)",
        (nomi, float(narx), int(kategoriya_id) if kategoriya_id else None, bolim)
    )
    conn.commit()
    conn.close()

    flash(f'"{nomi}" menyuga qo\'shildi!', 'success')
    return redirect(url_for('admin_menyu'))


@app.route('/admin/menyu/ochirish/<int:menyu_id>', methods=['POST'])
def admin_menyu_ochirish(menyu_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    conn.execute("DELETE FROM menyu WHERE id=?", (menyu_id,))
    conn.commit()
    conn.close()

    flash('Taom o\'chirildi!', 'success')
    return redirect(url_for('admin_menyu'))


@app.route('/admin/menyu/tahrirlash/<int:menyu_id>', methods=['POST'])
def admin_menyu_tahrirlash(menyu_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    nomi = request.form.get('nomi', '').strip()
    narx = request.form.get('narx', '0').strip()
    bolim = request.form.get('bolim', '').strip()

    conn = get_connection()
    conn.execute(
        "UPDATE menyu SET nomi=?, narx=?, bolim=? WHERE id=?",
        (nomi, float(narx), bolim, menyu_id)
    )
    conn.commit()
    conn.close()

    flash('Taom yangilandi!', 'success')
    return redirect(url_for('admin_menyu'))


# --- ADMIN: Stollar boshqarish ---

@app.route('/admin/stollar')
def admin_stollar():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    stollar_list = conn.execute("SELECT * FROM stollar ORDER BY raqam").fetchall()
    conn.close()

    return render_template('admin_stollar.html', stollar=stollar_list)


@app.route('/admin/stol/qoshish', methods=['POST'])
def admin_stol_qoshish():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    max_raqam = conn.execute("SELECT COALESCE(MAX(raqam),0) FROM stollar").fetchone()[0]
    conn.execute("INSERT INTO stollar (raqam) VALUES (?)", (max_raqam + 1,))
    conn.commit()
    conn.close()

    flash(f'Stol #{max_raqam + 1} qo\'shildi!', 'success')
    return redirect(url_for('admin_stollar'))


@app.route('/admin/stol/ochirish/<int:stol_id>', methods=['POST'])
def admin_stol_ochirish(stol_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    conn.execute("DELETE FROM stollar WHERE id=?", (stol_id,))
    conn.commit()
    conn.close()

    flash('Stol o\'chirildi!', 'success')
    return redirect(url_for('admin_stollar'))


# --- ADMIN: Ofitsiantlar boshqarish ---

@app.route('/admin/ofitsiantlar')
def admin_ofitsiantlar():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    ofitsiantlar_list = conn.execute("SELECT * FROM ofitsiantlar ORDER BY ism").fetchall()
    conn.close()

    return render_template('admin_ofitsiantlar.html', ofitsiantlar=ofitsiantlar_list)


@app.route('/admin/ofitsiant/qoshish', methods=['POST'])
def admin_ofitsiant_qoshish():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    ism = request.form.get('ism', '').strip()
    pin = request.form.get('pin', '').strip()

    if not ism or not pin:
        flash('Ism va PIN kiriting!', 'error')
        return redirect(url_for('admin_ofitsiantlar'))

    conn = get_connection()
    # PIN takrorlanmasin
    mavjud = conn.execute("SELECT * FROM ofitsiantlar WHERE pin=?", (pin,)).fetchone()
    if mavjud:
        conn.close()
        flash('Bu PIN allaqachon mavjud!', 'error')
        return redirect(url_for('admin_ofitsiantlar'))

    conn.execute(
        "INSERT INTO ofitsiantlar (ism, pin) VALUES (?, ?)",
        (ism, pin)
    )
    conn.commit()
    conn.close()

    flash(f'Ofitsiant "{ism}" qo\'shildi! PIN: {pin}', 'success')
    return redirect(url_for('admin_ofitsiantlar'))


@app.route('/admin/ofitsiant/ochirish/<int:ofitsiant_id>', methods=['POST'])
def admin_ofitsiant_ochirish(ofitsiant_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()
    conn.execute("DELETE FROM ofitsiantlar WHERE id=?", (ofitsiant_id,))
    conn.commit()
    conn.close()

    flash('Ofitsiant o\'chirildi!', 'success')
    return redirect(url_for('admin_ofitsiantlar'))


@app.route('/admin/ofitsiant/parol/<int:ofitsiant_id>', methods=['POST'])
def admin_ofitsiant_parol(ofitsiant_id):
    """Faqat admin PIN o'zgartira oladi"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    yangi_pin = request.form.get('pin', '').strip()
    if not yangi_pin:
        flash('PIN bo\'sh bo\'lishi mumkin emas!', 'error')
        return redirect(url_for('admin_ofitsiantlar'))

    conn = get_connection()
    # PIN takrorlanmasin
    mavjud = conn.execute("SELECT * FROM ofitsiantlar WHERE pin=? AND id!=?", (yangi_pin, ofitsiant_id)).fetchone()
    if mavjud:
        conn.close()
        flash('Bu PIN boshqa ofitsiantda mavjud!', 'error')
        return redirect(url_for('admin_ofitsiantlar'))

    conn.execute("UPDATE ofitsiantlar SET pin=? WHERE id=?", (yangi_pin, ofitsiant_id))
    conn.commit()
    conn.close()

    flash('PIN o\'zgartirildi!', 'success')
    return redirect(url_for('admin_ofitsiantlar'))


# --- ADMIN: Hisobot ---

@app.route('/admin/hisobot')
def admin_hisobot():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()

    # Xizmat haqqi foizi
    foiz_row = conn.execute("SELECT qiymat FROM sozlamalar WHERE kalit='xizmat_haqqi_foiz'").fetchone()
    foiz = float(foiz_row['qiymat']) if foiz_row else 10

    # Bugungi sotuv
    bugungi = conn.execute("""
        SELECT COALESCE(SUM(jami_summa),0) as jami, COUNT(*) as soni
        FROM buyurtmalar
        WHERE date(sana)=date('now','localtime') AND holat='yopiq'
    """).fetchone()

    bugungi_jami = bugungi['jami']
    bugungi_xizmat = bugungi_jami * foiz / 100
    bugungi_umumiy = bugungi_jami + bugungi_xizmat

    # Oylik sotuv
    oylik = conn.execute("""
        SELECT COALESCE(SUM(jami_summa),0) as jami, COUNT(*) as soni
        FROM buyurtmalar
        WHERE strftime('%Y-%m', sana)=strftime('%Y-%m', 'now','localtime') AND holat='yopiq'
    """).fetchone()

    oylik_jami = oylik['jami']
    oylik_xizmat = oylik_jami * foiz / 100
    oylik_umumiy = oylik_jami + oylik_xizmat

    # Eng ko'p sotilgan taomlar
    top_taomlar = conn.execute("""
        SELECT m.nomi, m.bolim, SUM(bt.soni) as jami_soni, SUM(bt.soni * bt.narx) as jami_summa
        FROM buyurtma_tafsilot bt
        JOIN menyu m ON bt.menyu_id = m.id
        JOIN buyurtmalar b ON bt.buyurtma_id = b.id
        WHERE b.holat='yopiq'
        GROUP BY bt.menyu_id
        ORDER BY jami_soni DESC
        LIMIT 10
    """).fetchall()

    # Ofitsiantlar bo'yicha
    ofitsiant_stat = conn.execute("""
        SELECT o.ism, COUNT(b.id) as buyurtmalar, COALESCE(SUM(b.jami_summa),0) as jami
        FROM ofitsiantlar o
        LEFT JOIN buyurtmalar b ON o.id = b.ofitsiant_id AND b.holat='yopiq'
        GROUP BY o.id
        ORDER BY jami DESC
    """).fetchall()

    # Bugungi cheklar (batafsil)
    bugungi_cheklar = conn.execute("""
        SELECT b.*, s.raqam as stol_raqam, o.ism as ofitsiant_ism
        FROM buyurtmalar b
        JOIN stollar s ON b.stol_id = s.id
        JOIN ofitsiantlar o ON b.ofitsiant_id = o.id
        WHERE date(b.sana)=date('now','localtime')
        ORDER BY b.sana DESC
    """).fetchall()

    conn.close()

    return render_template('admin_hisobot.html',
                           foiz=foiz,
                           bugungi_jami=bugungi_jami,
                           bugungi_xizmat=bugungi_xizmat,
                           bugungi_umumiy=bugungi_umumiy,
                           bugungi_soni=bugungi['soni'],
                           oylik_jami=oylik_jami,
                           oylik_xizmat=oylik_xizmat,
                           oylik_umumiy=oylik_umumiy,
                           oylik_soni=oylik['soni'],
                           top_taomlar=top_taomlar,
                           ofitsiant_stat=ofitsiant_stat,
                           bugungi_cheklar=bugungi_cheklar)


@app.route('/admin/sozlamalar', methods=['GET', 'POST'])
def admin_sozlamalar():
    """Xizmat haqqi foizi va boshqa sozlamalar"""
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_connection()

    if request.method == 'POST':
        foiz = request.form.get('xizmat_haqqi_foiz', '10').strip()
        conn.execute(
            "UPDATE sozlamalar SET qiymat=? WHERE kalit='xizmat_haqqi_foiz'",
            (foiz,)
        )
        conn.commit()
        flash(f'Xizmat haqqi {foiz}% ga o\'zgartirildi!', 'success')

    foiz_row = conn.execute("SELECT qiymat FROM sozlamalar WHERE kalit='xizmat_haqqi_foiz'").fetchone()
    foiz = foiz_row['qiymat'] if foiz_row else '10'
    conn.close()

    return render_template('admin_sozlamalar.html', foiz=foiz)


with app.app_context():
    init_db()
    # Tekshirish: ofitsiantlar bormi
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM ofitsiantlar").fetchone()[0]
    print(f"DB tayyor. Ofitsiantlar soni: {count}")
    conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
