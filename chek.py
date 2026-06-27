"""
Chek chiqarish moduli - bo'limlar bo'yicha alohida cheklar
"""
from datetime import datetime


def chek_yaratish(buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar, bolim=None):
    """
    Chek matnini yaratadi.
    bolim = None bo'lsa umumiy chek
    bolim = 'salatchi'/'shashlikchi'/'somsachi' bo'lsa bo'lim cheki
    """
    chek_kengligi = 40
    chiziq = "=" * chek_kengligi
    yupqa_chiziq = "-" * chek_kengligi

    sana = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Sarlavha
    if bolim:
        bolim_nomi = bolim.upper()
        sarlavha = f"  [{bolim_nomi}] BO'LIMI CHEKI"
    else:
        sarlavha = "  UMUMIY HISOB"

    chek = f"""
{chiziq}
         RESTORAN POS
{sarlavha}
{chiziq}
  Buyurtma: #{buyurtma_id}
  Stol: {stol_raqam}
  Ofitsiant: {ofitsiant_ism}
  Sana: {sana}
{yupqa_chiziq}
"""

    # Taomlar ro'yxati
    jami = 0
    if bolim:
        items = [t for t in tafsilotlar if t['bolim'] == bolim]
    else:
        items = tafsilotlar

    for item in items:
        nomi = item['nomi']
        soni = item['soni']
        narx = item['narx']
        summa = soni * narx
        jami += summa

        # Formatlash
        chek += f"  {nomi}\n"
        chek += f"    {soni} x {narx:,.0f} = {summa:,.0f} so'm\n"

    chek += f"""
{yupqa_chiziq}
  JAMI: {jami:,.0f} so'm
{chiziq}
"""

    if not bolim:
        chek += "       Rahmat! Yoqimli ishtaha!\n"
        chek += f"{chiziq}\n"

    return chek, jami


def barcha_cheklar(buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar):
    """
    Barcha bo'limlar uchun alohida cheklar yaratadi
    """
    bolimlar = ['salatchi', 'shashlikchi', 'somsachi']
    cheklar = {}

    for bolim in bolimlar:
        items = [t for t in tafsilotlar if t['bolim'] == bolim]
        if items:
            chek_matni, jami = chek_yaratish(
                buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar, bolim
            )
            cheklar[bolim] = {
                'matn': chek_matni,
                'jami': jami
            }

    # Umumiy chek
    umumiy_chek, umumiy_jami = chek_yaratish(
        buyurtma_id, stol_raqam, ofitsiant_ism, tafsilotlar, bolim=None
    )
    cheklar['umumiy'] = {
        'matn': umumiy_chek,
        'jami': umumiy_jami
    }

    return cheklar
