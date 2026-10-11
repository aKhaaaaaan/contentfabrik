"""Verhindert, dass Ersatzmaterial die zugesagte Zahl unterschiedlicher Motive verbraucht."""


def neues_noetig(benutzt, verbleibend, minimum):
    return len(benutzt) + verbleibend < minimum


def erlaubt(material_id, benutzt, verbleibend, minimum):
    return bool(material_id) and (material_id not in benutzt
                                 or not neues_noetig(benutzt, verbleibend, minimum))
