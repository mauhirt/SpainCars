"""
party_zbe_adoption_data.py

Hand-coded data on governing party (2019-2023 term) and ZBE implementation
status for >50k municipalities. Shared between scripts 12 and 12b.

Extracted from 12_party_zbe_adoption.py to allow reuse without circular imports.
"""

# ===================================================================
# GOVERNING PARTY 2019-2023 — hand-coded for >50k municipalities
# ===================================================================
# Format: cod_ine -> (municipality_name, party, bloc)

GOVERNING_PARTY_2019 = {
    "28079": ("Madrid", "PP", "right"),
    "08019": ("Barcelona", "BComú", "left"),
    "46250": ("València", "Compromís", "left"),
    "41091": ("Sevilla", "PSOE", "left"),
    "50297": ("Zaragoza", "PP", "right"),
    "29067": ("Málaga", "PP", "right"),
    "30030": ("Murcia", "PP", "right"),
    "07040": ("Palma", "PSOE", "left"),
    "35016": ("Las Palmas GC", "PSOE", "left"),
    "48020": ("Bilbao", "PNV", "right"),
    "03014": ("Alicante", "PP", "right"),
    "14021": ("Córdoba", "PSOE", "left"),
    "47186": ("Valladolid", "PSOE", "left"),
    "36057": ("Vigo", "PSOE", "left"),
    "33024": ("Gijón", "PSOE", "left"),
    "08101": ("L'Hospitalet", "PSC", "left"),
    "01059": ("Vitoria", "PNV", "right"),
    "15030": ("A Coruña", "PSOE", "left"),
    "03065": ("Elche", "PSOE", "left"),
    "18087": ("Granada", "PSOE", "left"),
    "08279": ("Terrassa", "PSOE", "left"),
    "08015": ("Badalona", "PP", "right"),
    "33044": ("Oviedo", "PP", "right"),
    "30016": ("Cartagena", "PSOE", "left"),
    "08187": ("Sabadell", "PSOE", "left"),
    "11020": ("Jerez", "PSOE", "left"),
    "28092": ("Móstoles", "PSOE", "left"),
    "38038": ("Sta Cruz Tenerife", "CC", "right"),
    "31201": ("Pamplona", "Navarra Suma", "right"),
    "04013": ("Almería", "PP", "right"),
    "28005": ("Alcalá de Henares", "PSOE", "left"),
    "28058": ("Fuenlabrada", "PSOE", "left"),
    "28074": ("Leganés", "PSOE", "left"),
    "20069": ("Donostia/SS", "Bildu", "left"),
    "28065": ("Getafe", "PSOE", "left"),
    "09059": ("Burgos", "PSOE", "left"),
    "02003": ("Albacete", "PP", "right"),
    "39075": ("Santander", "PP", "right"),
    "12040": ("Castellón", "PSOE", "left"),
    "28007": ("Alcorcón", "PSOE", "left"),
    "38023": ("La Laguna", "PSOE", "left"),
    "26089": ("Logroño", "PSOE", "left"),
    "06015": ("Badajoz", "PP", "right"),
    "37274": ("Salamanca", "PP", "right"),
    "21041": ("Huelva", "PSOE", "left"),
    "29069": ("Marbella", "PP", "right"),
    "25120": ("Lleida", "ERC", "left"),
    "43148": ("Tarragona", "ERC", "left"),
    "41038": ("Dos Hermanas", "PSOE", "left"),
    "28148": ("Torrejón", "PP", "right"),
    "28106": ("Parla", "PSOE", "left"),
    "08121": ("Mataró", "PSOE", "left"),
    "24089": ("León", "PSOE", "left"),
    "11004": ("Algeciras", "PP", "right"),
    "08245": ("Sta Coloma Gramenet", "PSOE", "left"),
    "28006": ("Alcobendas", "PSOE", "left"),
    "11012": ("Cádiz", "UP", "left"),
    "23050": ("Jaén", "PSOE", "left"),
    "32054": ("Ourense", "PP", "right"),
    "43123": ("Reus", "ERC", "left"),
    "08205": ("Sant Cugat", "JxCat", "right"),
    "08217": ("Sant Joan Despí", "PSOE", "left"),
    "28123": ("Rivas-Vaciamadrid", "UP", "left"),
    "36038": ("Pontevedra", "BNG", "left"),
    "08073": ("Cornellà", "PSOE", "left"),
    "08169": ("El Prat", "PSOE", "left"),
    "17079": ("Girona", "JxCat", "right"),
    "46131": ("Torrent", "Compromís", "left"),
    "03047": ("Benidorm", "PP", "right"),
    "08902": ("Castelldefels", "PP", "right"),
    "08307": ("Viladecans", "PSOE", "left"),
    "46220": ("Sagunto/Sagunt", "PSOE", "left"),
    "28150": ("Torrelodones", "PP", "right"),
    "10037": ("Cáceres", "PSOE", "left"),
    "30024": ("Lorca", "PP", "right"),
}


# ===================================================================
# ZBE STATUS — detailed coding
# ===================================================================
# Format: cod_ine -> (zbe_status, zbe_stringency, zbe_type, notes)

ZBE_STATUS = {
    "28079": ("enforced", 5, "label", "Madrid 360: full city, cameras, fines since 2021"),
    "08019": ("enforced", 5, "label", "Barcelona ZBE Rondes: 95km2, cameras, fines since 2020"),
    "08101": ("enforced", 5, "label", "Part of Barcelona AMB ZBE"),
    "08245": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08073": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08169": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08279": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08187": ("enforced", 4, "label", "Part of Barcelona AMB ZBE"),
    "08205": ("enforced", 3, "label", "Sant Cugat: 4km2, fines since Nov 2021"),
    "08217": ("enforced", 3, "label", "Sant Joan Despí: AMB regime"),
    "08015": ("enforced", 3, "label", "Badalona: trial year Mar 2023, later postponed to 2027"),
    "41091": ("nominal", 2, "relabel", "Sevilla: pre-existing restrictions relabeled; fines from Jul 2024"),
    "14021": ("nominal", 2, "relabel", "Córdoba: pre-existing ACIRE zones relabeled"),
    "36038": ("nominal", 2, "relabel", "Pontevedra: traffic-calmed since 1999, no label restrictions"),
    "15030": ("nominal", 2, "relabel", "A Coruña: pedestrianised areas renamed ZBE"),
    "28123": ("nominal", 1, "school", "Rivas: school-zone ZBE only"),
    "30016": ("nominal", 2, "relabel", "Cartagena: ordinance Mar 2023, supermanzanas focus"),
    "28148": ("nominal", 2, "paper", "Torrejón: ordinance Feb 2023, cameras not until Mar 2025"),
    "46250": ("delayed", 0, "none", "Valencia: APR declared ZBE Dec 2023"),
    "47186": ("delayed", 0, "none", "Valladolid: activated Nov 2024"),
    "48020": ("delayed", 0, "none", "Bilbao: activated Jun 2024"),
    "29067": ("delayed", 0, "none", "Málaga: informational phase Nov 2024"),
    "50297": ("delayed", 0, "none", "Zaragoza: activated Dec 2025"),
    "20069": ("delayed", 0, "none", "San Sebastián: activated Dec 2024"),
    "01059": ("delayed", 0, "none", "Vitoria: activated Sep 2025"),
    "09059": ("delayed", 0, "none", "Burgos: activated Aug 2025"),
    "39075": ("delayed", 0, "none", "Santander: activated Dec 2025"),
    "33024": ("delayed", 0, "none", "Gijón: ZBE derogated after May 2023 change of govt"),
}
