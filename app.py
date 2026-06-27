"""
Restoran POS - Web versiya (Flask)
Ofitsiantlar uchun buyurtma qabul qilish tizimi
Bo'limlar: Salatchi, Shashlikchi, Somsachi
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import init_db, get_connection
from chek import barcha_cheklar

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
        login_val = request.form.get('login', '').strip()
        parol = request.form.get('parol', '').strip()

        if not login_val or not parol:
            flash('Login va parolni kiriting!', 'error')
            return render_template('login.html')

        conn = get_connection()
        ofitsiant = conn.execute(
            "SELECT * FROM ofitsiantlar WHERE login=? AND parol=?",
            (login_val, parol)
        ).fetchone()
        conn.close()

        if ofitsiant:
            session['ofitsiant_id'] = ofitsiant['id']
            session['ofitsiant_ism'] = ofitsiant['ism']
            return redirect(url_for('stollar'))
        else:
            flash('Login yoki parol noto\'g\'ri!', 'error')

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

    conn.close()

    return render_template('buyurtma.html',
                           stol=stol,
                           buyurtma_id=buyurtma_id,
                           kategoriyalar=kategoriyalar,
                           menyu=menyu,
                           items=items,
                           jami=jami)


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


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
