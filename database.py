import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "restoran.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Kategoriyalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kategoriyalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomi TEXT NOT NULL,
            bolim TEXT NOT NULL  -- salatchi, shashlikchi, somsachi
        )
    """)

    # Menyu jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menyu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nomi TEXT NOT NULL,
            narx REAL NOT NULL,
            kategoriya_id INTEGER,
            bolim TEXT NOT NULL,  -- salatchi, shashlikchi, somsachi
            FOREIGN KEY (kategoriya_id) REFERENCES kategoriyalar(id)
        )
    """)

    # Stollar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stollar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raqam INTEGER NOT NULL UNIQUE,
            holat TEXT DEFAULT 'bosh'  -- bosh, band
        )
    """)

    # Ofitsiantlar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ofitsiantlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ism TEXT NOT NULL,
            login TEXT NOT NULL UNIQUE,
            parol TEXT NOT NULL
        )
    """)

    # Buyurtmalar jadvali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buyurtmalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stol_id INTEGER,
            ofitsiant_id INTEGER,
            sana TEXT DEFAULT (datetime('now', 'localtime')),
            holat TEXT DEFAULT 'ochiq',  -- ochiq, yopiq
            jami_summa REAL DEFAULT 0,
            FOREIGN KEY (stol_id) REFERENCES stollar(id),
            FOREIGN KEY (ofitsiant_id) REFERENCES ofitsiantlar(id)
        )
    """)

    # Buyurtma tafsilotlari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buyurtma_tafsilot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyurtma_id INTEGER,
            menyu_id INTEGER,
            soni INTEGER DEFAULT 1,
            narx REAL,
            bolim TEXT,  -- salatchi, shashlikchi, somsachi
            FOREIGN KEY (buyurtma_id) REFERENCES buyurtmalar(id),
            FOREIGN KEY (menyu_id) REFERENCES menyu(id)
        )
    """)

    conn.commit()

    # Boshlang'ich ma'lumotlar
    cursor.execute("SELECT COUNT(*) FROM stollar")
    if cursor.fetchone()[0] == 0:
        # 10 ta stol
        for i in range(1, 11):
            cursor.execute("INSERT INTO stollar (raqam) VALUES (?)", (i,))

    cursor.execute("SELECT COUNT(*) FROM kategoriyalar")
    if cursor.fetchone()[0] == 0:
        kategoriyalar = [
            ("Salatlar", "salatchi"),
            ("Sovuq taomlar", "salatchi"),
            ("Shashliklar", "shashlikchi"),
            ("Kaboblar", "shashlikchi"),
            ("Go'shtli taomlar", "shashlikchi"),
            ("Somsa", "somsachi"),
            ("Non mahsulotlari", "somsachi"),
            ("Ichimliklar", "salatchi"),
        ]
        cursor.executemany("INSERT INTO kategoriyalar (nomi, bolim) VALUES (?, ?)", kategoriyalar)

    cursor.execute("SELECT COUNT(*) FROM menyu")
    if cursor.fetchone()[0] == 0:
        menyu_items = [
            # Salatchi bo'limi
            ("Sezar salat", 32000, 1, "salatchi"),
            ("Grek salat", 28000, 1, "salatchi"),
            ("Ovoshli salat", 20000, 1, "salatchi"),
            ("Olivye", 25000, 2, "salatchi"),
            ("Achichiq", 18000, 2, "salatchi"),
            # Shashlikchi bo'limi
            ("Qo'y shashlik", 45000, 3, "shashlikchi"),
            ("Tovuq shashlik", 30000, 3, "shashlikchi"),
            ("Mol go'sht shashlik", 42000, 3, "shashlikchi"),
            ("Lyulya kabob", 35000, 4, "shashlikchi"),
            ("Tikka kabob", 38000, 4, "shashlikchi"),
            ("Qozon kabob", 55000, 5, "shashlikchi"),
            # Somsachi bo'limi
            ("Somsa (go'shtli)", 12000, 6, "somsachi"),
            ("Somsa (kartoshkali)", 10000, 6, "somsachi"),
            ("Somsa (to'xumli)", 11000, 6, "somsachi"),
            ("Tandir non", 5000, 7, "somsachi"),
            ("Patir non", 7000, 7, "somsachi"),
            # Ichimliklar
            ("Choy (choynak)", 10000, 8, "salatchi"),
            ("Pepsi 0.5l", 8000, 8, "salatchi"),
            ("Kompot", 12000, 8, "salatchi"),
            ("Mineral suv", 6000, 8, "salatchi"),
        ]
        cursor.executemany(
            "INSERT INTO menyu (nomi, narx, kategoriya_id, bolim) VALUES (?, ?, ?, ?)",
            menyu_items
        )

    cursor.execute("SELECT COUNT(*) FROM ofitsiantlar")
    if cursor.fetchone()[0] == 0:
        ofitsiantlar = [
            ("Sardor", "sardor", "1234"),
            ("Malika", "malika", "1234"),
            ("Bobur", "bobur", "1234"),
        ]
        cursor.executemany(
            "INSERT INTO ofitsiantlar (ism, login, parol) VALUES (?, ?, ?)",
            ofitsiantlar
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Ma'lumotlar bazasi yaratildi!")
