#!/usr/bin/env python3
"""vio_build.py — arma e instala las misiones configuradas de VIO-BECTI(-CW) descritas en tools/vio_catalog.json.

Cada escenario del catálogo dice de qué misión del Workshop sale, qué valores por defecto del lobby cambia
(con tools/vio_config.py), qué nombre y descripción muestra y qué parches lleva. Nunca toca el original.

Uso:
  vio_build.py list                       estado de cada escenario
  vio_build.py [--dry-run] build <id> ... arma e instala (o actualiza) esos escenarios; "all" = todos los posibles
  vio_build.py doc                        reescribe ESCENARIOS.md (catálogo legible) en el proyecto y su copia pública
                                          docs/ESCENARIOS.md + docs/launch/ (sin el usuario del Mac)

Instalar  = carpeta nueva en el mpmissions del perfil, registrada en install_manifest.tsv (undo.sh la borra).
Actualizar = solo si la copia instalada no cambió desde que se registró (misma huella). Se sobrescriben los
archivos distintos, se agregan los nuevos y se actualiza la huella del manifiesto. La carpeta conserva su
nombre, así que la partida guardada de esa misión (clave missionName_worldName) se mantiene.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
CATALOG = os.path.join(HERE, "vio_catalog.json")
MANIFEST = os.path.join(PROJECT, "install_manifest.tsv")
WORKSHOP = os.path.expanduser("~/Library/Application Support/Steam/steamapps/workshop/content/107410")
MPMISSIONS = os.path.expanduser("~/Library/Application Support/com.vpltd.Arma3/GameDocuments/Arma 3/mpmissions")
STAGE_ROOT = os.environ.get("VIO_STAGE_DIR") or os.path.join(PROJECT, "work", "vio_stage")
ENC = dict(encoding="utf-8", errors="surrogateescape", newline="")

sys.path.insert(0, HERE)
from vio_config import find_ci  # noqa: E402

WARDROBE_SQF = """// VIOC_wardrobe.sqf - agregado por tools/vio_build.py (copia configurada, no es del autor de la mision).
// Si el mod "Wardrobe - Outfit System" (Workshop 3352708204) esta cargado, el HQ de tu bando tiene la
// accion "Open Wardrobe" (a menos de 5 m). Hace lo mismo que el modulo "Add Wardrobe" de Zeus del mod.
// Sin el mod no hace nada.
if (!hasInterface) exitWith {};
if !(isClass (configFile >> "CfgPatches" >> "J3FF_Wardrobe")) exitWith {};
waitUntil {sleep 1; !isNull player && {!isNil "CTI_CO_FNC_GetSideHQ"} && {!isNil "Wardrobe_defaultConfigs"}};
while {true} do {
	private _hq = (side group player) call CTI_CO_FNC_GetSideHQ;
	if (!isNil "_hq" && {!isNull _hq} && {alive _hq} && {isNil {_hq getVariable "vioc_wardrobe"}}) then {
		_hq setVariable ["vioc_wardrobe", true];
		_hq setVariable ["_defaultContents", true, true];
		[_hq] spawn J3FF_Wardrobe_fnc_defineAvailableItems;
		[_hq] spawn J3FF_Wardrobe_fnc_addWardrobeAction;
	};
	sleep 10;
};
"""
WARDROBE_INIT = '//--- VIOC: armario de Wardrobe en el HQ (copia configurada; sin el mod no hace nada)'
WARDROBE_CALL = 'if (hasInterface) then {[] execVM "VIOC_wardrobe.sqf"};'

# Armas extra por nación: [clase, rango]. Rango 0, 1, 2... = 1.º, 2.º, 3.º... nivel de equipo que YA usa esa tienda
# (se recorta al último; nunca crea un nivel). Si la tienda empieza más arriba porque comparte bando con otra nación
# (cher_2009, cher_donbas2015), lo agregado se corre con ella.
# Clases de CUP, RHS o vanilla (todas cargan con la línea 1); lo que no existe en el juego se salta.
# Las tiendas de CUP (gear_CUP_US/SOV/UKR) reciben la lista de su nación; las de RHS (gear_RHS_US/SOV, nación "")
# reciben "RHS_WEST" o "RHS_EAST" según el bando, y además cargadores y accesorios para todas sus armas.
# "*" = lista común de armas de guerrilla e irregulares (AK viejos, fusiles de cerrojo, FAL, G3, PKM, RPG-7, escopetas de
# caza...). La reciben las tiendas modernas de GEAR_EXTRA_ALL_NATIONS (EE. UU., Rusia, Ucrania, CDF, ChDKZ y las dos de
# RHS), no las de 1985 ni Vietnam. Una clase va en su nación o en "*", no en las dos, si esa nación recibe "*" (lo revisa
# check_gear_lists). Con gear_unlock_all el rango ya no oculta nada: solo cambia el precio.
GEAR_EXTRA = {
    "US": [("CUP_arifle_M16A2", 0), ("CUP_arifle_M16A2_GL", 0), ("CUP_arifle_M16A4_Base", 0), ("CUP_arifle_M16A4_GL", 0),
           ("CUP_arifle_M16A4_Grip", 0), ("CUP_arifle_M4A1", 0), ("CUP_hgun_Glock17_blk", 0), ("CUP_hgun_M17_Black", 0),
           ("CUP_hgun_Colt1911", 0), ("CUP_launch_M72A6", 0), ("CUP_glaunch_M79", 0),
           ("CUP_arifle_mk18_black", 1), ("CUP_arifle_mk18_m203_black", 1), ("CUP_arifle_HK416_Black", 1), ("CUP_arifle_HK416_Desert", 1),
           ("CUP_arifle_HK416_Wood", 1), ("CUP_arifle_HK416_M203_Black", 1), ("CUP_arifle_HK416_CQB_Black", 1),
           ("CUP_arifle_HK416_CQB_M203_Black", 1), ("CUP_arifle_HK_M27", 1), ("CUP_arifle_HK_M27_VFG", 1), ("CUP_lmg_M60E4", 1),
           ("CUP_lmg_Mk48", 1), ("CUP_lmg_Mk48_des", 1), ("CUP_lmg_Mk48_wdl", 1), ("CUP_srifle_Mk12SPR", 1), ("CUP_glaunch_M32", 1),
           ("CUP_hgun_Mk23", 1), ("CUP_smg_MP7", 1), ("CUP_smg_p90_black", 1),
           ("CUP_arifle_Mk16_CQC", 2), ("CUP_arifle_Mk16_CQC_black", 2), ("CUP_arifle_Mk16_STD", 2), ("CUP_arifle_Mk16_STD_black", 2),
           ("CUP_arifle_Mk16_STD_EGLM", 2), ("CUP_arifle_Mk17_CQC", 2), ("CUP_arifle_Mk17_STD", 2), ("CUP_arifle_Mk17_STD_black", 2),
           ("CUP_arifle_Mk17_STD_EGLM", 2), ("CUP_arifle_Mk20", 2), ("CUP_srifle_M24_wdl", 2), ("CUP_srifle_M24_blk", 2),
           ("CUP_srifle_M2010_blk", 2), ("CUP_srifle_M2010_dsrt", 2), ("CUP_srifle_M2010_wdl", 2), ("CUP_srifle_Mk18_blk", 2),
           ("CUP_srifle_Mk18_des", 2), ("CUP_srifle_RSASS_Black", 2), ("CUP_srifle_RSASS_Sand", 2),
           # Guerra Fría como en Reforger (1989): M16A1, M60, M3A1, M590A1, Colt 727, M21, M47 Dragon
           ("CUP_arifle_M16A1", 0), ("CUP_arifle_M16A1GL", 0), ("CUP_lmg_M60", 1), ("CUP_smg_M3A1", 0),
           ("rhs_weap_M590_8RD", 0), ("rhs_weap_M590_5RD", 0), ("CUP_arifle_Colt727", 1), ("CUP_arifle_Colt727_M203", 1),
           ("CUP_srifle_M21", 1), ("CUP_launch_M47", 2),
           # Modernas: M4A1 con M320, M320, Mk13, M4 SBR, M14 EBR-RI, HK417, Mk 11, M40A5, M24 desierto
           ("rhs_weap_m4a1_m320", 1), ("rhs_weap_M320", 0), ("CUP_glaunch_Mk13", 1), ("CUP_arifle_SBR_od", 1),
           ("rhs_weap_m14ebrri", 1), ("CUP_arifle_HK417_20", 2), ("CUP_arifle_HK417_12", 2), ("rhs_weap_sr25", 2),
           ("rhs_weap_m40a5", 2), ("CUP_srifle_M24_des", 2),
           # Desechables de RHS (se venden con su cohete): M72A7, AT4 HEDP y HP
           ("rhs_weap_m72a7", 0), ("rhs_weap_M136_hedp", 1), ("rhs_weap_M136_hp", 1),
           # Contra drones: la M320 (lugar de pistola, cartucho de perdigones M576) va arriba en el nivel 0; la M1014 ya está
           # en la tienda del autor (el Promet SG vanilla de 2035 se quitó: política V6.1, parche tropical_gear)
           # Británicas (mod "[TRF] United Kingdom Armed Forces", Workshop 3678757032, en la carpeta @nue de la línea
           # 1N; sin el mod se saltan): fusil L85A3 (base HK416 de RHS: cargadores STANAG y accesorios entran solos) con
           # AFG, GripPod o lanzagranadas L123A2, y la ametralladora L7A2 (base M240B de RHS, cintas de 7.62), como el
           # M240 en el 2.º nivel
           ("Scotts_L85A3", 0), ("Scotts_L85A3_A", 0), ("Scotts_L85A3_AFG", 1), ("Scotts_L85A3_AFG_A", 1),
           ("Scotts_L85A3_GP", 1), ("Scotts_L85A3_GP_A", 1), ("Scotts_L85A3_UGL", 1), ("Scotts_L85A3_UGL_A", 1),
           ("Scotts_L85A3_UGL_D", 1), ("UKAF_L7A2", 1),
           # Aliados de la OTAN (misiones "OTAN"; todas de CUP): británicas L85A2 (con y sin L123A2), L86A2 LSW, L110A2,
           # L7A2, L129A1 y L115A3; alemanas G36, G36K, G36C, G36A3, G36 con AG36, MG36, MG3, G22 y Panzerfaust 3; FAMAS F1
           # francés; AUG A1 austríaco; checas CZ 805 BREN A1/A2/G1, BREN 2, CZ 807, CZ 750, CZ 75 DUTY y PHANTOM y Scorpion
           # EVO 3; Minimi y MAG belgas; NLAW
           ("CUP_arifle_L85A2", 0), ("CUP_arifle_L85A2_GL", 1), ("CUP_arifle_L86A2", 1), ("CUP_lmg_L110A1", 1),
           ("CUP_lmg_L7A2", 1), ("CUP_srifle_L129A1", 2), ("CUP_srifle_AWM_wdl", 2), ("CUP_srifle_AWM_des", 2),
           ("CUP_launch_NLAW", 1), ("CUP_arifle_G36A", 0), ("CUP_arifle_G36K", 0), ("CUP_arifle_G36C", 1),
           ("CUP_arifle_G36A3", 1), ("CUP_arifle_AG36", 1), ("CUP_arifle_MG36", 1), ("CUP_lmg_MG3", 1),
           ("CUP_srifle_G22_wdl", 2), ("CUP_launch_PzF3", 1), ("CUP_Famas_F1", 0), ("CUP_arifle_AUG_A1", 0),
           ("CUP_arifle_CZ805_A1", 1), ("CUP_arifle_CZ805_A2", 1), ("CUP_arifle_CZ805_GL", 1), ("CUP_CZ_BREN2_556_11", 1),
           ("CUP_CZ_BREN2_762_14", 2), ("CUP_srifle_CZ750", 2), ("CUP_hgun_Duty", 0), ("CUP_hgun_Phantom", 0),
           ("CUP_smg_EVO", 1), ("CUP_lmg_minimi", 1), ("CUP_lmg_FNMAG", 1)],
    # AKM, AKMS, PKM, RPK, SKS, Mosin y RPG-18 llegan con la lista común "*"
    "RU": [("CUP_arifle_AK74M", 0), ("CUP_arifle_AK74M_GL", 0), ("CUP_arifle_AKS74", 0), ("CUP_arifle_AKS74U", 0),
           ("CUP_hgun_PMM", 0), ("CUP_smg_bizon", 0), ("CUP_smg_vityaz", 0), ("CUP_launch_RShG2", 0),
           ("CUP_arifle_AK74M_railed", 1), ("CUP_arifle_AK74M_top_rail", 1), ("CUP_arifle_AK74M_GL_railed", 1), ("CUP_arifle_AK105", 1),
           ("CUP_arifle_AK105_railed", 1), ("CUP_arifle_AK104", 1), ("CUP_arifle_AK103", 1), ("CUP_arifle_AK103_GL", 1),
           ("CUP_arifle_AKS74U_railed", 1), ("CUP_lmg_PKMN", 1), ("CUP_lmg_PKM_top_rail", 1),
           ("CUP_sgun_Saiga12K", 0), ("CUP_glaunch_6G30", 1),
           ("CUP_arifle_AK15_AFG_black", 2), ("CUP_arifle_AK15_GP34_black", 2), ("CUP_srifle_VSSVintorez", 2),
           ("CUP_srifle_VSSVintorez_top_rail", 2), ("CUP_arifle_SR3M_Vikhr", 2), ("CUP_arifle_SR3M_Vikhr_top_rail", 2),
           ("CUP_arifle_OTS14_GROZA", 2), ("CUP_arifle_OTS14_GROZA_GL", 2),
           ("CUP_srifle_ksvk", 3),
           # Guerra Fría como en Reforger (1989): AK-74/AKS-74 (con y sin GP-25), AK-74N, AKM con GP-25, Strela-2 (AKM/AKMS,
           # SKS y RPK, en "*")
           ("CUP_arifle_AK74_Early", 0), ("CUP_arifle_AKS74_Early", 0), ("CUP_arifle_AK74_GL_Early", 0),
           ("CUP_arifle_AKS74_GL_Early", 0), ("CUP_arifle_AK74", 0), ("CUP_arifle_AK74_GL", 0), ("CUP_arifle_AKM_GL_Early", 0),
           ("CUP_launch_9K32Strela", 2),
           # Modernas: MP-443, PP-2000, SVDS, 6P53, SVDM, T-5000, AK-15, AK-107 (el Mosin de los movilizados
           # de 2022, en "*")
           ("rhs_weap_pya", 0), ("rhs_weap_pp2000", 1), ("rhs_weap_svds", 1),
           # (tropical_gear, politica V6.1: sin AKU-12/RPK-12 vanilla de 2035; quedan AK-12/AK-15 de CUP y RHS)
           ("rhs_weap_6p53", 2), ("rhs_weap_svdp", 2), ("rhs_weap_t5000", 2),
           ("CUP_arifle_AK15_black", 2), ("CUP_arifle_AK107", 2),
           # Contra drones: Saiga 12K (arriba, nivel 0) y Saiga con riel
           ("CUP_sgun_Saiga12K_top_rail", 0)],
    # AKM, AKMS, PKM, RPK, SKS, Sa vz. 58, G3, UK vz. 59, CZ 75, Browning HP, RPG-18 y RPG-75 llegan con la lista común "*"
    "UA": [("CUP_arifle_Fort221", 0), ("CUP_arifle_Fort222", 0), ("CUP_launch_M72A6", 0), ("CUP_hgun_Glock17_blk", 0),
           ("CUP_arifle_Fort224", 1), ("CUP_arifle_Fort224_Grippod", 1), ("CUP_arifle_M4A1_MOE_black", 1), ("CUP_arifle_M16A4_Base", 1),
           ("CUP_arifle_AK74M_railed", 1), ("CUP_arifle_AKS74U_railed", 1), ("CUP_lmg_PKM_top_rail", 1), ("CUP_lmg_minimi_railed", 1),
           ("CUP_lmg_MG3_rail", 1), ("CUP_lmg_FNMAG_RIS_modern", 1), ("CUP_launch_M136", 1), ("CUP_launch_PzF3", 1), ("CUP_launch_NLAW", 1),
           ("CUP_launch_Javelin", 2), ("CUP_launch_FIM92Stinger", 2), ("CUP_launch_MAAWS", 2), ("CUP_srifle_M24_blk", 2),
           ("CUP_srifle_M107_Woodland", 3),
           # Armas soviéticas que Ucrania sigue usando y donaciones de la OTAN (el autor comentó los AK-74/AKS-74 en
           # gear_CUP_UKR; se devuelven porque son el fusil más común del ejército ucraniano)
           ("CUP_arifle_AK74", 0), ("CUP_arifle_AKS74", 0), ("CUP_arifle_AK74_GL", 1), ("CUP_arifle_AKS74_GL_Early", 1),
           ("CUP_arifle_AKM_GL_Early", 1), ("CUP_Famas_F1", 1), ("CUP_launch_9K32Strela", 2),
           # Modernas (ayuda occidental y fuerzas especiales, como la facción AFU de CUP)
           ("CUP_CZ_BREN2_556_11", 1), ("CUP_CZ_BREN2_556_14", 1), ("CUP_CZ_BREN2_556_8", 1), ("CUP_CZ_BREN2_556_14_GL", 1),
           ("CUP_arifle_M4A1_camo", 1), ("CUP_arifle_M4A1_MOE_short_wdl", 1), ("CUP_arifle_M4A1_SOMMOD_green", 1),
           ("CUP_arifle_ACRC_wdl_556", 1), ("CUP_arifle_ACR_blk_556", 1), ("CUP_lmg_m249_pip1", 1), ("CUP_lmg_M240_B", 1),
           ("CUP_hgun_M17_Black", 1), ("CUP_hgun_Phantom", 1), ("CUP_smg_EVO", 1), ("CUP_smg_MP5A5", 1),
           ("CUP_arifle_Mk16_STD_woodland", 2), ("CUP_arifle_Mk16_STD_EGLM", 2), ("CUP_arifle_Mk17_STD_EGLM_woodland", 2),
           ("CUP_arifle_HK416_Wood", 2), ("CUP_arifle_HK416_CQB_M203_Wood", 2), ("CUP_arifle_HK417_20", 2),
           ("CUP_srifle_RSASS_WDLNet", 2), ("CUP_srifle_M2010_wdl", 2), ("CUP_hgun_Mk23", 2),
           # Contra drones (la tienda del autor no trae escopetas): Saiga 12K, M1014 y Promet SG
           ("CUP_sgun_Saiga12K", 0), ("CUP_sgun_M1014", 0),
           # Lanzagranadas (la tienda no tenía ninguno): M79, M320, RG-6 y M32; M14 de los países bálticos; RShG-2 y VSS
           # capturados
           ("CUP_glaunch_M79", 0), ("rhs_weap_M320", 0), ("CUP_glaunch_6G30", 1), ("CUP_glaunch_M32", 1),
           ("CUP_srifle_M14", 1), ("CUP_launch_RShG2", 1), ("CUP_srifle_VSSVintorez", 2),
           # De RHS (Ucrania no tiene tienda de RHS: Init_Client.sqf solo la arma para EE. UU. o la CDF): AK-74M, AKS-74N,
           # AKS-74U, PKM, RPK-74M, SVDM, RPG-7, RPG-26 y PM soviéticos; M4A1 Block II (y M203), M249 PIP, M240B, Mk 17,
           # M72A7, AT4, Carl Gustaf M3, Javelin, Stinger, M2010 y M107 donados. Los desechables se venden con su cohete
           ("rhs_weap_ak74m", 0), ("rhs_weap_aks74n", 0), ("rhs_weap_aks74u", 0), ("rhs_weap_pkm", 0), ("rhs_weap_rpg7", 0),
           ("rhs_weap_rpg26", 0), ("rhs_weap_makarov_pm", 0), ("rhs_weap_m72a7", 0), ("rhs_weap_ak74m_gp25", 1),
           ("rhs_weap_rpk74m", 1), ("rhs_weap_svdp", 1), ("rhs_weap_m4a1_blockII", 1), ("rhs_weap_m4a1_blockII_M203", 1),
           ("rhs_weap_m249_pip", 1), ("rhs_weap_m240B", 1), ("rhs_weap_M136_hedp", 1), ("rhs_weap_mk17_STD", 2),
           ("rhs_weap_maaws", 2), ("rhs_weap_fgm148", 2), ("rhs_weap_fim92", 2), ("rhs_weap_XM2010", 2), ("rhs_weap_M107", 3)],
    # Fuerzas de Defensa de Chernarus (tienda gear_RHS_CDF: Georgia 2008 y Chernarus 2009; antes sin gancho): fusiles de
    # EE. UU. (M16A2, M4A1, M4A3, M16A4), SVD, SVDM y M24, lanzagranadas M79 y RG-6, RPG-26, RShG-2, M72, Strela-2,
    # Saiga 12K, M590 y MP5. La tienda de la ChDKZ (gear_RHS_ChDKZ, guerrilla) no tiene lista propia: recibe "*"
    "CDF": [("CUP_arifle_M16A2", 0), ("CUP_arifle_M4A1", 0), ("CUP_glaunch_M79", 0), ("rhs_weap_rpg26", 0),
            ("CUP_launch_M72A6", 0), ("CUP_sgun_Saiga12K", 0), ("rhs_weap_M590_8RD", 0), ("CUP_arifle_M4A3_black", 1),
            ("CUP_arifle_M16A4_Base", 1), ("CUP_srifle_SVD", 1), ("CUP_glaunch_6G30", 1), ("CUP_launch_RShG2", 1),
            ("CUP_launch_9K32Strela", 1), ("CUP_smg_MP5A5", 1), ("rhs_weap_svdp", 2), ("CUP_srifle_M24_wdl", 2)],
    # Lista común (ver arriba): armas de guerrilla, milicias y movilizados; todas existen con alcance 2 en la línea 6
    # (CUP, RHS GREF y vanilla), incluidas las de la guerrilla de los pueblos (CUP_I_GUE_*: AK, AKS, AKMN, CZ 550, PKM,
    # RPG-7, RPG-18, Makarov). Fusiles AK, AKN, AKS, AKM, AKMN/AKMSN, M70 y M92 yugoslavos, Sa vz. 58, FAL, G3,
    # Mosin, Lee-Enfield (sin StG 44, M1 Garand ni Kar 98k: política V6.1, parche tropical_gear), M14 "Classic", Saiga MK03, Colt Sporter, CZ 550 y Remington 700 de caza;
    # ametralladoras PKM, RPK y UK vz. 59; Uzi, Micro Uzi, TEC-9, Škorpion, Makarov, TT-33, CZ 75, Browning HP y
    # revólver Taurus; escopetas CZ 584, de fabricación casera, IZh-18 y Kozlice (y recortada); RPG-7, RPG-18 y RPG-75
    "*": [("CUP_arifle_AK47_Early", 0), ("CUP_arifle_AK47", 0), ("CUP_arifle_AKS", 0), ("CUP_arifle_AKM", 0),
          ("CUP_arifle_AKMS", 0), ("CUP_arifle_AKM_Early", 0), ("CUP_arifle_AKMS_Early", 0), ("CUP_SKS", 0),
          ("rhs_weap_m70b1", 0), ("rhs_weap_m70ab2", 0), ("rhs_weap_m92", 0), ("CUP_arifle_Sa58V", 0),
          ("CUP_arifle_Sa58P", 0), ("CUP_arifle_FNFAL5060", 0), ("CUP_arifle_FNFAL5061", 0), ("CUP_arifle_G3A3_ris", 0),
          # (tropical_gear, politica V6.1: fuera MP44, M1 Garand, Kar98k y MG42 de la 2a Guerra Mundial)
          ("CUP_srifle_Mosin_Nagant", 0),
          ("CUP_srifle_LeeEnfield", 0), ("srifle_DMR_06_hunter_F", 0), ("CUP_arifle_SAIGA_MK03", 0), ("CUP_arifle_Colt_Sporter", 0),
          ("CUP_srifle_CZ550", 0), ("CUP_srifle_Remington700", 0), ("CUP_lmg_PKM", 1), ("CUP_arifle_RPK74", 1),
          ("CUP_lmg_UK59", 1), ("CUP_smg_UZI", 0), ("CUP_hgun_MicroUzi", 0), ("CUP_hgun_TEC9", 0),
          ("CUP_hgun_SA61", 0), ("CUP_hgun_Makarov", 0), ("CUP_hgun_TT", 0), ("CUP_hgun_CZ75", 0),
          ("CUP_hgun_Browning_HP", 0), ("CUP_hgun_TaurusTracker455", 0), ("CUP_sgun_CZ584", 0), ("CUP_sgun_slamfire", 0),
          ("rhs_weap_Izh18", 0), ("sgun_HunterShotgun_01_F", 0), ("sgun_HunterShotgun_01_sawedoff_F", 0),
          ("CUP_launch_RPG7V", 0), ("CUP_launch_RPG18", 0), ("rhs_weap_rpg75", 0)],
    # Tiendas de RHS (nación ""), por bando. Las armas de RHS ya están; escopetas contra drones (la M590 del autor está
    # en el nivel 1 y Rusia no tiene ninguna) y, en el Oeste, las británicas de UKAF. CUP carga con la línea 1 aunque la
    # misión tenga "CUP Support" apagado.
    "RHS_WEST": [# (tropical_gear: sin Promet SG vanilla de 2035)
                 # Británicas de UKAF (las mismas que en "US"; heredan de RHS, así que también entran sus cargadores y
                 # accesorios)
                 ("Scotts_L85A3", 0), ("Scotts_L85A3_A", 0), ("Scotts_L85A3_AFG", 1), ("Scotts_L85A3_AFG_A", 1),
                 ("Scotts_L85A3_GP", 1), ("Scotts_L85A3_GP_A", 1), ("Scotts_L85A3_UGL", 1), ("Scotts_L85A3_UGL_A", 1),
                 ("Scotts_L85A3_UGL_D", 1), ("UKAF_L7A2", 1)],
    "RHS_EAST": [("CUP_sgun_Saiga12K", 0), ("CUP_sgun_Saiga12K_top_rail", 0)],
    # Global Mobilization, Bundeswehr 1985 (tienda gear_GM_BW): armas OTAN de los 80 de CUP que el DLC no trae
    # (G3 y MG3 ya están en el DLC). M249E1 es de 1984.
    "BW": [("CUP_arifle_M16A1", 0), ("CUP_arifle_M16A1GL", 0), ("CUP_arifle_M16A2", 0), ("CUP_arifle_M16A2_GL", 0),
           ("CUP_arifle_FNFAL5060", 0), ("CUP_srifle_M14", 0), ("CUP_srifle_M21", 0), ("CUP_lmg_M60", 0),
           ("CUP_lmg_M249_E1", 0), ("CUP_smg_MP5A5", 0), ("CUP_smg_UZI", 0), ("CUP_smg_M3A1", 0), ("CUP_hgun_Colt1911", 0),
           ("CUP_hgun_M9", 0), ("CUP_hgun_Browning_HP", 0), ("CUP_glaunch_M79", 0), ("CUP_launch_M72A6", 0),
           ("CUP_launch_M47", 0), ("CUP_launch_FIM92Stinger", 0)],
    # Global Mobilization, Ejército de Alemania Oriental 1985 (gear_GM_NVA): armas del Pacto de Varsovia de CUP
    # (soviéticas y checoslovacas).
    "NVA": [("CUP_arifle_AK74_Early", 0), ("CUP_arifle_AKS74_Early", 0), ("CUP_arifle_AK74_GL_Early", 0),
            ("CUP_arifle_AKS74U", 0), ("CUP_arifle_AKM_Early", 0), ("CUP_arifle_AKMS_Early", 0), ("CUP_arifle_AKM_GL_Early", 0),
            ("CUP_arifle_RPK74_45", 0), ("CUP_arifle_RPK74", 0), ("CUP_lmg_PKM", 0), ("CUP_srifle_SVD", 0), ("CUP_SKS", 0),
            ("CUP_arifle_Sa58V", 0), ("CUP_arifle_Sa58P", 0), ("CUP_hgun_SA61", 0), ("CUP_hgun_Makarov", 0), ("CUP_hgun_TT", 0),
            ("CUP_launch_RPG7V", 0), ("CUP_launch_RPG18", 0), ("CUP_launch_9K32Strela", 0)],
    # S.O.G. Prairie Fire, EE.UU. 1968 (gear_US_SOG) y Ejército de Vietnam del Norte (gear_NVA_SOG): pocas, porque el DLC
    # ya trae casi todo lo de la época.
    "USSOG": [("CUP_arifle_M16A1", 0), ("CUP_srifle_M14", 0), ("CUP_srifle_M21", 0), ("CUP_lmg_M60", 0), ("CUP_glaunch_M79", 0),
              ("CUP_smg_M3A1", 0), ("CUP_hgun_Colt1911", 0), ("CUP_hgun_Browning_HP", 0), ("CUP_launch_M72A6", 0)],
    "PAVN": [("CUP_arifle_AK47_Early", 0), ("CUP_arifle_AKM_Early", 0), ("CUP_arifle_AKMS_Early", 0), ("CUP_SKS", 0),
             ("CUP_srifle_Mosin_Nagant", 0), ("CUP_hgun_TT", 0), ("CUP_hgun_Makarov", 0), ("CUP_launch_RPG7V", 0)],
}
# Ropa extra por nación: (clase, rango[, multiplicador]). Rango como en GEAR_EXTRA (el autor pone casi toda su ropa en el
# primer nivel de su tienda). Sin multiplicador, el precio sale como lo pone el autor según la configuración
# del objeto: [CTI_ECONOMY_PRIZE_EQUIPMENT, nivel, x] con uniforme x1, casco x1, gorra x0.5, chaleco blindado (8+) x3,
# correaje x2, mochila x2 y gafas x0.5; visor nocturno [CTI_ECONOMY_PRIZE_WEAPONS, nivel, 2].
# Tiendas: gear_CUP_US y gear_RHS_US = "US", gear_CUP_SOV y gear_RHS_SOV = "RU", gear_CUP_UKR = "UA"; "*" (guerrilla tipo
# FIA) se suma a todas. Un uniforme solo entra si el bando de la tienda puede vestirlo (modelSides de su uniformClass).
# Una clase va en su nación o en "*", no en las dos (lo revisa check_gear_lists); entre naciones del mismo bando
# (OTAN + Ucrania) vale la primera tienda. Clases revisadas contra la configuración de la línea 1
# (work/vio_gear/curated_clothing.json; lo que se agrega de verdad, en work/vio_gear/added_items_report.json).
GEAR_EXTRA_CLOTHING = {
    "US": [
        # EE. UU. Guerra Fría (1965-1989; Reforger es 1989): BDU M81/OD y ERDL, cascos PASGT y M1, gorras M81 y OG-107,
        # chaleco PASGT, mochilas ALICE (carga 300-320: x3 como las grandes de Gear_Basic), PVS-7; correaje ALICE en "*"
        ("CUP_U_B_BDUv2_M81_US", 0), ("CUP_U_B_BDUv2_roll_M81_US", 0), ("CUP_U_B_BDUv2_roll2_M81_US", 0),
        ("CUP_U_B_BDUv2_gloves_M81_US", 0), ("CUP_U_B_BDUv2_roll_gloves_M81_US", 0), ("CUP_U_B_BDUv2_dirty_M81_US", 0),
        ("CUP_U_B_BDUv2_roll_dirty_M81_US", 0), ("CUP_U_B_BDUv2_roll2_dirty_M81_US", 0), ("CUP_U_B_BDUv2_M81", 0),
        ("CUP_U_B_BDUv2_roll_M81", 0), ("CUP_U_B_BDUv2_OD_US", 0), ("CUP_U_B_BDUv2_roll_OD_US", 0), ("rhs_uniform_bdu_erdl", 0),
        ("CUP_U_B_BDUv2_ERDL_lowland", 0), ("CUP_H_PASGTv2_WDL", 0), ("CUP_H_PASGTv2_WDL_CF", 0), ("CUP_H_PASGTv2_WDL_GG", 0),
        ("CUP_H_PASGTv2_NVG_WDL", 0), ("CUP_H_PASGTv2_OD", 0), ("rhsgref_helmet_pasgt_woodland", 0),
        ("rhsgref_helmet_pasgt_olive", 0), ("CUP_H_USArmy_Helmet_M1_plain_M81", 0), ("CUP_H_USArmy_Helmet_M1_m81", 0),
        ("CUP_H_USArmy_Helmet_M1_plain_Olive", 0), ("CUP_H_US_patrol_cap_WDL", 0), ("CUP_H_US_patrol_cap_OD", 0),
        ("CUP_H_USA_Boonie_wdl", 0), ("rhs_Booniehat_m81", 0), ("CUP_H_USA_Cap_M81", 0), ("rhsgref_hat_M1951", 0),
        ("CUP_H_CVC", 0), ("CUP_H_SPH4", 0), ("CUP_V_B_PASGT", 0), ("CUP_V_B_PASGT_no_bags", 0), ("CUP_V_B_PASGT_OD", 0),
        ("CUP_V_B_PASGT_no_bags_OD", 0), ("CUP_B_AlicePack_OD", 0, 3.0), ("CUP_B_AlicePack_Bedroll", 0, 3.0),
        ("rhsgref_wdl_alicepack", 0, 3.0), ("CUP_NVG_PVS7", 0),
        # 1991-2003: BDU de desierto (6 colores) y DCU, PASGT y chalecos de desierto, Interceptor DCU
        ("CUP_U_B_BDUv2_desert_US", 0), ("CUP_U_B_BDUv2_roll_desert_US", 0), ("CUP_U_B_BDUv2_DCU_US", 0),
        ("CUP_U_B_BDUv2_roll_DCU_US", 0), ("CUP_H_PASGTv2_desert", 0), ("CUP_H_PASGTv2_DCU", 0),
        ("CUP_H_US_patrol_cap_desert", 0), ("CUP_H_US_patrol_cap_DCU", 0), ("CUP_V_B_PASGT_desert", 0),
        ("CUP_V_B_PASGT_no_bags_desert", 0), ("CUP_V_B_Interceptor_Rifleman_DCU", 0),
        # Moderno: RHS ACU/OCP (con parches de división), FROG y G3; CUP Crye; cascos ACH, Ops-Core, LWH, ECH y MICH; SPCS,
        # MBAV, plateframe, SPC, CPC/JPC y MTV; mochilas Eagle/Falcon; PVS-14/15 y GPNVG; gafas y shemaghs
        ("rhs_uniform_acu_ocp", 0), ("rhs_uniform_acu_oefcp", 0), ("rhs_uniform_acu_ucp", 0), ("rhs_uniform_cu_ocp", 0),
        ("rhs_uniform_cu_ocp_82nd", 0), ("rhs_uniform_cu_ocp_101st", 0), ("rhs_uniform_cu_ocp_10th", 0),
        ("rhs_uniform_cu_ocp_1stcav", 0), ("rhs_uniform_cu_ucp", 0), ("rhs_uniform_FROG01_wd", 0), ("rhs_uniform_FROG01_d", 0),
        ("rhs_uniform_g3_mc", 0), ("rhs_uniform_g3_rgr", 0), ("rhs_uniform_g3_m81", 0), ("rhs_uniform_g3_tan", 0),
        ("rhs_uniform_g3_blk", 0), ("CUP_U_CRYE_G3C_MC_US", 0), ("CUP_U_CRYE_G3C_M81_US", 0), ("CUP_U_CRYE_G3C_RGR_MC_US", 0),
        ("CUP_U_CRYE_RGR_US_Full", 0), ("CUP_U_CRYE_RGR_US_Roll", 0), ("CUP_U_CRYE_TAN_US_Full", 0),
        ("CUP_U_CRYE_TAN_US_Roll", 0), ("CUP_U_CRYE_G3C_Tan_MC_US", 0), ("CUP_U_CRYE_V1_Full", 0), ("CUP_U_CRYE_V1_Roll", 0),
        ("rhsusf_ach_helmet_ocp", 0), ("rhsusf_ach_helmet_headset_ocp", 0), ("rhsusf_ach_helmet_ESS_ocp", 0),
        ("rhsusf_ach_helmet_headset_ess_ocp", 0), ("rhsusf_ach_helmet_ucp", 0), ("rhsusf_ach_helmet_headset_ucp", 0),
        ("rhsusf_opscore_mc_cover", 0), ("rhsusf_opscore_mc_cover_pelt", 0), ("rhsusf_opscore_rg_cover", 0),
        ("rhsusf_opscore_rg_cover_pelt", 0), ("rhsusf_opscore_coy_cover_pelt", 0), ("rhsusf_lwh_helmet_marpatwd", 0),
        ("rhsusf_lwh_helmet_marpatd", 0), ("rhsusf_mich_helmet_marpatwd", 0), ("rhsusf_patrolcap_ocp", 0),
        ("rhsusf_patrolcap_ucp", 0), ("rhs_Booniehat_ocp", 0), ("rhsusf_bowman_cap", 0), ("CUP_H_OpsCore_Covered_MCAM_US", 0),
        ("CUP_H_OpsCore_Spray_US", 0), ("CUP_H_USArmy_Boonie_OCP", 0), ("CUP_H_USArmy_Boonie_hs_OCP", 0),
        ("CUP_H_US_patrol_cap_OCP", 0), ("CUP_H_USA_Cap_MCAM", 0), ("CUP_H_USArmy_Helmet_ECH1_Green", 0),
        ("CUP_H_USArmy_Helmet_ECH2_Sand", 0),
        ("CUP_H_OpsCore_Covered_MCAM_US_SF", 0), ("CUP_H_US_patrol_cap_OEFCP", 0), ("CUP_H_US_patrol_cap_UCP", 0),
        ("rhsusf_spcs_ocp_rifleman", 0), ("rhsusf_spcs_ocp_teamleader", 0), ("rhsusf_spcs_ocp_squadleader", 0),
        ("rhsusf_spcs_ocp_machinegunner", 0), ("rhsusf_spcs_ocp_medic", 0), ("rhsusf_spcs_ocp_grenadier", 0),
        ("rhsusf_spcs_ocp_sniper", 0), ("rhsusf_spcs_ucp_rifleman", 0), ("rhsusf_mbav_rifleman", 0), ("rhsusf_mbav_light", 0),
        ("rhsusf_mbav_mg", 0), ("rhsusf_plateframe_rifleman", 0), ("rhsusf_plateframe_teamleader", 0),
        ("rhsusf_plateframe_machinegunner", 0), ("rhsusf_spc_light", 0), ("rhsusf_spc_mg", 0), ("CUP_V_CPC_light_mc", 0),
        ("CUP_V_CPC_tl_mc", 0), ("CUP_V_CPC_weapons_mc", 0),
        ("CUP_V_CPC_medical_mc", 0), ("CUP_V_JPC_tl_mc", 0), ("CUP_V_JPC_weapons_rngr", 0), ("CUP_V_CPC_tlbelt_mc", 0),
        ("CUP_V_CPC_weaponsbelt_mc", 0), ("CUP_V_CPC_medicalbelt_mc", 0), ("CUP_V_B_RRV_DA1_CB", 0), ("CUP_V_B_RRV_TL_CB", 0),
        ("CUP_V_B_MTV", 0), ("CUP_V_B_MTV_Patrol", 0), ("CUP_V_B_MTV_TL", 0), ("CUP_V_B_MTV_MG", 0),
        ("CUP_V_B_Interceptor_Rifleman_Coyote", 0), ("rhsusf_assault_eagleaiii_ocp", 0), ("rhsusf_assault_eagleaiii_ucp", 0),
        ("rhsusf_assault_eagleaiii_coy", 0), ("rhsusf_falconii", 0), ("rhsusf_falconii_coy", 0), ("rhsusf_falconii_mc", 0),
        ("CUP_B_MedicPack_ACU", 0), ("B_RadioBag_01_wdl_F", 0, 3.0), ("B_RadioBag_01_mtp_F", 0, 3.0), ("rhsusf_ANPVS_14", 0),
        ("rhsusf_ANPVS_15", 0), ("CUP_NVG_PVS15_black", 0), ("CUP_NVG_PVS15_tan", 0), ("CUP_NVG_GPNVG_black", 1),
        ("CUP_NVG_GPNVG_tan", 1), ("rhs_ess_black", 0), ("rhsusf_oakley_goggles_blk", 0), ("rhsusf_oakley_goggles_clr", 0),
        ("rhs_googles_black", 0), ("rhs_googles_clear", 0), ("rhsusf_shemagh_od", 0), ("rhsusf_shemagh_tan", 0),
        ("rhsusf_shemagh_gogg_od", 0), ("rhsusf_shemagh_gogg_tan", 0), ("CUP_G_ESS_BLK", 0), ("CUP_G_ESS_CBR", 0),
        ("CUP_G_ESS_KHK", 0), ("CUP_G_ESS_RGR", 0), ("CUP_G_Oakleys_Clr", 0), ("CUP_G_Oakleys_Drk", 0),
        # Aspecto guerrilla (tipo FIA) que en la tienda rusa repetiría nombre
        ("rhsgref_chicom", 0), ("H_Watchcap_blk", 0, 0.25),
        # Británico moderno (mod "[TRF] United Kingdom Armed Forces", Workshop 3678757032, en la carpeta @nue de la
        # línea 1N; sin el mod se salta): uniformes MTP CS95 y PCS (sin insignia de regimiento); chalecos STV Virtus y
        # C2R CBAV (blindaje 24, cerca del tope de la tienda, 28: rango 1 a x3) y correaje; boinas y TOS de regimiento y
        # boonie; gafas ESS y pañuelos
        ("TRF_CS95_FS_G_U", 0), ("TRF_CS95_FS_NG_U", 0), ("TRF_CS95_HS_G_U", 0), ("TRF_CS95_HS_NG_U", 0),
        ("TRF_CS95_RS_G_U", 0), ("TRF_CS95_RS_NG_U", 0), ("TRF_PCS_FS_G_U", 0), ("TRF_PCS_FS_NG_U", 0),
        ("TRF_PCS_HS_G_U", 0), ("TRF_PCS_HS_NG_U", 0), ("TRF_PCS_RS_G_U", 0), ("TRF_PCS_RS_NG_U", 0),
        ("TRF_STV_Crew", 1, 3.0), ("TRF_STV_Grenadier", 1, 3.0),
        ("TRF_STV_Gunner", 1, 3.0), ("TRF_STV_IC", 1, 3.0), ("TRF_STV_IC_2", 1, 3.0), ("TRF_STV_IC_3", 1, 3.0),
        ("TRF_STV_Medic", 1, 3.0), ("TRF_STV_Pilot", 1, 3.0), ("TRF_STV_Rifleman", 1, 3.0),
        ("TRF_STV_Rifleman_2", 1, 3.0), ("TRF_STV_Rifleman_3", 1, 3.0), ("TRF_STV_Sharpshooter", 1, 3.0),
        ("TRF_STV_SIGNALLER", 1, 3.0), ("TRF_STV_WEBBING", 0), ("TRF_STV_WEBBING_P", 1, 3.0),
        ("TRF_VIRTUS_SHOOTER_GRENADIER", 1, 3.0), ("TRF_VIRTUS_SHOOTER_GUNNER", 1, 3.0),
        ("TRF_VIRTUS_SHOOTER_IC", 1, 3.0), ("TRF_VIRTUS_SHOOTER_IC_2", 1, 3.0), ("TRF_VIRTUS_SHOOTER_IC_3", 1, 3.0),
        ("TRF_VIRTUS_SHOOTER_MEDIC", 1, 3.0), ("TRF_VIRTUS_SHOOTER_RIFLEMAN", 1, 3.0),
        ("TRF_VIRTUS_SHOOTER_RIFLEMAN_2", 1, 3.0), ("TRF_VIRTUS_SHOOTER_RIFLEMAN_3", 1, 3.0),
        ("TRF_VIRTUS_SHOOTER_SHARPSHOOTER", 1, 3.0), ("UKAF_C2R_CBAV_JTAC", 1, 3.0), ("UKAF_C2R_CBAV_JTAC_2", 1, 3.0),
        ("UKAF_C2R_CBAV_MARKSMAN", 1, 3.0), ("UKAF_C2R_CBAV_MEDIC", 1, 3.0), ("UKAF_C2R_CBAV_RIFLEMAN", 1, 3.0),
        ("UKAF_C2R_CBAV_RIFLEMAN_2", 1, 3.0), ("UKAF_C2R_CBAV_SL", 1, 3.0), ("UKAF_C2R_CBAV_SL_2", 1, 3.0),
        ("UKAF_1RA_BERET", 0), ("UKAF_1RIFLES_BERET_V1", 0), ("UKAF_1RIFLES_BERET_V2", 0), ("UKAF_1RIR2_BERET", 0),
        ("UKAF_1RIR_BERET", 0), ("UKAF_AAC_BERET", 0), ("UKAF_BOONIE", 0), ("UKAF_KRH_BERET", 0),
        ("UKAF_MERCIAN_BERET", 0), ("UKAF_PARAS_BERET", 0), ("UKAF_QRH_BERET", 0), ("UKAF_RAF_BERET", 0),
        ("UKAF_RAFREG_BERET", 0), ("UKAF_RAMS_BERET", 0), ("UKAF_RAMS_PARA_BERET", 0), ("UKAF_RCS_BERET", 0),
        ("UKAF_RCS_PARA_BERET", 0), ("UKAF_RDG_BERET", 0), ("UKAF_RLC_BERET", 0), ("UKAF_RMC_BERET_V1", 0),
        ("UKAF_RMC_BERET_V2", 0), ("UKAF_RNG_BERET_V1", 0), ("UKAF_RNG_BERET_V2", 0), ("UKAF_RRF_BERET_V1", 0),
        ("UKAF_RRF_BERET_V2", 0), ("UKAF_RROS_1SCOTS_TOS", 0), ("UKAF_RROS_2SCOTS_TOS", 0), ("UKAF_RROS_3SCOTS_TOS", 0),
        ("UKAF_RROS_4SCOTS_TOS", 0), ("UKAF_RROS_5SCOTS_TOS", 0), ("UKAF_RTR_BERET", 0), ("UKAF_SG_BERET_V1", 0),
        ("UKAF_SG_BERET_V2", 0), ("UKAF_YORKS_BERET", 0), ("UKAF_ESS_OFF", 0), ("UKAF_ESS_OFF_SHEMAGH_DOWN_OD", 0),
        ("UKAF_ESS_OFF_SHEMAGH_DOWN_TAN", 0), ("UKAF_ESS_OFF_SHEMAGH_UP_OD", 0), ("UKAF_ESS_OFF_SHEMAGH_UP_TAN", 0),
        ("UKAF_ESS_ON", 0), ("UKAF_ESS_SHEMAGH_DOWN_OD", 0), ("UKAF_ESS_SHEMAGH_DOWN_TAN", 0),
        ("UKAF_ESS_SHEMAGH_UP_OD", 0), ("UKAF_ESS_SHEMAGH_UP_TAN", 0), ("UKAF_SHEMAGH_DOWN_OD", 0),
        ("UKAF_SHEMAGH_DOWN_TAN", 0), ("UKAF_SHEMAGH_UP_OD", 0), ("UKAF_SHEMAGH_UP_TAN", 0),
        # Contratista / fuerzas especiales occidentales (mod "[TRF] Blackthorn Operators Equipment - REDUX", Workshop
        # 3694150202, sin su PBO de ACE): Crye G4 y Patagonia L9 multicam, OD y negros, traje y camisa de piloto;
        # chalecos Spiritus LV119 y de piloto (blindaje 24: rango 1 a x3) y chest rig; boonie y gorra; pasamontañas;
        # mochilas Minimap y Zipon (carga 300 con masa 10: rango 1 a x3, como las grandes de la tienda)
        ("BTRG_CRYE_G4_G_PCU_U_BLK", 0), ("BTRG_CRYE_G4_G_RS_U", 0), ("BTRG_CRYE_G4_G_RS_U_BLK", 0),
        ("BTRG_CRYE_G4_NG_FS_U", 0), ("BTRG_CRYE_G4_NG_RS_U", 0), ("BTRG_CRYE_G4_PCU_OD_U", 0),
        ("BTRG_CRYE_G4_PCU_U", 0), ("BTRG_CRYE_L9_G_RS_OD_U", 0), ("BTRG_CRYE_L9_G_RS_U", 0), ("BTRG_FLIGHTSUIT_U", 0),
        ("BTRG_MERLIN_SHIRT_U", 0), ("BTRG_CHESTRIG", 0), ("BTRG_PILOT_VEST", 1, 3.0), ("BTRG_SPIRITUS_A", 1, 3.0),
        ("BTRG_SPIRITUS_A_BLK", 1, 3.0), ("BTRG_SPIRITUS_B", 1, 3.0), ("BTRG_SPIRITUS_B_BLK", 1, 3.0),
        ("BTRG_SPIRITUS_C", 1, 3.0), ("BTRG_SPIRITUS_C_BLK", 1, 3.0), ("BTRG_SPIRITUS_D", 1, 3.0),
        ("BTRG_SPIRITUS_D_BLK", 1, 3.0), ("BTRG_SPIRITUS_E", 1, 3.0), ("BTRG_SPIRITUS_E_BLK", 1, 3.0),
        ("BTRG_SPIRITUS_F", 1, 3.0), ("BTRG_SPIRITUS_F_BLK", 1, 3.0), ("BTRG_SPIRITUS_THUMPER", 1, 3.0),
        ("BTRG_BOONIE", 0), ("BTRG_CAP", 0), ("BTRG_Balaclava_BLK", 0), ("BTRG_Balaclava_CB", 0),
        ("BTRG_Balaclava_CB_ESS", 0), ("BTRG_Balaclava_MC", 0), ("BTRG_Balaclava_MC_ESS", 0), ("BTRG_Balaclava_OD", 0),
        ("BTRG_Balaclava_OD_ESS", 0), ("BTRG_MINIMAP", 1, 3.0), ("BTRG_MINIMAP_BLK", 1, 3.0),
        ("BTRG_MINIMAP_CUT", 1, 3.0), ("BTRG_MINIMAP_CUT_BLK", 1, 3.0), ("BTRG_MINIMAP_LR", 1, 3.0),
        ("BTRG_MINIMAP_LR_BLK", 1, 3.0), ("BTRG_MINIMAP_LR_CUT", 1, 3.0), ("BTRG_MINIMAP_LR_CUT_BLK", 1, 3.0),
        ("BTRG_MINIMAP_PILOT", 1, 3.0), ("BTRG_ZIPON", 1, 3.0), ("BTRG_ZIPON_BLK", 1, 3.0), ("BTRG_ZIPON_CUT", 1, 3.0),
        ("BTRG_ZIPON_CUT_BLK", 1, 3.0), ("BTRG_ZIPON_LR", 1, 3.0), ("BTRG_ZIPON_LR_BLK", 1, 3.0),
        ("BTRG_ZIPON_LR_CUT", 1, 3.0),
        # Fuera a propósito (work/vio_newmods/gear_added.json): cascos TRF de blindaje 24 y el LH250 (visión nocturna y
        # térmica), visor FPV de UKAF (terminal UAV gratis), gunbelt, radio invisible, mochilas de carga 400-600, la
        # bayoneta (es un silenciador), todo lo del Blackthorn viejo (3616178602, no se carga) y 21 uniformes de UKAF
        # cuyos modelos piden un .rvmat que el mod no trae en su versión del 2026-10-13 (aviso "Cannot load material"):
        # Crye G4 (12), PCS Smock (2), trajes de vuelo (5), traje seco y mono de nieve. Volver a ponerlos cuando el autor
        # lo corrija (comprobar con work/vio_newmods/final/recheck/recheck.sh)
    ],
    "RU": [
        # URSS 1989 como en Reforger: M88 'Afghanka' (CUP y RHS), KLMK, Gorka Berezka, cascos SSh-68/SSh-60, pilotka y gorras
        # M88, 6B2/6B3/6B5, chest rigs Chicom y lifchik, correajes, RD-54 y portacohetes RPG (el sidor va en "*")
        ("CUP_U_O_RUS_M88_MSV", 0), ("CUP_U_O_RUS_M88_MSV_rolled_up", 0), ("CUP_U_O_RUS_M88_VDV", 0),
        ("CUP_U_O_RUS_M88_VDV_rolled_up", 0), ("rhs_uniform_afghanka", 0), ("rhs_uniform_afghanka_boots", 0),
        ("rhs_uniform_afghanka_para", 0), ("rhs_uniform_afghanka_winter", 0), ("rhs_uniform_afghanka_winter_boots", 0),
        ("rhs_uniform_klmk_oversuit", 0), ("rhs_uniform_afghanka_klmk", 0), ("rhs_uniform_afghanka_spetsodezhda", 0),
        ("rhs_uniform_gorka_1_b", 0), ("rhs_uniform_gorka_1_a", 0), ("CUP_H_RUS_SSH68_green", 0), ("CUP_H_RUS_SSH68_olive", 0),
        ("CUP_H_RUS_SSH68_cover_berezka", 0), ("CUP_H_RUS_SSH68_cover_vsr84_dubok", 0), ("rhs_ssh68_2", 0), ("rhs_ssh60", 0),
        ("rhs_pilotka", 0), ("rhs_fieldcap_m88", 0), ("rhs_fieldcap_m88_back", 0), ("rhs_fieldcap_m88_klmk", 0),
        ("rhs_fieldcap_khk", 0), ("rhs_fieldcap_early", 0), ("rhs_ushanka", 0), ("rhs_beret_vdv_early", 0), ("rhs_tsh4", 0),
        ("CUP_H_RUS_TSH_4_Brown", 0), ("rhs_6b2", 0), ("rhs_6b2_chicom", 0), ("rhs_6b2_lifchik", 0), ("rhs_6b2_AK", 0),
        ("rhs_6b3", 0), ("rhs_6b3_AK", 0), ("rhs_6b3_VOG", 0), ("rhs_6b3_RPK", 0), ("rhs_6b5", 0), ("rhs_6b5_khaki", 0),
        ("rhs_chicom", 0), ("rhs_chicom_khk", 0), ("rhs_lifchik", 0), ("rhs_lifchik_vog", 0), ("rhs_suspender_AK", 0),
        ("rhs_belt_AK", 0), ("rhs_belt_AK_GL", 0), ("rhs_belt_RPK", 0), ("CUP_V_O_SLA_Carrier_Belt02", 0), ("rhs_rd54", 0),
        ("rhs_rd54_vest", 0), ("rhs_rpg_6b2", 0), ("rhs_rpg_6b3", 0), ("rhs_rpg_empty", 0),
        ("CUP_B_RPGPack_Khaki", 0), ("rhs_r148", 0), ("rhs_medic_bag", 0),
        # Años 90 / Chechenia: M88 TTsKO y VSR, Flora, SSh-68 con funda VSR, 6B26, 6B5 TTsKO/VSR, 6Sh92, 6B13
        ("rhs_uniform_afghanka_ttsko", 0), ("rhs_uniform_afghanka_ttsko_2", 0), ("rhs_uniform_afghanka_vsr_1", 0),
        ("rhs_uniform_afghanka_vsr_2", 0), ("rhs_uniform_afghanka_vsr_3", 0), ("rhs_uniform_afghanka_para_ttsko", 0),
        ("rhs_uniform_flora", 0), ("rhs_uniform_flora_patchless", 0), ("rhs_uniform_vdv_flora", 0),
        ("rhs_uniform_mflora_patchless", 0), ("rhs_uniform_vdv_mflora", 0), ("CUP_H_RUS_SSH68_cover_vsr93", 0),
        ("CUP_H_RUS_SSH68_cover_vsr98", 0), ("rhsgref_ssh68_vsr", 0), ("rhs_6b26", 0), ("rhs_6b26_green", 0),
        ("rhs_6b26_ess", 0), ("rhs_fieldcap_m88_ttsko", 0), ("rhs_fieldcap_m88_vsr", 0), ("rhs_fieldcap_vsr", 0),
        ("rhs_beanie", 0), ("rhs_Booniehat_flora", 0), ("rhs_6b5_ttsko", 0), ("rhs_6b5_vsr", 0), ("rhs_6b5_rifleman_ttsko", 0),
        ("rhs_6b5_rifleman_vsr", 0), ("rhs_6sh92", 0), ("rhs_6sh92_vog", 0), ("rhs_6sh92_radio", 0), ("rhs_6b13_Flora", 0),
        ("rhs_6b13_Flora_6sh92", 0), ("rhs_rd54_flora1", 0), ("rhs_rd54_vest_flora1", 0),
        # Moderno (2014-2026): Gorka y Gorka-3, VKPO, 6Sh122, EMR, Izlom; 6B47, 6B7, Altyn; 6B45, 6B23, 6B43, Smersh, 6Sh117;
        # mochilas 6Sh117/6Sh118; NVG; pasamontañas
        ("CUP_U_O_RUS_Gorka_Green", 0), ("CUP_U_O_RUS_Gorka_Green_gloves_kneepads", 0), ("CUP_U_O_RUS_Gorka_Partizan", 0),
        ("CUP_U_O_RUS_Gorka_Partizan_A", 0), ("CUP_U_O_RUS_Soldier_Gorka_EMR_1", 0), ("CUP_U_O_RUS_Soldier_Gorka_Khaki_1", 0),
        ("CUP_U_O_RUS_Soldier_Gorka_A_Tacs_1", 0), ("CUP_U_O_RUS_Soldier_Gorka_Brown_1", 0),
        ("CUP_U_O_RUS_Soldier_VKPO_Summer_1", 0), ("CUP_U_O_RUS_Soldier_VKPO_Rolled_Summer_1", 0),
        ("CUP_U_O_RUS_Soldier_VKPO_Desert_1", 0), ("CUP_U_O_RUS_Soldier_VKPO_Winter_1", 0),
        ("CUP_U_O_RUS_Soldier_VKPO_Jacket_Winter_1", 0), ("CUP_U_O_RUS_BeigeDigital_MSV", 0), ("rhs_uniform_vkpo", 0),
        ("rhs_uniform_vkpo_gloves", 0), ("rhs_uniform_vkpo_alt", 0), ("rhs_uniform_6sh122_v1", 0), ("rhs_uniform_6sh122_v2", 0),
        ("rhs_uniform_gorka_r_g", 0), ("rhs_uniform_gorka_r_y", 0), ("rhs_uniform_emr_patchless", 0),
        ("rhs_uniform_vdv_emr", 0), ("rhs_uniform_emr_des_patchless", 0), ("rhs_uniform_mvd_izlom", 0), ("U_O_R_Gorka_01_F", 0),
        ("U_O_R_Gorka_01_camo_F", 0), ("U_O_R_Gorka_01_brown_F", 0), ("CUP_H_RUS_Altyn", 1), ("CUP_H_RUS_Altyn_Goggles", 1),
        ("CUP_H_RUS_K6_3", 1), ("CUP_H_RUS_Beret_Spetsnaz", 0), ("CUP_H_RUS_Cap_EMR", 0), ("CUP_H_RUS_Bandana_HS", 0),
        ("rhs_6b47", 0), ("rhs_6b47_emr", 0), ("rhs_6b47_bala", 0), ("rhs_6b47_ess", 0), ("rhs_6b47_6m2", 0),
        ("rhs_6b47_bare_d", 0), ("rhs_6b7_1m", 0), ("rhs_6b7_1m_emr", 0), ("rhs_6b7_1m_emr_ess", 0), ("rhs_6b7_1m_olive", 0),
        ("rhs_6b27m_digi", 0), ("rhs_6b27m_green", 0), ("rhs_6b28", 0), ("rhs_6b28_green", 0), ("rhs_fieldcap_digi", 0),
        ("rhs_fieldcap_izlom", 0), ("rhs_vkpo_cap", 0), ("rhs_beanie_green", 0), ("rhs_Booniehat_digi", 0), ("rhs_gssh18", 0),
        ("CUP_H_RUS_6B47_NV_Summer", 0), ("CUP_H_RUS_6B47_NV_6M2_6B34C_Summer", 0),
        ("CUP_V_O_RUS_6B45_AK_Summer", 1), ("CUP_V_O_RUS_6B45_AK_Radio_Summer", 1), ("CUP_V_O_RUS_6B45_SVD_Summer", 1),
        ("CUP_V_O_RUS_6B45_AK_Med_Summer", 1), ("CUP_V_O_RUS_6B45_AK_Desert", 1), ("CUP_V_O_RUS_6B45_1_AK_Summer", 1),
        ("CUP_V_O_RUS_6B45_1_6Sh117_AK_Summer", 1), ("CUP_V_O_RUS_RPS_Smersh_AK_Green", 0),
        ("CUP_V_O_RUS_RPS_Smersh_AK_ModernOlive", 0), ("CUP_V_O_RUS_RPS_Smersh_AK_Coyote", 0),
        ("CUP_V_O_RUS_RPS_Smersh_VOG_Green", 0), ("CUP_V_O_RUS_RPS_Smersh_PKP_Green", 0), ("rhs_6b45_rifleman", 1),
        ("rhs_6b45_light", 1), ("rhs_6b45_mg", 1), ("rhs_6b45_grn", 1), ("rhs_6b45_off", 1), ("rhs_6b23_digi_rifleman", 1),
        ("rhs_6b23_digi_6sh92", 1), ("rhs_6b23_digi_6sh92_vog", 1), ("rhs_6b23_digi_medic", 1), ("rhs_6b23_digi_sniper", 1),
        ("rhs_6b13_EMR_6sh92", 1), ("rhs_6sh117_rifleman", 0), ("rhs_6sh117_nco", 0), ("rhs_6sh117_mg", 0),
        ("rhs_6sh117_grn", 0), ("rhs_6sh92_digi", 0), ("rhs_vydra_3m", 0), ("rhs_6b43", 1), ("CUP_B_RUS_Patrol_bag_Summer", 0),
        ("CUP_B_RUS_Patrol_bag_Desert", 0), ("CUP_B_RUS_Patrol_bag_Winter", 0), ("CUP_B_RUS_Raid_bag_Summer", 1),
        ("CUP_B_RUS_Raid_bag_Desert", 1), ("CUP_B_RUS_Raid_bag_Winter", 1), ("CUP_B_Raid_bag_SSO_Ataka_2_Green", 1),
        ("CUP_B_Raid_bag_SSO_Ataka_2_ModernOlive", 1), ("CUP_B_RUS_Backpack", 0), ("rhs_assault_umbts", 0),
        ("rhs_rk_sht_30_emr", 0), ("rhs_rk_sht_30_olive", 0), ("rhs_tortila_emr", 2), ("rhs_tortila_olive", 2),
        ("rhs_rd54_emr1", 0), ("CUP_NVG_HMNVS", 0), ("rhs_6m2_nvg", 0), ("rhs_6m2_1_nvg", 0), ("O_NVGoggles_grn_F", 0),
        ("rhs_balaclava", 0), ("CUP_G_RUS_Ratnik_Balaclava_Green_1", 0),
        ("CUP_G_RUS_Ratnik_Balaclava_EMR_Summer_1", 0), ("CUP_G_RUS_Ratnik_Balaclava_Olive_1", 0),
    ],
    "UA": [
        # Ucrania 2014-2026: lo que llevan las unidades AFU de CUP y la tienda no tiene (Crye G3, multicam sin parches, vz.95
        # checo, Flecktarn alemán, MTP/DDPM, TTsKO/VSR, BDU M81; IOTV MM-14, chalecos checos, alemanes y británicos, CPC/JPC;
        # Ops-Core, ACH, M92; Falcon-II MM-14; PVS-14/15, HMNVS; gafas y pañuelos)
        ("CUP_U_B_AFU_ACU_Rolled_M14", 0), ("CUP_U_B_AFU_ACU_Rolled_Gloves_M14", 0), ("CUP_U_B_AFU_ACU_Kneepad_Rolled_M14", 0),
        ("CUP_U_CRYE_G3C_MC", 0), ("CUP_U_CRYE_G3C_MC_V3", 0), ("CUP_U_CRYE_G3C_M81", 0), ("CUP_U_CRYE_G3C_RGR", 0),
        ("CUP_U_CRYE_MCAM_NP_Roll", 0), ("CUP_U_CRYE_MCAM_NP2_Full", 0), ("CUP_U_CRYE_MCAM_NP2_Roll", 0),
        ("CUP_U_B_CZ_WDL_NoKneepads", 0), ("CUP_U_B_CZ_WDL_Kneepads_Gloves", 0), ("CUP_U_B_GER_Fleck_Crye", 0),
        ("CUP_U_B_GER_Fleck_Crye2", 0), ("CUP_I_B_PARA_Unit_9", 0), ("CUP_I_B_PARA_Unit_15", 0), ("CUP_I_B_PARA_Unit_12", 0),
        ("rhs_uniform_g3_mc", 0), ("rhs_uniform_g3_rgr", 0), ("CUP_U_O_Partisan_TTsKO", 0), ("CUP_U_O_Partisan_VSR_Mixed1", 0),
        ("CUP_U_O_Partisan_VSR_Mixed2", 0), ("CUP_U_B_BDUv2_M81", 0), ("CUP_U_B_BDUv2_roll_M81", 0),
        ("CUP_U_B_BDUv2_dirty_M81", 0), ("CUP_H_AFU_HelmetACH_GCOVERED_Headset_MM_14", 0), ("CUP_H_OpsCore_Covered_MM14", 0),
        ("CUP_H_OpsCore_Covered_MM14_NoHS", 0), ("CUP_H_OpsCore_Covered_MM14_SF", 0), ("CUP_H_CZ_Helmet09", 0),
        ("CUP_H_CZ_Hat02", 0), ("CUP_H_Ger_M92_Cover", 0), ("CUP_H_Ger_Boonie_Flecktarn", 0),
        ("CUP_H_OpsCore_Covered_Fleck", 0), ("CUP_H_OpsCore_Covered_MTP", 0), ("CUP_H_OpsCore_Covered_MCAM", 0),
        ("CUP_H_OpsCore_Covered_MCAM_SF", 0), ("CUP_H_OpsCore_Green", 0), ("CUP_H_OpsCore_Tan", 0), ("CUP_H_OpsCore_Spray", 0),
        ("CUP_H_USArmy_HelmetACH_Headset_OCP", 0), ("CUP_H_USArmy_Boonie_hs_OCP", 0), ("CUP_H_CDF_H_PASGT_FST", 0),
        ("rhsusf_opscore_mc_cover", 0), ("CUP_H_PASGTv2_OD", 0), ("rhsgref_helmet_pasgt_olive", 0), ("CUP_H_USA_Cap_MCAM", 0),
        ("H_Booniehat_mcamo", 0, 0.25), ("H_Watchcap_blk", 0, 0.25), ("CUP_V_B_IOTV_MM14_SL_USArmy", 0),
        ("CUP_V_B_IOTV_MM14_Grenadier_USArmy", 0), ("CUP_V_B_IOTV_MM14_Rifleman_Deltoid_USArmy", 0), ("CUP_V_CZ_vest10", 0),
        ("CUP_V_CZ_vest12", 0), ("CUP_V_CZ_vest16", 0), ("CUP_V_B_GER_Armatus_Fleck", 0), ("CUP_V_B_GER_Carrier_Vest", 0),
        ("CUP_V_B_BAF_DPM_Osprey_Mk3_Grenadier", 0), ("CUP_V_B_BAF_DPM_Osprey_Mk3_Medic", 0),
        ("CUP_V_B_BAF_MTP_Osprey_Mk4_Scout", 0), ("CUP_V_CPC_communicationsbelt_mc", 0), ("CUP_V_CPC_medicalbelt_mc", 0),
        ("CUP_V_CPC_tlbelt_rngr", 0), ("CUP_V_CPC_weaponsbelt_rngr", 0), ("CUP_V_CPC_lightbelt_rngr", 0),
        ("CUP_V_JPC_communicationsbelt_mc", 0), ("CUP_V_JPC_lightbelt_mc", 0), ("CUP_V_JPC_weaponsbelt_mc", 0),
        ("CUP_V_JPC_tl_mc", 0), ("CUP_V_CPC_light_mc", 0), ("CUP_V_B_Ciras_Coyote", 0),
        ("V_PlateCarrier1_rgr_noflag_F", 0), ("V_PlateCarrier2_rgr_noflag_F", 0), ("V_CarrierRigKBT_01_Olive_F", 0),
        ("V_CarrierRigKBT_01_light_Olive_F", 0), ("rhsusf_plateframe_rifleman", 0), ("rhsusf_mbav_rifleman", 0),
        ("CUP_B_AFU_Assault_MM14", 0), ("B_Kitbag_mcamo", 1, 3.0), ("B_Carryall_mcamo", 1, 3.0),
        ("B_RadioBag_01_mtp_F", 0, 3.0), ("rhsusf_falconii_mc", 0), ("CUP_NVG_PVS14", 0), ("CUP_NVG_PVS15_black", 0),
        ("CUP_NVG_HMNVS", 0), ("rhsusf_ANPVS_14", 0), ("CUP_G_ESS_RGR", 0), ("CUP_G_ESS_BLK", 0), ("CUP_G_Oakleys_Clr", 0),
        ("rhsusf_shemagh_grn", 0), ("rhsusf_shemagh_gogg_grn", 0),
        # Aspecto guerrilla (tipo FIA) que en la tienda rusa repetiría nombre
        ("rhsgref_chicom", 0),
        # Ucrania 1991-2014 (y Donbás 2014-2015): M88 y M10 TTsKO, cascos SSh-68 (con funda TTsKO y lisos), gorras TTsKO,
        # chalecos 6B2 y mochila ALICE TTsKO
        ("rhsgref_uniform_ttsko_forest", 0), ("rhsgref_uniform_ttsko_mountain", 0), ("rhsgref_uniform_para_ttsko_mountain", 0),
        ("rhsgref_ssh68_ttsko_forest", 0), ("rhsgref_ssh68_ttsko_mountain", 0), ("CUP_H_RUS_SSH68_green", 0),
        ("CUP_H_RUS_SSH68_olive", 0), ("rhsgref_fieldcap_ttsko_forest", 0), ("rhsgref_fieldcap_ttsko_mountain", 0),
        ("rhs_6b2", 0), ("rhs_6b2_chicom", 0), ("rhsgref_ttsko_alicepack", 0, 3.0),
        # Ayuda británica y voluntarios (mods TRF "UK Armed Forces" 3678757032 y "Blackthorn REDUX" 3694150202, carpeta
        # @nue; sin los mods se saltan): uniformes MTP CS95 y PCS sin insignia; chalecos STV Virtus, C2R CBAV y
        # Spiritus LV119 multicam (blindaje 24: rango 1 a x3), chest rig y correaje; boonies; gafas ESS, pañuelos OD y
        # pasamontañas. Sin boinas, uniformes de la Royal Navy/Marines ni las versiones negras de REDUX
        ("TRF_CS95_FS_G_U", 0), ("TRF_CS95_FS_NG_U", 0), ("TRF_CS95_HS_G_U", 0), ("TRF_CS95_HS_NG_U", 0),
        ("TRF_CS95_RS_G_U", 0), ("TRF_CS95_RS_NG_U", 0), ("TRF_PCS_FS_G_U", 0), ("TRF_PCS_FS_NG_U", 0),
        ("TRF_PCS_HS_G_U", 0), ("TRF_PCS_HS_NG_U", 0), ("TRF_PCS_RS_G_U", 0), ("TRF_PCS_RS_NG_U", 0),
        ("TRF_STV_Crew", 1, 3.0), ("TRF_STV_Grenadier", 1, 3.0),
        ("TRF_STV_Gunner", 1, 3.0), ("TRF_STV_IC", 1, 3.0), ("TRF_STV_IC_2", 1, 3.0), ("TRF_STV_IC_3", 1, 3.0),
        ("TRF_STV_Medic", 1, 3.0), ("TRF_STV_Rifleman", 1, 3.0), ("TRF_STV_Rifleman_2", 1, 3.0),
        ("TRF_STV_Rifleman_3", 1, 3.0), ("TRF_STV_Sharpshooter", 1, 3.0), ("TRF_STV_SIGNALLER", 1, 3.0),
        ("TRF_STV_WEBBING", 0), ("TRF_STV_WEBBING_P", 1, 3.0), ("UKAF_C2R_CBAV_JTAC", 1, 3.0),
        ("UKAF_C2R_CBAV_JTAC_2", 1, 3.0), ("UKAF_C2R_CBAV_MARKSMAN", 1, 3.0), ("UKAF_C2R_CBAV_MEDIC", 1, 3.0),
        ("UKAF_C2R_CBAV_RIFLEMAN", 1, 3.0), ("UKAF_C2R_CBAV_RIFLEMAN_2", 1, 3.0), ("UKAF_C2R_CBAV_SL", 1, 3.0),
        ("UKAF_C2R_CBAV_SL_2", 1, 3.0), ("UKAF_BOONIE", 0), ("UKAF_ESS_OFF", 0), ("UKAF_ESS_OFF_SHEMAGH_DOWN_OD", 0),
        ("UKAF_ESS_OFF_SHEMAGH_UP_OD", 0), ("UKAF_ESS_ON", 0), ("UKAF_ESS_SHEMAGH_DOWN_OD", 0),
        ("UKAF_ESS_SHEMAGH_UP_OD", 0), ("UKAF_SHEMAGH_DOWN_OD", 0), ("UKAF_SHEMAGH_UP_OD", 0), ("BTRG_CHESTRIG", 0),
        ("BTRG_SPIRITUS_A", 1, 3.0), ("BTRG_SPIRITUS_B", 1, 3.0), ("BTRG_SPIRITUS_C", 1, 3.0),
        ("BTRG_SPIRITUS_D", 1, 3.0), ("BTRG_SPIRITUS_E", 1, 3.0), ("BTRG_SPIRITUS_F", 1, 3.0),
        ("BTRG_SPIRITUS_THUMPER", 1, 3.0), ("BTRG_BOONIE", 0), ("BTRG_Balaclava_CB", 0), ("BTRG_Balaclava_CB_ESS", 0),
        ("BTRG_Balaclava_MC", 0), ("BTRG_Balaclava_MC_ESS", 0), ("BTRG_Balaclava_OD", 0), ("BTRG_Balaclava_OD_ESS", 0),
    ],
    "*": [
        # Guerrilla tipo FIA (Reforger) para todos: ropa civil y NAPA de Chernarus (solo oeste), guerrilla vanilla (oeste),
        # ChDKZ, M93 de RHS y chándal (solo este; sin los woodland que parecen el M81 de EE. UU.); el filtro de bando deja a
        # cada tienda la suya. Gorros, sombreros, chalecos improvisados, bolsos y pañuelos sirven a los dos (los de vanilla
        # al precio de Gear_Basic: gorra x0.25, chaleco x1)
        ("CUP_U_I_GUE_Anorak_01", 0), ("CUP_U_I_GUE_Anorak_02", 0), ("CUP_U_I_GUE_Anorak_03", 0), ("CUP_U_I_GUE_Woodland1", 0),
        ("CUP_U_I_GUE_Flecktarn", 0), ("CUP_U_I_GUE_Flecktarn2", 0), ("CUP_U_I_GUE_Flecktarn3", 0),
        ("CUP_U_I_GUE_Flecktarn4", 0), ("CUP_U_I_GUE_WorkU_01", 0), ("CUP_U_I_GUE_WorkU_02", 0), ("CUP_U_C_Woodlander_01", 0),
        ("CUP_U_C_Woodlander_02", 0), ("CUP_U_C_Woodlander_03", 0), ("CUP_U_C_Woodlander_04", 0), ("CUP_U_C_Villager_01", 0),
        ("CUP_U_C_Villager_02", 0), ("CUP_U_C_Villager_03", 0), ("CUP_U_C_Villager_04", 0), ("CUP_U_C_Worker_01", 0),
        ("CUP_U_C_Worker_02", 0), ("CUP_U_C_Worker_03", 0), ("CUP_U_C_Worker_04", 0), ("CUP_U_C_Citizen_01", 0),
        ("CUP_U_C_Citizen_03", 0), ("U_BG_Guerilla1_1", 0), ("U_BG_Guerilla1_2_F", 0), ("U_BG_Guerilla2_1", 0),
        ("U_BG_Guerilla2_2", 0), ("U_BG_Guerilla2_3", 0), ("U_BG_Guerilla3_1", 0), ("U_BG_leader", 0),
        ("U_BG_Guerrilla_6_1", 0), ("U_I_G_resistanceLeader_F", 0), ("CUP_H_C_Beanie_01", 0), ("CUP_H_C_Beanie_02", 0),
        ("CUP_H_C_Beanie_03", 0), ("CUP_H_C_Beanie_04", 0), ("CUP_H_C_Beret_01", 0), ("CUP_H_C_Beret_02", 0),
        ("CUP_H_C_Beret_04", 0), ("CUP_H_C_Ushanka_01", 0), ("CUP_H_C_Ushanka_02", 0), ("CUP_H_C_Ushanka_03", 0),
        ("CUP_H_C_Ushanka_04", 0), ("H_Watchcap_camo", 0, 0.25), ("H_Watchcap_cbr", 0, 0.25), ("H_Watchcap_khk", 0, 0.25),
        ("H_Cap_oli", 0, 0.25), ("H_Cap_grn", 0, 0.25), ("H_Cap_blk", 0, 0.25), ("H_Cap_tan", 0, 0.25),
        ("H_Hat_brown", 0, 0.25), ("H_Hat_grey", 0, 0.25), ("H_Hat_camo", 0, 0.25), ("H_Bandanna_camo", 0, 0.25),
        ("H_Booniehat_wdl", 0, 0.25), ("H_MilCap_grn", 0, 0.25), ("CUP_H_NAPA_Fedora", 0), ("H_Hat_Safari_olive_F", 0, 0.25),
        ("CUP_V_I_Guerilla_Jacket", 0), ("CUP_V_I_Carrier_Belt", 0), ("CUP_V_O_Ins_Carrier_Rig", 0), ("rhsgref_chestrig", 0),
        ("CUP_V_B_ALICE", 0), ("V_HarnessO_brn", 0, 1.0), ("V_HarnessOGL_brn", 0, 1.0), ("V_Pocketed_olive_F", 0, 1.0),
        ("V_Pocketed_coyote_F", 0, 1.0), ("V_LegStrapBag_olive_F", 0, 1.0), ("B_Messenger_Olive_F", 0),
        ("B_Messenger_Coyote_F", 0), ("B_Messenger_Gray_F", 0), ("B_Messenger_Black_F", 0), ("CUP_B_AlicePack_Khaki", 0, 3.0),
        ("rhs_sidor", 0), ("CUP_FR_NeckScarf2", 0), ("CUP_FR_NeckScarf3", 0), ("rhs_scarf", 0), ("CUP_G_Scarf_Face_Grn", 0),
        ("CUP_G_Scarf_Face_Blk", 0), ("CUP_U_O_CHDKZ_Kam_01", 0), ("CUP_U_O_CHDKZ_Kam_02", 0), ("CUP_U_O_CHDKZ_Kam_05", 0),
        ("CUP_U_O_CHDKZ_Kam_06", 0), ("CUP_U_O_CHDKZ_Kam_08", 0), ("CUP_U_O_CHDKZ_Commander", 0), ("CUP_U_O_CHDKZ_Bardak", 0),
        ("CUP_U_O_CHDKZ_Lopotev", 0), ("rhsgref_uniform_reed", 0), ("rhsgref_uniform_olive", 0), ("U_O_R_Gorka_01_black_F", 0),
    ],
}
GEAR_FILES = [("Common/Config/Gear/gear_CUP_US.sqf", "US"), ("Common/Config/Gear/gear_CUP_SOV.sqf", "RU"),
              ("Common/Config/Gear/gear_CUP_UKR.sqf", "UA"), ("Common/Config/Gear/gear_RHS_US.sqf", ""),
              ("Common/Config/Gear/gear_RHS_SOV.sqf", ""),
              # Tiendas de RHS GREF: Fuerzas de Defensa de Chernarus (Oeste) y ChDKZ (guerrilla, Este), en Georgia 2008,
              # Chernarus 2009 y Donbás 2015
              ("Common/Config/Gear/gear_RHS_CDF.sqf", "CDF"), ("Common/Config/Gear/gear_RHS_ChDKZ.sqf", "CHDKZ"),
              # Tiendas de los Creator DLC: Global Mobilization (1985) y S.O.G. (1968). Solo armas de su época.
              ("Common/Config/Gear/gear_GM_BW.sqf", "BW"), ("Common/Config/Gear/gear_GM_NVA.sqf", "NVA"),
              ("Common/Config/Gear/gear_US_SOG.sqf", "USSOG"), ("Common/Config/Gear/gear_NVA_SOG.sqf", "PAVN")]
GEAR_ANCHOR = "if(!isNil 'CTI_Init_Common') then {"
# Claves de GEAR_EXTRA para las tiendas de RHS (nación ""), por bando del jugador.
RHS_SIDE_KEYS = {"west": "RHS_WEST", "east": "RHS_EAST"}
# Valores de _vioc_nation cuyas tiendas reciben la lista común de armas GEAR_EXTRA["*"]; "" = las dos tiendas de RHS.
GEAR_EXTRA_ALL_NATIONS = ("US", "RU", "UA", "CDF", "CHDKZ", "")


# Texto de Common/Config/Gear/VIOC_gear_extra.sqf; @WEAPONS@, @WEAPONS_ALL@ (+ @WEAPONS_ALL_NATIONS@), @WEAR@ y @WEAR_ALL@
# son las listas (ver gear_extra_sqf).
GEAR_EXTRA_SQF = """// VIOC_gear_extra.sqf - agregado por tools/vio_build.py (copia configurada, no es del autor de la mision).
// Lo llaman las tiendas de GEAR_FILES (gear_CUP_US/SOV/UKR, gear_RHS_US/SOV/CDF/ChDKZ, gear_GM_BW/NVA,
// gear_US_SOG y gear_NVA_SOG) justo antes de Gear_Config_Set, con sus _c/_u/_p (tienda).
// 1) Suma armas reales (CUP, RHS y vanilla) segun la nacion (_vioc_nation); en las tiendas RHS (nacion "") segun
//    el bando. Las tiendas modernas (EE. UU., Rusia, Ucrania, CDF, ChDKZ y RHS) suman ademas una lista comun de armas
//    de guerrilla e irregulares (AK viejos, FAL, G3, Mosin, PKM, RPG-7, escopetas de caza...).
// 2) Para TODAS las armas de la tienda agrega sus cargadores compatibles y sus accesorios de CUP o RHS
//    (miras, silenciadores, laseres, bipodes), asi siempre hay algo que montar. Se recorren de menor a mayor
//    nivel: un cargador que sirve a varias armas queda en el nivel mas bajo de ellas. Los lanzadores
//    desechables de RHS se venden con su cohete (es de scope 1).
// 3) Suma ropa de la nacion y una lista comun de guerrilla: uniformes, chalecos, cascos y gorras, mochilas,
//    gafas y visores nocturnos. Las tiendas RHS (_vioc_nation "") toman la ropa del bando: en el cliente
//    gear_RHS_US solo se arma para west (EE. UU.) y gear_RHS_SOV solo para east (Rusia).
//    Un uniforme solo entra si el bando de la tienda puede vestirlo (modelSides de su uniformClass).
//    Precio como el autor: [CTI_ECONOMY_PRIZE_EQUIPMENT, nivel, x] con uniforme x1, casco x1, gorra x0.5,
//    chaleco blindado x3, correaje x2, mochila x2 y gafas x0.5; visor nocturno [CTI_ECONOMY_PRIZE_WEAPONS, nivel, 2].
// Lo que no existe en el juego, o que esta tienda u otra anterior del mismo bando ya tiene, se salta.
// No agrega niveles de mejora nuevos: el rango 0, 1, 2.. de las listas es el 1.o, 2.o, 3.o.. nivel que YA usa esta
// tienda (se recorta al ultimo). Si la tienda empieza mas arriba porque comparte bando con otra nacion, se corre con ella.
if (isNil 'CTI_Init_Common') exitWith {};
private _vioc_levels = [];
{ _vioc_levels pushBackUnique _x } forEach _u;
_vioc_levels sort true;
if (_vioc_levels isEqualTo []) then { _vioc_levels = [0] };
private _vioc_rank = { _vioc_levels select ((_this max 0) min ((count _vioc_levels) - 1)) };
private _vioc_seen = createHashMap;
{ _vioc_seen set [toLower _x, true] } forEach _c;
private _vioc_tierOf = createHashMap;
{
	if (isClass (configFile >> "CfgWeapons" >> _x) && {(getNumber (configFile >> "CfgWeapons" >> _x >> "type")) in [1, 2, 4]}) then {
		_vioc_tierOf set [_x, _u select _forEachIndex];
	};
} forEach _c;
private _vioc_add = {
	params ["_item", "_tier", "_price"];
	private _k = toLower _item;
	if (_vioc_seen getOrDefault [_k, false]) exitWith {false};
	_vioc_seen set [_k, true];
	if !(isNil {missionNamespace getVariable _k}) exitWith {false};
	_c pushBack _item; _u pushBack _tier; _p pushBack _price;
	true
};
private _vioc_extra = switch (_vioc_nation) do {
@WEAPONS@
	default { [] };
};
if (_vioc_nation in @WEAPONS_ALL_NATIONS@) then { _vioc_extra = _vioc_extra + @WEAPONS_ALL@; };
{
	_x params ["_w", "_t"];
	if (isClass (configFile >> "CfgWeapons" >> _w)) then {
		_t = _t call _vioc_rank;
		if ([_w, _t, [CTI_ECONOMY_PRIZE_WEAPONS, _t, 1.0] call CTI_CO_FNC_GetCalculatedItemPrize] call _vioc_add) then { _vioc_tierOf set [_w, _t] };
	};
} forEach _vioc_extra;
private _vioc_okPrefix = ["cup_", "rhs"];
private _vioc_byTier = [];
{ _vioc_byTier pushBack [_y, _x] } forEach _vioc_tierOf;
_vioc_byTier sort true;
{
	_x params ["_t", "_w"];
	private _disp = (getNumber (configFile >> "CfgWeapons" >> _w >> "rhs_disposable")) == 1;
	{
		private _sc = getNumber (configFile >> "CfgMagazines" >> _x >> "scope");
		if (_sc >= 2 || {_disp && {_sc >= 1}}) then {
			private _cnt = getNumber (configFile >> "CfgMagazines" >> _x >> "count");
			private _price = if (_cnt <= 3) then {[CTI_ECONOMY_PRIZE_WEAPONS, _t, 0.5] call CTI_CO_FNC_GetCalculatedItemPrize} else {[CTI_ECONOMY_PRIZE_WEAPONS, _t, 0.4, _cnt] call CTI_CO_FNC_GetCalculatedItemPrize};
			[_x, _t, _price] call _vioc_add;
		};
	} forEach (compatibleMagazines _w);
	{
		private _a = toLower _x;
		if ((_vioc_okPrefix findIf {(_a find _x) == 0}) >= 0 && {getNumber (configFile >> "CfgWeapons" >> _a >> "scope") >= 2}) then {
			[_x, _t, [CTI_ECONOMY_PRIZE_EQUIPMENT, _t, 0.5] call CTI_CO_FNC_GetCalculatedItemPrize] call _vioc_add;
		};
	} forEach (_w call BIS_fnc_compatibleItems);
} forEach _vioc_byTier;
private _vioc_wear = _vioc_nation;
if (_vioc_wear == "") then { _vioc_wear = switch (_side) do { case west: {"US"}; case east: {"RU"}; default {""}; }; };
private _vioc_sid = [east, west, resistance, civilian] find _side;
private _vioc_wearList = switch (_vioc_wear) do {
@WEAR@
	default { [] };
};
if (_vioc_wear in ["US", "RU", "UA"]) then { _vioc_wearList = _vioc_wearList + @WEAR_ALL@; };
{
	_x params ["_cls", "_t", ["_m", -1]];
	_t = _t call _vioc_rank;
	private _base = CTI_ECONOMY_PRIZE_EQUIPMENT;
	private _auto = -1;
	private _cw = configFile >> "CfgWeapons" >> _cls;
	if (isClass _cw) then {
		private _ii = _cw >> "ItemInfo";
		switch (getNumber (_cw >> "type")) do {
			case CTI_TYPE_ITEM: {
				private _arm = getNumber (_ii >> "armor");
				{ _arm = _arm max (getNumber (_x >> "armor")) } forEach (configProperties [_ii >> "HitpointsProtectionInfo", "isClass _x", true]);
				switch (getNumber (_ii >> "type")) do {
					case CTI_SUBTYPE_UNIFORM: {
						if (_vioc_sid in (getArray (configFile >> "CfgVehicles" >> (getText (_ii >> "uniformClass")) >> "modelSides"))) then { _auto = 1 };
					};
					case CTI_SUBTYPE_VEST: { _auto = [2, 3] select (_arm >= 8) };
					case CTI_SUBTYPE_HEADGEAR: { _auto = [0.5, 1] select (_arm > 0) };
				};
			};
			case CTI_TYPE_EQUIPMENT: {
				if ((getText (_cw >> "simulation")) == "NVGoggles") then { _base = CTI_ECONOMY_PRIZE_WEAPONS; _auto = 2 };
			};
		};
	} else {
		if ((getNumber (configFile >> "CfgVehicles" >> _cls >> "isBackpack")) == 1) then { _auto = 2 } else {
			if (isClass (configFile >> "CfgGlasses" >> _cls)) then { _auto = 0.5 };
		};
	};
	if (_auto >= 0) then {
		if (_m < 0) then { _m = _auto };
		[_cls, _t, [_base, _t, _m] call CTI_CO_FNC_GetCalculatedItemPrize] call _vioc_add;
	};
} forEach _vioc_wearList;
"""


def check_gear_lists():
    """Revisa GEAR_EXTRA y GEAR_EXTRA_CLOTHING antes de generar el SQF: claves de nación que usa GEAR_FILES, entradas bien
    formadas, clases sin caracteres que rompan el SQF, rango entero 0..9, multiplicador finito > 0, ninguna clase repetida
    dentro de una lista y ninguna que esté a la vez en una nación y en la lista común "*" de esa tabla (ropa: toda nación;
    armas: las naciones de GEAR_EXTRA_ALL_NATIONS y las claves de RHS, que son las que reciben las dos)."""
    if "*" not in GEAR_EXTRA_CLOTHING:
        sys.exit("ERROR: GEAR_EXTRA_CLOTHING necesita la lista común \"*\"")
    nations = {n for _, n in GEAR_FILES if n}
    if not set(GEAR_EXTRA_ALL_NATIONS) <= nations | {""}:
        sys.exit(f"ERROR: GEAR_EXTRA_ALL_NATIONS no está en GEAR_FILES: {set(GEAR_EXTRA_ALL_NATIONS) - nations - {''}}")
    common = {e[0].lower() for e in GEAR_EXTRA_CLOTHING["*"] if isinstance(e, tuple) and e and isinstance(e[0], str)}
    common_w = {e[0].lower() for e in GEAR_EXTRA.get("*", []) if isinstance(e, tuple) and e and isinstance(e[0], str)}
    gets_w = set(GEAR_EXTRA_ALL_NATIONS) | (set(RHS_SIDE_KEYS.values()) if "" in GEAR_EXTRA_ALL_NATIONS else set())
    for name, lists, sizes, keys in (("GEAR_EXTRA", GEAR_EXTRA, (2,), nations | set(RHS_SIDE_KEYS.values()) | {"*"}),
                                     ("GEAR_EXTRA_CLOTHING", GEAR_EXTRA_CLOTHING, (2, 3), nations | {"*"})):
        for key, items in lists.items():
            if key not in keys:
                sys.exit(f"ERROR: {name}: clave de nación desconocida {key!r} (válidas: {', '.join(sorted(keys))})")
            seen = set()
            for e in items:
                ok = isinstance(e, tuple) and len(e) in sizes and isinstance(e[0], str) and re.fullmatch(r"[A-Za-z0-9_]+", e[0])
                ok = ok and type(e[1]) is int and 0 <= e[1] <= 9
                ok = ok and (len(e) == 2 or (type(e[2]) in (int, float) and math.isfinite(e[2]) and e[2] > 0))
                if not ok or e[0].lower() == "binocular":  # "binocular" lo guarda la misión con otro nombre: saldría dos veces
                    sys.exit(f"ERROR: {name}[{key}]: entrada mal formada {e!r}")
                if e[0].lower() in seen:
                    sys.exit(f"ERROR: {name}[{key}]: {e[0]} está repetida")
                if lists is GEAR_EXTRA_CLOTHING and key != "*" and e[0].lower() in common:
                    sys.exit(f"ERROR: {name}[{key}]: {e[0]} ya está en la lista común \"*\"")
                if lists is GEAR_EXTRA and key in gets_w and e[0].lower() in common_w:
                    sys.exit(f"ERROR: {name}[{key}]: {e[0]} ya está en la lista común \"*\"")
                seen.add(e[0].lower())


def sqf_list(items):
    """Lista SQF [["clase", nivel(, multiplicador)], ...] en varias líneas."""
    lines, cur = [], ""
    for e in items:
        tok = "[" + ", ".join([f'"{e[0]}"'] + [str(x) for x in e[1:]]) + "]"
        if cur and len(cur) + len(tok) > 110:
            lines.append(cur + ",")
            cur = ""
        cur = f"{cur}, {tok}" if cur else tok
    return "[\n\t\t" + "\n\t\t".join(lines + [cur]) + "\n\t]"


def gear_extra_sqf():
    check_gear_lists()

    def cases(lists):
        return "\n".join(f'\tcase "{k}": {{{sqf_list(v)}}};' for k, v in lists.items()
                         if k != "*" and k not in RHS_SIDE_KEYS.values())

    def rhs_case():
        # Tiendas de RHS (_vioc_nation ""): la lista del bando (_side es variable privada del archivo de la tienda).
        sides = "".join(f'\t\tcase {side}: {{{sqf_list(GEAR_EXTRA[k])}}};\n'
                        for side, k in RHS_SIDE_KEYS.items() if GEAR_EXTRA.get(k))
        return f'\n\tcase "": {{ switch (_side) do {{\n{sides}\t\tdefault {{ [] }};\n\t}} }};' if sides else ""
    nations_all = "[" + ", ".join(f'"{n}"' for n in GEAR_EXTRA_ALL_NATIONS) + "]"
    return (GEAR_EXTRA_SQF.replace("@WEAPONS@", cases(GEAR_EXTRA) + rhs_case())
            .replace("@WEAPONS_ALL_NATIONS@", nations_all).replace("@WEAPONS_ALL@", sqf_list(GEAR_EXTRA.get("*", [])))
            .replace("@WEAR@", cases(GEAR_EXTRA_CLOTHING)).replace("@WEAR_ALL@", sqf_list(GEAR_EXTRA_CLOTHING["*"])))


def read(p):
    with open(p, **ENC) as f:
        return f.read()


def write(p, s):
    with open(p, "w", **ENC) as f:
        f.write(s)


def tree_hash(root):
    """Igual que tree_hash de tools/track.sh (rutas relativas + sha256 de cada archivo, ignora .DS_Store)."""
    h = hashlib.sha256()
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            if f == ".DS_Store":
                continue
            p = os.path.join(dp, f)
            h.update(os.path.relpath(p, root).encode() + b"\0")
            with open(p, "rb") as fh:
                h.update(hashlib.sha256(fh.read()).digest())
    return h.hexdigest()


def manifest_tree_hash(dest):
    if not os.path.exists(MANIFEST):
        return None
    for line in open(MANIFEST, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) == 3 and parts[0] == "tree" and parts[1] == dest:
            return parts[2]
    return None


def manifest_set(dest, new_hash, append=False):
    lines = open(MANIFEST, encoding="utf-8").read().splitlines() if os.path.exists(MANIFEST) else []
    if append:
        lines.append(f"tree\t{dest}\t{new_hash}")
    else:
        lines = [f"tree\t{dest}\t{new_hash}" if l.split("\t")[:2] == ["tree", dest] else l for l in lines]
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(l for l in lines if l.strip()) + "\n")
    os.replace(tmp, MANIFEST)


def source_bin(cat, scn):
    """PBO del Workshop del origen, o carpeta local si el origen tiene "path" (relativa al proyecto; p. ej. una misión
    base generada por tools/vio_port.py). vio_config.py acepta las dos. None si falta."""
    src = cat["sources"][scn["source"]]
    if src.get("path"):
        folder = os.path.join(PROJECT, src["path"])
        return folder if os.path.isfile(os.path.join(folder, "mission.sqm")) else None
    hits = glob.glob(os.path.join(WORKSHOP, src["workshop"], "*_legacy.bin"))
    return hits[0] if len(hits) == 1 else None


def world_of(cat, scn):
    """El escenario puede usar otro mundo que su origen (p. ej. la misión de Chernarus verano en Chernarus otoño,
    que es el mismo terreno con otras texturas)."""
    return scn.get("world") or cat["sources"][scn["source"]]["world"]


def map_of(cat, scn):
    return scn.get("map") or cat["sources"][scn["source"]]["map"]


def dest_of(cat, scn):
    return os.path.join(MPMISSIONS, f'{scn["folder"]}.{world_of(cat, scn)}')


def sqf_str(s):
    return s.replace('"', '""')


def set_texts(stage, name, overview):
    """Descripción en la lista de misiones y en la pantalla de carga (el nombre lo pone vio_config.py)."""
    p = find_ci(stage, "Rsc/Game.hpp")
    s = read(p)
    for key in ("overviewText", "overviewTextLocked", "onLoadMission"):
        s, n = re.subn(rf'(\b{key}\s*=\s*")[^"]*(")', lambda m: m.group(1) + sqf_str(overview) + m.group(2), s)
        if n > 1:
            sys.exit(f"ERROR: {key} aparece {n} veces en Game.hpp")  # 0 = versión vieja de la misión sin ese campo: se omite
    write(p, s)
    p = find_ci(stage, "mission.sqm")
    s = read(p)
    s, n = re.subn(r'(\boverviewText(?:Locked)?\s*=\s*")[^"]*(")', lambda m: m.group(1) + sqf_str(overview) + m.group(2), s)
    if n < 1:
        sys.exit("ERROR: no encontré overviewText en mission.sqm")
    write(p, s)


def patch_wardrobe(stage):
    write(os.path.join(stage, "VIOC_wardrobe.sqf"), WARDROBE_SQF)
    p = find_ci(stage, "init.sqf")
    s = read(p)
    if WARDROBE_CALL in s:
        return
    nl = "\r\n" if "\r\n" in s else "\n"
    if not s.endswith(nl):
        s += nl
    write(p, s + nl + WARDROBE_INIT + nl + WARDROBE_CALL + nl)


def patch_coop_ai_both(stage):
    """Los modos de pueblos "Coop ... [Border]" (4-9) apagan las escuadras IA del bando de los jugadores
    (Server/Init/Init_Server.sqf). Para jugar solo se dejan activas en los dos bandos."""
    p = find_ci(stage, "Server/Init/Init_Server.sqf")
    s = read(p)
    s, n = re.subn(r"(?m)^(\s*)_ai_teams_enabled = false;",
                   r"\1//_ai_teams_enabled = false; // VIOC: escuadras IA también en el bando de los jugadores", s)
    if n != 2:
        sys.exit(f"ERROR: esperaba 2 líneas '_ai_teams_enabled = false;' en Init_Server.sqf y hay {n}")
    write(p, s)


def patch_gear_extra(stage):
    """Más armas y ropa por nación y, para toda arma de la tienda, sus cargadores y accesorios (ver GEAR_EXTRA_SQF).
    La línea que se inserta en cada tienda no cambia; la ropa sale del mismo _vioc_nation (o del bando en las de RHS)."""
    write(os.path.join(find_ci(stage, "Common/Config/Gear"), "VIOC_gear_extra.sqf"), gear_extra_sqf())
    for rel, nation in GEAR_FILES:
        folder = find_ci(stage, os.path.dirname(rel))
        names = {n.lower(): n for n in os.listdir(folder)}
        if os.path.basename(rel).lower() not in names:
            continue  # versiones viejas de la misión no traen todas las naciones (p. ej. Ucrania)
        p = os.path.join(folder, names[os.path.basename(rel).lower()])
        s = read(p)
        if s.count(GEAR_ANCHOR) != 1:
            sys.exit(f"ERROR: {rel} no tiene exactamente un '{GEAR_ANCHOR}'")
        nl = "\r\n" if "\r\n" in s else "\n"
        line = (f'//--- VIOC: más armas y todos sus accesorios y cargadores (copia configurada){nl}'
                f'_vioc_nation = "{nation}"; call compile preprocessFileLineNumbers "Common\\Config\\Gear\\VIOC_gear_extra.sqf";{nl}')
        i = s.index(GEAR_ANCHOR)
        write(p, s[:i] + line + s[i:])


def patch_corpses(stage):
    """Los cuerpos quedan 10 min en el suelo (la misión los borraba a los 120 s)."""
    p = find_ci(stage, "Common/Init/Init_CommonConstants.sqf")
    s = read(p)
    s, n = re.subn(r"CTI_GC_DELAY_MAN = 120;", "CTI_GC_DELAY_MAN = 600; // VIOC: cuerpos 10 min (original 120)", s)
    if n != 1:
        sys.exit(f"ERROR: esperaba 1 'CTI_GC_DELAY_MAN = 120;' y hay {n}")
    write(p, s)


def patch_respawn_anywhere(stage):
    """Reaparecer en cualquier campamento de pueblo o FOB propio, no solo en los que quedan cerca de donde moriste
    (la misión limitaba los campamentos a CTI_RESPAWN_MOBILE_RANGE, 600 m, y las FOB a CTI_RESPAWN_FOB_RANGE, 1 km)."""
    p = find_ci(stage, "Common/Init/Init_CommonConstants.sqf")
    s = read(p)
    old = "CTI_RESPAWN_CAMPS_RANGE = CTI_RESPAWN_MOBILE_RANGE;"
    if s.count(old) != 1:
        sys.exit(f"ERROR: esperaba 1 '{old}' en Init_CommonConstants.sqf")
    s = s.replace(old, "CTI_RESPAWN_CAMPS_RANGE = 100000; CTI_RESPAWN_FOB_RANGE = 100000; "
                       "// VIOC: cualquier campamento o FOB propio (original: solo cerca de donde moriste)")
    write(p, s)


PATCHES = {"wardrobe": patch_wardrobe, "coop_ai_both": patch_coop_ai_both,
           "gear_extra": patch_gear_extra, "corpses": patch_corpses, "respawn_anywhere": patch_respawn_anywhere}

PATCH_DIR = os.path.join(HERE, "vio_patches")


def apply_steps(stage, name):
    """Parche descrito en tools/vio_patches/<name>.json: pasos new_file / append / replace / insert_before / insert_after.
    Cada ancla debe aparecer exactamente una vez; los saltos de línea del texto se adaptan a los del archivo (CRLF o LF)."""
    path = os.path.join(PATCH_DIR, name + ".json")
    if not os.path.exists(path):
        sys.exit(f"ERROR: parche desconocido '{name}'")
    spec = json.load(open(path, encoding="utf-8"))
    for st in spec["steps"]:
        rel = st["file"].replace("\\", "/")
        action = st["action"]
        text = st["text"].replace("\r\n", "\n")
        if action == "new_file":
            folder = os.path.dirname(rel)
            target = os.path.join(find_ci(stage, folder) if folder else stage, os.path.basename(rel))
            if os.path.exists(target):
                sys.exit(f"ERROR parche {name}: {rel} ya existe")
            write(target, text.replace("\n", "\r\n"))
            continue
        p = find_ci(stage, rel)
        s = read(p)
        nl = "\r\n" if "\r\n" in s else "\n"
        t = text.replace("\n", nl)
        if action == "append":
            s = (s if s.endswith(nl) else s + nl) + t
        else:
            anchor = (st.get("anchor") or "").replace("\r\n", "\n").replace("\n", nl)
            n = s.count(anchor) if anchor else 0
            if n != 1:
                sys.exit(f"ERROR parche {name}: el ancla aparece {n} veces en {rel}: {anchor[:90]!r}")
            i = s.index(anchor)
            j = i + len(anchor)
            if action == "replace":
                s = s[:i] + t + s[j:]
            elif action == "insert_before":
                s = s[:i] + t + s[i:]
            elif action == "insert_after":
                s = s[:j] + t + s[j:]
            else:
                sys.exit(f"ERROR parche {name}: acción desconocida {action}")
        write(p, s)


def build_stage(cat, scn, binp):
    stage = os.path.join(STAGE_ROOT, f'{scn["folder"]}.{world_of(cat, scn)}')
    if os.path.exists(stage):
        shutil.rmtree(stage)
    os.makedirs(STAGE_ROOT, exist_ok=True)
    params = dict(cat["common_params"][scn["common"]])
    params.update(scn["params"])
    cmd = [sys.executable, os.path.join(HERE, "vio_config.py"), "--src", binp, "--out", stage, "--name", scn["name"]]
    for k, v in params.items():
        cmd += ["--set", f"{k}={v}"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"ERROR en vio_config.py ({scn['id']}):\n{out.stdout}{out.stderr}")
    set_texts(stage, scn["name"], scn["overview"])
    for patch in scn.get("patches", []):
        if patch in PATCHES:
            PATCHES[patch](stage)
        else:
            apply_steps(stage, patch)
    return stage, out.stdout


def files_of(root):
    res = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f != ".DS_Store":
                p = os.path.join(dp, f)
                res[os.path.relpath(p, root)] = p
    return res


def install_or_update(stage, dest, dry):
    if not os.path.exists(dest):
        if dry:
            return "instalaría (carpeta nueva)"
        shutil.copytree(stage, dest)
        manifest_set(dest, tree_hash(dest), append=True)
        return "instalada"
    recorded = manifest_tree_hash(dest)
    if recorded is None:
        sys.exit(f"ERROR: {dest} existe pero no está en el manifiesto; no la toco")
    if tree_hash(dest) != recorded:
        sys.exit(f"ERROR: {dest} cambió desde que se registró; no la toco")
    new, old = files_of(stage), files_of(dest)
    extra = sorted(set(old) - set(new))
    if extra:
        sys.exit(f"ERROR: la copia instalada tiene archivos que la nueva no tiene: {extra[:5]}")
    changed = [r for r in sorted(new) if r not in old or open(new[r], "rb").read() != open(old[r], "rb").read()]
    if not changed:
        return "sin cambios"
    if dry:
        return "actualizaría: " + ", ".join(changed)
    for r in changed:
        target = os.path.join(dest, r)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(new[r], target)
    manifest_set(dest, tree_hash(dest))
    return "actualizada: " + ", ".join(changed)


def cmd_list(cat):
    for scn in cat["scenarios"]:
        src = cat["sources"][scn["source"]]
        binp, dest = source_bin(cat, scn), dest_of(cat, scn)
        if not binp:
            state = (f'falta generar {src["path"]} (tools/vio_port.py build)' if src.get("path") else
                     f'falta descargar {src["title"]} (Workshop {src["workshop"]})')
        elif not os.path.exists(dest):
            state = "lista para instalar"
        else:
            state = "instalada" + ("" if tree_hash(dest) == manifest_tree_hash(dest) else " (CAMBIADA a mano)")
        print(f'{scn["id"]:20} {map_of(cat, scn):22} {scn["name"]}\n{"":20} -> {state}')


def cmd_build(cat, ids, dry):
    wanted = [s for s in cat["scenarios"] if "all" in ids or s["id"] in ids]
    unknown = set(ids) - {s["id"] for s in cat["scenarios"]} - {"all"}
    if unknown:
        sys.exit(f"ERROR: escenarios desconocidos: {', '.join(sorted(unknown))}")
    for scn in wanted:
        binp = source_bin(cat, scn)
        if not binp:
            src = cat["sources"][scn["source"]]
            print(f'- {scn["id"]}: se omite, ' + (f'falta generar {src["path"]} (tools/vio_port.py build)' if src.get("path")
                                                  else f'falta descargar {src["title"]}'))
            continue
        stage, log = build_stage(cat, scn, binp)
        result = install_or_update(stage, dest_of(cat, scn), dry)
        if not dry:
            shutil.rmtree(stage)
        print(f'- {scn["id"]}: {result}\n  carpeta: {dest_of(cat, scn)}')
        for line in log.splitlines():
            if line.startswith("  - "):
                print("  " + line)


def launch_section():
    """Las líneas de LAUNCH_OPTIONS.txt, con su comentario, como bloques copiables."""
    p = os.path.join(PROJECT, "LAUNCH_OPTIONS.txt")
    if not os.path.exists(p):
        return []
    lines = open(p, encoding="utf-8").read().splitlines()
    out = ["## Cómo lanzar el juego (líneas de Steam)", "",
           "En **Steam → Arma 3 → Propiedades → General → Opciones de lanzamiento** pega **una** línea, según lo que vayas a jugar. "
           "Después de cambiarla, cierra y vuelve a abrir el juego. Para jugar sin mods, borra el texto. "
           "Las mismas líneas están en `LAUNCH_OPTIONS.txt`.", ""]
    # Nota de la cabecera (las líneas de comentario después de "Pega UNA línea", hasta la primera línea en blanco).
    note = []
    for line in lines[2:]:
        if not line.startswith("#"):
            break
        note.append(line.lstrip("# ").strip())
    if note:
        out += [" ".join(note), ""]
    comment, legend = [], []
    for line in lines:
        if line.startswith("# LEYENDA"):
            legend, comment = [line.lstrip("# ").strip()], []
        elif legend and line.startswith("#"):
            legend += [x for x in line.lstrip("# ").split("  ") if x.strip()]
        elif line.startswith(("-mod=", "-par=")):
            text = " ".join(c.lstrip("# ").strip() for c in comment) or "Línea"
            title, _, detail = text.partition(": ")
            out += [f"**{title}**", ""] + ([detail[:1].upper() + detail[1:], ""] if detail else []) + ["```", line, "```", ""]
            comment = []
        elif line.startswith("# ") and line[2:3].isdigit():
            comment = [line]
        elif line.startswith("#") and comment:
            comment.append(line)
    if legend:
        title = legend[0].rstrip(":")
        out += [f"**{title[:1].upper() + title[1:]}**", "", "| Nombre corto | Mod |", "|---|---|"]
        out += [f"| `{k}` | {v} |" for k, _, v in (x.partition("=") for x in legend[1:])]
        out.append("")
    return out


def sanitize_public(text):
    """Quita el usuario del Mac de un texto para publicarlo (repo): C:/Users/<yo>/ -> C:/Users/<usuario>/, /Users/<yo>/ -> ~/."""
    me = os.path.basename(os.path.expanduser("~"))
    text = text.replace(f"C:/Users/{me}/", "C:/Users/<usuario>/").replace(f"C:\\Users\\{me}\\", "C:\\Users\\<usuario>\\")
    text = text.replace(f"/Users/{me}/", "~/").replace(f"/Users/{me}", "~")
    if me and me in text:
        sys.exit(f"ERROR: el texto publico aun menciona '{me}'")
    return text


def doc_lines(cat, public=False):
    """ESCENARIOS.md (public=False: con el estado de esta maquina) o docs/ESCENARIOS.md (public=True: sin estado ni rutas propias)."""
    out = ["# Escenarios configurados", "",
           "Generado por `tools/vio_build.py doc` desde `tools/vio_catalog.json` y `LAUNCH_OPTIONS.txt`.", ""]
    if public:
        out += ["Las rutas `C:/Users/<usuario>/m/...` son la carpeta `~/m` vista desde el juego (el puerto de Mac la ve como "
                "`C:/Users/<tu usuario del Mac>`): cambia `<usuario>` por tu usuario. Plantillas en `docs/launch/`.", ""]
        out += [x.replace("están en `LAUNCH_OPTIONS.txt`", "están en `docs/launch/LAUNCH_OPTIONS.txt`") for x in launch_section()]
    else:
        out += launch_section()
    # Guía de parámetros del lobby, escrita a mano en tools/vio_doc_params.md (empieza con su propio "## ...").
    params = os.path.join(HERE, "vio_doc_params.md")
    if os.path.exists(params):
        out += open(params, encoding="utf-8").read().rstrip("\n").splitlines() + [""]
    out += ["## Misiones CW (Warfare)", "",
            "Se juegan con la **línea 6** (las de Tanoa, con la **10**; \"CW: Selva 2026\", con la **1V**), en **MULTIPLAYER → SERVER BROWSER → Host Server (LAN)**: eliges el mapa a la izquierda "
            "y la misión a la derecha. Todas empiezan por \"CW:\" (o \"BECTI clásica\") para encontrarlas juntas. "
            "Cada una guarda su partida por separado. Las marcadas \"Requiere CUP y RHS\" también: esas líneas ya traen RHS.", ""]
    by_map = {}
    for scn in cat["scenarios"]:
        by_map.setdefault(map_of(cat, scn), []).append(scn)
    for mp, scns in by_map.items():
        out += [f"### {mp}", ""]
        for scn in scns:
            src = cat["sources"][scn["source"]]
            if public:
                origin = (f'[{src["title"]}](https://steamcommunity.com/sharedfiles/filedetails/?id={src["workshop"]})'
                          if src.get("workshop") else f'`{src.get("path", "?")}` (`tools/vio_port.py build`)')
                out += [f'- **{scn["name"]}**', f'  - {scn["overview"]}', f'  - Se arma desde: {origin}',
                        f'  - Carpeta: `mpmissions/{scn["folder"]}.{world_of(cat, scn)}`']
                continue
            state = "instalada" if os.path.exists(dest_of(cat, scn)) else (
                "lista para instalar" if source_bin(cat, scn) else
                f'falta generar `{src["path"]}` (`tools/vio_port.py build`)' if src.get("path") else
                f'falta descargar [{src["title"]}](https://steamcommunity.com/sharedfiles/filedetails/?id={src["workshop"]})')
            out += [f'- **{scn["name"]}** ({state})', f'  - {scn["overview"]}',
                    f'  - Carpeta: `mpmissions/{scn["folder"]}.{world_of(cat, scn)}`']
        out.append("")
    if cat.get("others"):
        out += ["## Otras misiones y campañas", ""]
        for o in cat["others"]:
            out += [f'- **{o["name"]}**', f'  - Dónde: {o["where"]}', f'  - Línea de lanzamiento: {o["line"]}',
                    f'  - Ojo: {o["notes"]}']
        out.append("")
    return out


def cmd_doc(cat):
    with open(os.path.join(PROJECT, "ESCENARIOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(doc_lines(cat)))
    print("ESCENARIOS.md actualizado")
    # Copias para el repo publico (docs/): sin el usuario del Mac ni el estado de esta maquina.
    docs = os.path.join(PROJECT, "docs")
    os.makedirs(os.path.join(docs, "launch", "par"), exist_ok=True)
    with open(os.path.join(docs, "ESCENARIOS.md"), "w", encoding="utf-8") as f:
        f.write(sanitize_public("\n".join(doc_lines(cat, public=True))))
    srcs = [("LAUNCH_OPTIONS.txt", os.path.join("launch", "LAUNCH_OPTIONS.txt"))]
    par_dir = os.path.join(PROJECT, "par")
    if os.path.isdir(par_dir):
        for old in glob.glob(os.path.join(docs, "launch", "par", "*.txt")):
            if not os.path.exists(os.path.join(par_dir, os.path.basename(old))):
                os.remove(old)
        srcs += [(os.path.join("par", n), os.path.join("launch", "par", n)) for n in sorted(os.listdir(par_dir)) if n.endswith(".txt")]
    for src, dst in srcs:
        sp = os.path.join(PROJECT, src)
        if os.path.exists(sp):
            with open(sp, encoding="utf-8") as f:
                txt = sanitize_public(f.read())
            with open(os.path.join(docs, dst), "w", encoding="utf-8") as f:
                f.write(txt)
    print(f"docs/ESCENARIOS.md y docs/launch/ actualizados (sin rutas propias; {len(srcs)} archivos de lanzamiento)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("cmd", choices=["list", "build", "doc"])
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args()
    cat = json.load(open(CATALOG, encoding="utf-8"))
    if a.cmd == "list":
        cmd_list(cat)
    elif a.cmd == "build":
        if not a.ids:
            sys.exit("ERROR: indica los escenarios o 'all'")
        cmd_build(cat, a.ids, a.dry_run)
    else:
        cmd_doc(cat)


if __name__ == "__main__":
    main()
