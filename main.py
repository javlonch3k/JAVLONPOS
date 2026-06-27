"""
Restoran POS dasturi - Ofitsiantlar uchun
Bo'limlar: Salatchi, Shashlikchi, Somsachi
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from database import init_db, get_connection
from chek import barcha_cheklar


class LoginOyna:
    """Ofitsiant login oynasi"""

    def __init__(self, root, on_login):
        self.root = root
        self.on_login = on_login
        self.frame = tk.Frame(root, bg="#2c3e50")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Markaziy panel
        panel = tk.Frame(self.frame, bg="#34495e", padx=40, pady=40)
        panel.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(panel, text="RESTORAN POS", font=("Arial", 24, "bold"),
                 bg="#34495e", fg="white").pack(pady=(0, 5))
        tk.Label(panel, text="Ofitsiant tizimi", font=("Arial", 12),
                 bg="#34495e", fg="#bdc3c7").pack(pady=(0, 30))

        # Login
        tk.Label(panel, text="Login:", font=("Arial", 12),
                 bg="#34495e", fg="white").pack(anchor=tk.W)
        self.login_entry = tk.Entry(panel, font=("Arial", 14), width=25)
        self.login_entry.pack(pady=(5, 15))

        # Parol
        tk.Label(panel, text="Parol:", font=("Arial", 12),
                 bg="#34495e", fg="white").pack(anchor=tk.W)
        self.parol_entry = tk.Entry(panel, font=("Arial", 14), width=25, show="*")
        self.parol_entry.pack(pady=(5, 20))

        # Kirish tugmasi
        tk.Button(panel, text="KIRISH", font=("Arial", 14, "bold"),
                  bg="#27ae60", fg="white", width=20, height=2,
                  command=self.kirish).pack(pady=10)

        # Enter tugmasi bilan kirish
        self.root.bind('<Return>', lambda e: self.kirish())

    def kirish(self):
        login = self.login_entry.get().strip()
        parol = self.parol_entry.get().strip()

        if not login or not parol:
            messagebox.showwarning("Xatolik", "Login va parolni kiriting!")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM ofitsiantlar WHERE login=? AND parol=?",
            (login, parol)
        )
        ofitsiant = cursor.fetchone()
        conn.close()

        if ofitsiant:
            self.frame.destroy()
            self.root.unbind('<Return>')
            self.on_login(dict(ofitsiant))
        else:
            messagebox.showerror("Xatolik", "Login yoki parol noto'g'ri!")


class AsosiyOyna:
    """Asosiy dastur oynasi"""

    def __init__(self, root, ofitsiant):
        self.root = root
        self.ofitsiant = ofitsiant
        self.joriy_buyurtma_id = None
        self.joriy_stol = None
        self.buyurtma_items = []  # [{menyu_id, nomi, narx, soni, bolim}]

        self.frame = tk.Frame(root, bg="#ecf0f1")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.ui_yaratish()

    def ui_yaratish(self):
        # Yuqori panel
        top_panel = tk.Frame(self.frame, bg="#2c3e50", height=60)
        top_panel.pack(fill=tk.X)
        top_panel.pack_propagate(False)

        tk.Label(top_panel, text="RESTORAN POS",
                 font=("Arial", 16, "bold"), bg="#2c3e50", fg="white"
                 ).pack(side=tk.LEFT, padx=20)

        tk.Label(top_panel, text=f"Ofitsiant: {self.ofitsiant['ism']}",
                 font=("Arial", 12), bg="#2c3e50", fg="#bdc3c7"
                 ).pack(side=tk.RIGHT, padx=20)

        # Asosiy maydon
        main_area = tk.Frame(self.frame, bg="#ecf0f1")
        main_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chap panel - Stollar
        self.stollar_paneli(main_area)

        # O'rta panel - Menyu
        self.menyu_paneli(main_area)

        # O'ng panel - Buyurtma
        self.buyurtma_paneli(main_area)

    def stollar_paneli(self, parent):
        """Stollar ko'rinishi"""
        panel = tk.LabelFrame(parent, text=" STOLLAR ", font=("Arial", 12, "bold"),
                              bg="#ecf0f1", padx=10, pady=10)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.stol_buttons = {}
        conn = get_connection()
        stollar = conn.execute("SELECT * FROM stollar ORDER BY raqam").fetchall()
        conn.close()

        for i, stol in enumerate(stollar):
            row = i // 2
            col = i % 2
            rang = "#27ae60" if stol['holat'] == 'bosh' else "#e74c3c"
            btn = tk.Button(panel, text=f"Stol\n{stol['raqam']}",
                           font=("Arial", 11, "bold"), width=8, height=3,
                           bg=rang, fg="white",
                           command=lambda s=stol: self.stol_tanlash(s))
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.stol_buttons[stol['raqam']] = btn

    def stol_tanlash(self, stol):
        """Stol tanlash"""
        self.joriy_stol = dict(stol)

        # Mavjud ochiq buyurtma bormi?
        conn = get_connection()
        buyurtma = conn.execute(
            "SELECT * FROM buyurtmalar WHERE stol_id=? AND holat='ochiq'",
            (stol['id'],)
        ).fetchone()

        if buyurtma:
            self.joriy_buyurtma_id = buyurtma['id']
            # Mavjud itemlarni yuklash
            items = conn.execute("""
                SELECT bt.*, m.nomi FROM buyurtma_tafsilot bt
                JOIN menyu m ON bt.menyu_id = m.id
                WHERE bt.buyurtma_id = ?
            """, (buyurtma['id'],)).fetchall()
            self.buyurtma_items = [dict(item) for item in items]
        else:
            # Yangi buyurtma
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO buyurtmalar (stol_id, ofitsiant_id) VALUES (?, ?)",
                (stol['id'], self.ofitsiant['id'])
            )
            self.joriy_buyurtma_id = cursor.lastrowid
            conn.execute(
                "UPDATE stollar SET holat='band' WHERE id=?", (stol['id'],)
            )
            conn.commit()
            self.buyurtma_items = []

        conn.close()

        self.buyurtma_yangilash()
        self.stollar_yangilash()
        self.stol_label.config(text=f"Stol #{stol['raqam']} | Buyurtma #{self.joriy_buyurtma_id}")

    def menyu_paneli(self, parent):
        """Menyu ko'rinishi"""
        panel = tk.LabelFrame(parent, text=" MENYU ", font=("Arial", 12, "bold"),
                              bg="#ecf0f1", padx=10, pady=10)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Kategoriya tugmalari
        kat_frame = tk.Frame(panel, bg="#ecf0f1")
        kat_frame.pack(fill=tk.X, pady=(0, 10))

        conn = get_connection()
        kategoriyalar = conn.execute("SELECT * FROM kategoriyalar").fetchall()
        conn.close()

        # "Hammasi" tugmasi
        tk.Button(kat_frame, text="Hammasi", font=("Arial", 10, "bold"),
                  bg="#3498db", fg="white", padx=10,
                  command=lambda: self.menyu_yuklash(None)
                  ).pack(side=tk.LEFT, padx=2)

        for kat in kategoriyalar:
            bolim_rang = {"salatchi": "#27ae60", "shashlikchi": "#e67e22", "somsachi": "#9b59b6"}
            rang = bolim_rang.get(kat['bolim'], "#3498db")
            tk.Button(kat_frame, text=kat['nomi'], font=("Arial", 9),
                      bg=rang, fg="white", padx=8,
                      command=lambda k=kat['id']: self.menyu_yuklash(k)
                      ).pack(side=tk.LEFT, padx=2)

        # Menyu ro'yxati
        self.menyu_frame = tk.Frame(panel, bg="white")
        self.menyu_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        canvas = tk.Canvas(self.menyu_frame, bg="white")
        scrollbar = ttk.Scrollbar(self.menyu_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.menyu_scroll_frame = tk.Frame(canvas, bg="white")

        self.menyu_scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.menyu_scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.menyu_yuklash(None)

    def menyu_yuklash(self, kategoriya_id):
        """Menyu itemlarini yuklash"""
        for widget in self.menyu_scroll_frame.winfo_children():
            widget.destroy()

        conn = get_connection()
        if kategoriya_id:
            items = conn.execute(
                "SELECT * FROM menyu WHERE kategoriya_id=? ORDER BY nomi",
                (kategoriya_id,)
            ).fetchall()
        else:
            items = conn.execute("SELECT * FROM menyu ORDER BY bolim, nomi").fetchall()
        conn.close()

        bolim_rang = {"salatchi": "#27ae60", "shashlikchi": "#e67e22", "somsachi": "#9b59b6"}

        for item in items:
            item_frame = tk.Frame(self.menyu_scroll_frame, bg="white",
                                  highlightbackground="#ddd", highlightthickness=1)
            item_frame.pack(fill=tk.X, padx=5, pady=2)

            # Bo'lim rangli chiziq
            rang = bolim_rang.get(item['bolim'], "#3498db")
            tk.Frame(item_frame, bg=rang, width=5).pack(side=tk.LEFT, fill=tk.Y)

            # Ma'lumot
            info_frame = tk.Frame(item_frame, bg="white")
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)

            tk.Label(info_frame, text=item['nomi'], font=("Arial", 11, "bold"),
                     bg="white", anchor=tk.W).pack(anchor=tk.W)
            tk.Label(info_frame, text=f"{item['narx']:,.0f} so'm | {item['bolim']}",
                     font=("Arial", 9), bg="white", fg="#7f8c8d", anchor=tk.W).pack(anchor=tk.W)

            # Qo'shish tugmasi
            tk.Button(item_frame, text="+", font=("Arial", 14, "bold"),
                      bg=rang, fg="white", width=3,
                      command=lambda i=item: self.buyurtmaga_qoshish(dict(i))
                      ).pack(side=tk.RIGHT, padx=10, pady=5)

    def buyurtma_paneli(self, parent):
        """Buyurtma ko'rinishi"""
        panel = tk.LabelFrame(parent, text=" BUYURTMA ", font=("Arial", 12, "bold"),
                              bg="#ecf0f1", padx=10, pady=10, width=300)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)
        panel.config(width=320)

        # Stol ma'lumoti
        self.stol_label = tk.Label(panel, text="Stol tanlang...",
                                   font=("Arial", 11, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.stol_label.pack(pady=(0, 10))

        # Buyurtma ro'yxati
        self.buyurtma_listbox = tk.Listbox(panel, font=("Arial", 10), height=15, width=35)
        self.buyurtma_listbox.pack(fill=tk.BOTH, expand=True)

        # O'chirish tugmasi
        tk.Button(panel, text="O'chirish", font=("Arial", 10),
                  bg="#e74c3c", fg="white",
                  command=self.itemni_ochirish).pack(fill=tk.X, pady=(5, 0))

        # Jami summa
        self.jami_label = tk.Label(panel, text="JAMI: 0 so'm",
                                   font=("Arial", 14, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.jami_label.pack(pady=10)

        # Tugmalar
        btn_frame = tk.Frame(panel, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X)

        tk.Button(btn_frame, text="CHEK CHIQARISH\n(Bo'limlar bo'yicha)",
                  font=("Arial", 11, "bold"), bg="#3498db", fg="white", height=3,
                  command=self.chek_chiqarish).pack(fill=tk.X, pady=2)

        tk.Button(btn_frame, text="HISOBNI YOPISH",
                  font=("Arial", 11, "bold"), bg="#27ae60", fg="white", height=2,
                  command=self.hisobni_yopish).pack(fill=tk.X, pady=2)

    def buyurtmaga_qoshish(self, menyu_item):
        """Buyurtmaga taom qo'shish"""
        if not self.joriy_buyurtma_id:
            messagebox.showwarning("Xatolik", "Avval stol tanlang!")
            return

        # Mavjud item bormi?
        for item in self.buyurtma_items:
            if item.get('menyu_id') == menyu_item['id']:
                item['soni'] += 1
                # DB yangilash
                conn = get_connection()
                conn.execute(
                    "UPDATE buyurtma_tafsilot SET soni=? WHERE buyurtma_id=? AND menyu_id=?",
                    (item['soni'], self.joriy_buyurtma_id, menyu_item['id'])
                )
                conn.commit()
                conn.close()
                self.buyurtma_yangilash()
                return

        # Yangi item
        conn = get_connection()
        conn.execute(
            "INSERT INTO buyurtma_tafsilot (buyurtma_id, menyu_id, soni, narx, bolim) VALUES (?, ?, ?, ?, ?)",
            (self.joriy_buyurtma_id, menyu_item['id'], 1, menyu_item['narx'], menyu_item['bolim'])
        )
        conn.commit()
        conn.close()

        self.buyurtma_items.append({
            'menyu_id': menyu_item['id'],
            'nomi': menyu_item['nomi'],
            'narx': menyu_item['narx'],
            'soni': 1,
            'bolim': menyu_item['bolim']
        })
        self.buyurtma_yangilash()

    def itemni_ochirish(self):
        """Tanlangan itemni o'chirish"""
        selection = self.buyurtma_listbox.curselection()
        if not selection:
            messagebox.showwarning("Xatolik", "O'chirish uchun item tanlang!")
            return

        index = selection[0]
        item = self.buyurtma_items[index]

        if item['soni'] > 1:
            item['soni'] -= 1
            conn = get_connection()
            conn.execute(
                "UPDATE buyurtma_tafsilot SET soni=? WHERE buyurtma_id=? AND menyu_id=?",
                (item['soni'], self.joriy_buyurtma_id, item['menyu_id'])
            )
            conn.commit()
            conn.close()
        else:
            conn = get_connection()
            conn.execute(
                "DELETE FROM buyurtma_tafsilot WHERE buyurtma_id=? AND menyu_id=?",
                (self.joriy_buyurtma_id, item['menyu_id'])
            )
            conn.commit()
            conn.close()
            self.buyurtma_items.pop(index)

        self.buyurtma_yangilash()

    def buyurtma_yangilash(self):
        """Buyurtma ro'yxatini yangilash"""
        self.buyurtma_listbox.delete(0, tk.END)
        jami = 0

        for item in self.buyurtma_items:
            summa = item['soni'] * item['narx']
            jami += summa
            matn = f"{item['nomi']} x{item['soni']} = {summa:,.0f}"
            self.buyurtma_listbox.insert(tk.END, matn)

        self.jami_label.config(text=f"JAMI: {jami:,.0f} so'm")

        # DB yangilash
        if self.joriy_buyurtma_id:
            conn = get_connection()
            conn.execute(
                "UPDATE buyurtmalar SET jami_summa=? WHERE id=?",
                (jami, self.joriy_buyurtma_id)
            )
            conn.commit()
            conn.close()

    def chek_chiqarish(self):
        """Bo'limlar bo'yicha chek chiqarish"""
        if not self.buyurtma_items:
            messagebox.showwarning("Xatolik", "Buyurtma bo'sh!")
            return

        cheklar = barcha_cheklar(
            self.joriy_buyurtma_id,
            self.joriy_stol['raqam'],
            self.ofitsiant['ism'],
            self.buyurtma_items
        )

        # Chek oynasi
        chek_oyna = tk.Toplevel(self.root)
        chek_oyna.title("Cheklar - Bo'limlar bo'yicha")
        chek_oyna.geometry("700x600")
        chek_oyna.configure(bg="#2c3e50")

        # Tab lar
        notebook = ttk.Notebook(chek_oyna)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        bolim_nomlari = {
            'salatchi': 'Salatchi',
            'shashlikchi': 'Shashlikchi',
            'somsachi': 'Somsachi',
            'umumiy': 'Umumiy hisob'
        }

        for bolim, data in cheklar.items():
            frame = tk.Frame(notebook)
            notebook.add(frame, text=f" {bolim_nomlari.get(bolim, bolim)} ")

            text_widget = scrolledtext.ScrolledText(frame, font=("Courier", 12),
                                                    width=50, height=25)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, data['matn'])
            text_widget.config(state=tk.DISABLED)

            # Chop etish tugmasi
            tk.Button(frame, text=f"CHOP ETISH ({bolim_nomlari.get(bolim, bolim)})",
                      font=("Arial", 11, "bold"), bg="#27ae60", fg="white",
                      command=lambda m=data['matn'], b=bolim: self.chop_etish(m, b)
                      ).pack(pady=5)

    def chop_etish(self, matn, bolim):
        """Chekni chop etish (fayl sifatida saqlash)"""
        import os
        cheklar_dir = os.path.join(os.path.dirname(__file__), "cheklar")
        os.makedirs(cheklar_dir, exist_ok=True)

        from datetime import datetime
        fayl_nomi = f"chek_{bolim}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        fayl_path = os.path.join(cheklar_dir, fayl_nomi)

        with open(fayl_path, 'w', encoding='utf-8') as f:
            f.write(matn)

        messagebox.showinfo("Muvaffaqiyat", f"Chek saqlandi:\n{fayl_nomi}")

    def hisobni_yopish(self):
        """Buyurtmani yopish va stolni bo'shatish"""
        if not self.joriy_buyurtma_id:
            return

        if not self.buyurtma_items:
            messagebox.showwarning("Xatolik", "Buyurtma bo'sh!")
            return

        javob = messagebox.askyesno("Tasdiqlash", "Hisobni yopishni tasdiqlaysizmi?")
        if not javob:
            return

        conn = get_connection()
        conn.execute(
            "UPDATE buyurtmalar SET holat='yopiq' WHERE id=?",
            (self.joriy_buyurtma_id,)
        )
        conn.execute(
            "UPDATE stollar SET holat='bosh' WHERE id=?",
            (self.joriy_stol['id'],)
        )
        conn.commit()
        conn.close()

        self.joriy_buyurtma_id = None
        self.joriy_stol = None
        self.buyurtma_items = []
        self.buyurtma_yangilash()
        self.stollar_yangilash()
        self.stol_label.config(text="Stol tanlang...")

        messagebox.showinfo("Muvaffaqiyat", "Hisob yopildi! Stol bo'shatildi.")

    def stollar_yangilash(self):
        """Stol ranglarini yangilash"""
        conn = get_connection()
        stollar = conn.execute("SELECT * FROM stollar ORDER BY raqam").fetchall()
        conn.close()

        for stol in stollar:
            btn = self.stol_buttons.get(stol['raqam'])
            if btn:
                rang = "#27ae60" if stol['holat'] == 'bosh' else "#e74c3c"
                btn.config(bg=rang)


def main():
    # DB yaratish
    init_db()

    # Oynani yaratish
    root = tk.Tk()
    root.title("Restoran POS - Ofitsiant tizimi")
    root.geometry("1200x700")
    root.configure(bg="#2c3e50")

    # Login oynasi
    def on_login(ofitsiant):
        AsosiyOyna(root, ofitsiant)

    LoginOyna(root, on_login)

    root.mainloop()


if __name__ == "__main__":
    main()
