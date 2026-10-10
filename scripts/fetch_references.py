"""Baixa do site da Storopack as fotos reais usadas como referência visual na geração de imagens.

Uso: python scripts/fetch_references.py   (salva em assets/references/)
Rode de novo só se o site trocar as fotos; os arquivos ficam versionados no repositório.
"""

from pathlib import Path

import requests

BASE = "https://www.storopack.com.br/fileadmin/_processed_/"
OUT = Path(__file__).resolve().parents[1] / "assets" / "references"

FILES = {
    "airplus_void_1.jpg": "e/d/csm_PP_AP_Void_100__Recycled_application_0195_1280x580px_ae781a643b.jpg",
    "airplus_void_2.jpg": "2/c/csm_PP_AP_Void_Bio_Home_Compostable_application_9042_1280x580_f7f08a5260.jpg",
    "airplus_cushion_1.jpg": "b/e/csm_PP_AP_Cushion_16P_100___recycled_application_1280x580_Zeichenflaeche_1_035003ac41.jpg",
    "airplus_wrap_1.jpg": "1/f/csm_PP_AP_Wrap_recycle_140d_application_0110_650x295px_afc0072f63.jpg",
    "airplus_void_3.jpg": "a/6/csm_Image-Slider_Void_30__Recycled_XL_1280x580px_711fdeafc3.jpg",
    "paperplus_classic_1.png": "f/9/csm_PP_PP_Classic_application_motive11_1280x580px_617974a22f.png",
    "paperplus_classic_2.png": "7/d/csm_PP_PP_Classic_application_motive6_1280x580px_c482959a95.png",
    "paperplus_shooter_1.jpg": "2/d/csm_PP_PP_Shooter_application_6046_1280x580px_2a1a3fd031.jpg",
    "paperplus_shooter_2.jpg": "a/6/csm_PP_PP_Shooter_application_1939_1280x580px_e6c8b7ba26.jpg",
    "paperplus_track_1.png": "2/2/csm_PP_PP_Track_application_with_coffee_machine_9603_1280x580px_ede14af942.png",
    "paperplus_track_2.png": "5/a/csm_PP_PP_Track_application_with_technical_parts_9606_1280x580px_a703dcf681.png",
    "paperbubble_1.png": "b/d/csm_PP_PB_PAPERbubble_application_0758_1280x580px_16de6ea60b.png",
    "paperbubble_2.png": "7/d/csm_PP_PB_PAPERbubble_application_0761_1280x580px_6f7bc7bf14.png",
    "foamplus_bag_1.png": "a/1/csm_PP_FP_application_motive2_freigest_1280x580px_004c67716b.png",
    "foamplus_bag_2.png": "9/b/csm_PP_FP_Bag_Packer___cushion_application_1280x580px_a1a12af89a.png",
    "foamplus_hand_1.png": "5/3/csm_PP_FP_Hand_Packer2_application_3_1280x580px_281297bfba.png",
    "foamplus_hand_2.png": "e/5/csm_PP_FP_Hand_Packer2_application_1_1280x580px_3d9b58ee24.png",
    "comfort_pack_1.jpg": "3/9/csm_P_PL_Working_Comfort_Comfort_Pack_640x590_45d67322e1.jpg",
    "comfort_erect_1.jpg": "9/2/csm_P_PL_Working_Comfort_Comfort_Erect_640x590_9215c9dc3f.jpg",
    "comfort_close_1.jpg": "9/d/csm_P_PL_Working_Comfort_Comfort_Close_640x590_98c983a5d0.jpg",
    "comfort_protect_1.jpg": "9/3/csm_P_PL_Working_Comfort_Comfort.Protect_640x590_67fa7e6864.jpg",
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, path in FILES.items():
        resp = requests.get(BASE + path, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        resp.raise_for_status()
        (OUT / name).write_bytes(resp.content)
        print("ok", name)
