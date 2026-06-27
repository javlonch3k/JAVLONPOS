# 🍽️ JAVLON POS - Restoran uchun Web dastur

Ofitsiantlar uchun buyurtma qabul qilish tizimi.  
📱 Telefondan ham, 💻 kompyuterdan ham ishlaydi!

## O'rnatish va ishga tushirish

### Talablar:
- Python 3.7+
- Flask

### O'rnatish:
```bash
git clone https://github.com/javlonch3k/JAVLONPOS.git
cd JAVLONPOS
pip install -r requirements.txt
python app.py
```

### Brauzerda ochish:
```
http://localhost:5000
```
yoki telefondan (bir xil WiFi da bo'lsa):
```
http://KOMPYUTER_IP:5000
```

### Kirish ma'lumotlari (test):
| Login   | Parol | Ism     |
|---------|-------|---------|
| sardor  | 1234  | Sardor  |
| malika  | 1234  | Malika  |
| bobur   | 1234  | Bobur   |

## Funksiyalar:
1. ✅ Ofitsiant login/parol bilan kirish
2. ✅ Stollar xaritasi (yashil = bo'sh, qizil = band)
3. ✅ Menyu - kategoriyalar bo'yicha
4. ✅ Buyurtma qilish (real-time)
5. ✅ **Chek chiqarish - bo'limlar bo'yicha:**
   - 🥗 Salatchi bo'limi cheki
   - 🍖 Shashlikchi bo'limi cheki
   - 🥟 Somsachi bo'limi cheki
   - 📋 Umumiy hisob cheki
6. ✅ Hisobni yopish va stolni bo'shatish
7. ✅ Mobil moslashuvchan dizayn (telefon/planshet)

## Bo'limlar:
- **Salatchi** - salatlar, sovuq taomlar, ichimliklar
- **Shashlikchi** - shashliklar, kaboblar, go'shtli taomlar
- **Somsachi** - somsa, non mahsulotlari

## Telefondan foydalanish:
1. Kompyuterda `python app.py` ishga tushiring
2. Kompyuter IP manzilini aniqlang: `ipconfig` (Windows)
3. Telefon brauzerida oching: `http://192.168.x.x:5000`
4. Kompyuter va telefon bir xil WiFi da bo'lishi kerak!
