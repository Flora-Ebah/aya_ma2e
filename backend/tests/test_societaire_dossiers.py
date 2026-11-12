"""Tests : les sociétaires importés apparaissent dans la page « Dossiers ».

Couvre, sans base de données :
  A. conversion sociétaire -> utilisateur final / données du dossier (clés lues par la fiche PDF)
  B. sync_dossiers avec une fausse session : création, mise à jour, statut jamais écrasé,
     unicité du n° de sociétaire, lots
  C. fiche PDF d'un dossier importé : nom composé, téléphone, consentement
  D. API Dossiers : filtre d'origine, recherche, pagination et total côté serveur (SQL généré)
  E. Reporting : toutes les requêtes excluent la base importée ; anti-doublon sans MultipleResultsFound
  F. liens : import et chat déclenchent la synchronisation

Lancer :
    python -m tests.test_societaire_dossiers
"""
from __future__ import annotations

import asyncio
import inspect
import io
import os
import re
import sys
import types
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import DonneesPro, Dossier, DossierStatus, EndUser, Societaire  # noqa: E402
from app.services import societaire_dossiers as sd  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
CHECKS = 0


def _assert(cond: bool, msg: str) -> None:
    global CHECKS
    if not cond:
        print(f"FAIL: {msg}", file=sys.stderr)
        raise AssertionError(msg)
    CHECKS += 1


def _soc(**over) -> Societaire:
    base = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), id_client="A0100003", code_client="A0104688",
        matricule="016126G", matricule_norm="016126G", nom="SOUMAHORO", prenoms="FALIKOU",
        civilite="M", statut_matrimonial="M", date_naissance=date(1978, 12, 13),
        lieu_naissance="ZOUANHOUNIEN", type_piece="Attestation d'Identité", numero_piece="CI001490454",
        telephone="01 42 87 84 80/07 07 04 73 92", telephone_norm="0142878480", email="f@x.ci",
        adresse="Trechville", boite_postale="01 BP 1", profession="DIRECTEUR REGIONAL",
        employeur_code="SODECI", categorie_client="CADRE", date_adhesion=date(2008, 5, 9),
        nom_mere="KONE FANTA", consentement_recu=True, actif=True, extra={},
        personne_a_prevenir="KONE AWA - 0701020304",
    )
    base.update(over)
    return Societaire(**base)


# ---------------------------------------------------------------- fausse session
class _Res:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class _FakeDB:
    """Répond aux 3 SELECT de sync_dossiers (dossiers existants, utilisateurs, n° pris)."""

    def __init__(self, dossiers=(), end_users=(), taken=()):
        self.dossiers, self.end_users, self.taken = list(dossiers), list(end_users), list(taken)
        self.added: list = []
        self.flushes = 0

    async def execute(self, stmt):
        sql = str(stmt)
        if "FROM dossiers" in sql and "numero_societaire IN" in sql:
            return _Res(self.taken)
        if "FROM dossiers" in sql:
            return _Res(self.dossiers)
        if "FROM end_users" in sql:
            return _Res(self.end_users)
        raise AssertionError(f"requête inattendue : {sql[:80]}")

    def add(self, o):
        self.added.append(o)

    def add_all(self, objs):
        self.added.extend(objs)

    async def flush(self):
        self.flushes += 1


def _run(socs, db=None):
    db = db or _FakeDB()
    out = asyncio.run(sd.sync_dossiers(db, socs[0].tenant_id if socs else uuid.uuid4(), socs))
    return db, out


def _of(db, cls):
    return [o for o in db.added if isinstance(o, cls)]


# =========================================================================== A
def test_conversion() -> None:
    s = _soc()
    eu = sd.end_user_values(s)
    _assert(eu["name"] == "FALIKOU SOUMAHORO", "nom affiché : « PRÉNOMS NOM »")
    _assert(eu["extra"]["nom"] == "SOUMAHORO" and eu["extra"]["prenoms"] == "FALIKOU", "nom / prénoms séparés")
    _assert(eu["extra"]["telephone"] == "0142878480" and eu["extra"]["email"] == "f@x.ci", "coordonnées dans extra")
    _assert(eu["extra"]["origine"] == sd.ORIGINE_IMPORT, "origine marquée")
    _assert("phone" not in eu, "PAS de téléphone d'utilisateur final (aucun rattachement WhatsApp par erreur)")

    dp = sd.donnees_values(s)
    _assert(dp["fonction"] == "DIRECTEUR REGIONAL" and dp["situation_familiale"] == "marie", "fonction / situation")
    e = dp["extra"]
    _assert(e["civilite"] == "M." and e["date_naissance"] == "1978-12-13", "civilité et date au format de la fiche")
    _assert(e["domicile"] == "Trechville" and e["boite_postale"] == "01 BP 1", "domicile / boîte postale")
    _assert(e["categorie"] == "CADRE" and e["nom_mere"] == "KONE FANTA", "catégorie / mère")
    _assert(e["personne_a_prevenir"] == "KONE AWA" and e["contact_prevenir_1"] == "0701020304",
            "« NOM - téléphone » séparé en nom et contact")
    _assert(e["consentement_recu"] is True, "consentement reporté")

    vide = sd.donnees_values(_soc(adresse=None, email=None, consentement_recu=None, civilite="Mme", statut_matrimonial="D"))
    _assert("domicile" not in vide["extra"] and "consentement_recu" not in vide["extra"],
            "valeurs vides non écrites (ne pas effacer une donnée existante)")
    _assert(vide["extra"]["civilite"] == "Mme" and vide["situation_familiale"] == "divorce", "Mme / divorcé(e)")


# =========================================================================== B
def test_sync() -> None:
    s = _soc()
    db, (c, u) = _run([s])
    _assert((c, u) == (1, 0), "1 dossier créé")
    d, eu, dp = _of(db, Dossier)[0], _of(db, EndUser)[0], _of(db, DonneesPro)[0]
    _assert(d.societaire_id == s.id and d.end_user_id == eu.id and dp.dossier_id == d.id, "liens dossier / utilisateur / données")
    _assert(d.status == DossierStatus.valide, "statut « valide » (déjà adhérent)")
    _assert(d.dossier_number == "IMP-A0100003", "n° de dossier IMP-<id client>")
    _assert(d.numero_societaire == "A0104688", "code client = n° de sociétaire (champ « Code » de la fiche)")
    _assert(d.matricule == "016126G" and d.employeur_code == "SODECI", "matricule / employeur")
    _assert(d.submitted_at == datetime(2008, 5, 9, tzinfo=timezone.utc), "« Soumis le » = date d'adhésion")
    _assert(db.flushes == 1, "un seul flush par lot")

    # n° de sociétaire déjà pris : on ne casse pas la contrainte d'unicité
    db, _ = _run([_soc()], _FakeDB(taken=["A0104688"]))
    _assert(_of(db, Dossier)[0].numero_societaire is None, "code client déjà pris -> pas de n° de sociétaire")
    # deux sociétaires du même lot avec le même code client
    a, b = _soc(id_client="A1", code_client="DUP"), _soc(id_client="A2", code_client="DUP")
    db, _ = _run([a, b])
    nums = [d.numero_societaire for d in _of(db, Dossier)]
    _assert(nums == ["DUP", None], f"doublon de code client dans le lot : {nums}")
    # matricule trop long pour la colonne dossiers (32)
    db, _ = _run([_soc(matricule="X" * 50)])
    _assert(len(_of(db, Dossier)[0].matricule) == 32, "matricule tronqué à 32 caractères")

    # lots
    n = sd.BATCH * 2 + 5
    db, (c, u) = _run([_soc(id=uuid.uuid4(), id_client=f"B{i}", code_client=f"C{i}") for i in range(n)])
    _assert(c == n and db.flushes == 3, f"{n} sociétaires -> 3 lots")

    # mise à jour d'un dossier existant : données réécrites, statut / n° conservés
    s = _soc(nom="SOUMAHORO", telephone_norm="0707070707")
    old_eu = EndUser(id=uuid.uuid4(), tenant_id=s.tenant_id, name="ANCIEN", extra={"note": "garde"})
    old = Dossier(id=uuid.uuid4(), tenant_id=s.tenant_id, dossier_number="IMP-A0100003", end_user_id=old_eu.id,
                  societaire_id=s.id, status=DossierStatus.rejete, numero_societaire="KEEP")
    old.donnees_pro = DonneesPro(tenant_id=s.tenant_id, dossier_id=old.id, extra={"observations": "agent"})
    db, (c, u) = _run([s], _FakeDB(dossiers=[old], end_users=[old_eu]))
    _assert((c, u) == (0, 1) and db.added == [], "dossier existant : mis à jour, rien de recréé")
    _assert(old.status == DossierStatus.rejete, "le STATUT décidé par un agent n'est JAMAIS écrasé")
    _assert(old.numero_societaire == "KEEP", "n° de sociétaire conservé")
    _assert(old_eu.name == "FALIKOU SOUMAHORO" and old_eu.extra["telephone"] == "0707070707", "utilisateur mis à jour")
    _assert(old_eu.extra["note"] == "garde", "extra fusionné (clés étrangères conservées)")
    _assert(old.donnees_pro.extra["observations"] == "agent" and old.donnees_pro.extra["nom_mere"] == "KONE FANTA",
            "données fusionnées : observation d'agent conservée, nouvelles valeurs ajoutées")


# =========================================================================== C
def test_fiche() -> None:
    from app.services.fiche_pdf import generate_fiche_pdf
    import pymupdf

    s = _soc(nom="KONE TRAORE", prenoms="AWA MARIE", telephone_norm="0707070707", email="awa@x.ci")
    db, _ = _run([s])
    d, eu, dp = _of(db, Dossier)[0], _of(db, EndUser)[0], _of(db, DonneesPro)[0]
    d.donnees_pro, d.end_user, d.pieces, d.consentements = dp, eu, [], []
    d.created_at = datetime(2026, 11, 10, tzinfo=timezone.utc)
    text = pymupdf.open(stream=generate_fiche_pdf(d, "Test"), filetype="pdf")[0].get_text()
    for expected, what in [("KONE TRAORE", "nom composé entier (pas « TRAORE » seul)"), ("AWA MARIE", "prénoms"),
                           ("0707070707", "téléphone"), ("awa@x.ci", "e-mail"), ("A0104688", "code client"),
                           ("13/12/1978", "date de naissance"), ("KONE FANTA", "nom de la mère"),
                           ("OUI", "consentement reçu"), ("Marié(e)", "situation matrimoniale")]:
        _assert(expected in text, f"fiche PDF : {what}")


# =========================================================================== D
def test_api_dossiers() -> None:
    from app.api import dossiers as api
    src = inspect.getsource(api.list_dossiers)
    p = inspect.signature(api.list_dossiers).parameters
    for name in ("q", "origine", "offset", "limit"):
        _assert(name in p, f"paramètre {name} exposé")
    _assert(p["offset"].default.default == 0, "offset 0 par défaut")
    _assert("Dossier.societaire_id.is_not(None)" in src and "Dossier.societaire_id.is_(None)" in src,
            "filtre d'origine : import / inscription")
    _assert("regexp_replace" in src and "norm_matricule" in src, "recherche de matricule insensible à la casse et aux séparateurs")
    _assert('EndUser.extra["telephone"]' in src, "recherche sur le téléphone des dossiers importés")
    _assert(".offset(offset).limit(limit)" in src, "pagination côté serveur")
    _assert("func.count(func.distinct(Dossier.id))" in src, "total calculé sur TOUS les dossiers filtrés")
    _assert("Dossier.dossier_number" in src.split("# Tri", 1)[1], "tri stable (départage par n° de dossier)")
    _assert("total=total" in src and "by_status_rows" in src, "le total et le récapitulatif sont renvoyés")
    _assert('origine="import" if d.societaire_id else "inscription"' in src, "origine exposée sur chaque ligne")

    from app.schemas.dossier import DossierListItem, DossierListResponse
    _assert("origine" in DossierListItem.model_fields and "total" in DossierListResponse.model_fields,
            "schéma : origine et total")
    _assert(DossierListItem.model_fields["origine"].default == "inscription", "origine par défaut = inscription")


# =========================================================================== E
def test_reporting_and_duplicates() -> None:
    stats_src = (BACKEND / "app/services/stats_service.py").read_text(encoding="utf-8")
    nb_tenant = len(re.findall(r"Dossier\.tenant_id == tenant_id", stats_src))
    nb_excl = len(re.findall(r"Dossier\.tenant_id == tenant_id, Dossier\.societaire_id\.is_\(None\)", stats_src))
    _assert(nb_tenant == nb_excl and nb_tenant >= 14,
            f"Reporting : les {nb_tenant} requêtes sur les dossiers excluent la base importée ({nb_excl})")

    from app.conversation import default_actions as da
    src = inspect.getsource(da.check_duplicates)
    code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))  # sans les commentaires
    _assert("scalar_one_or_none" not in code, "anti-doublon : plus de MultipleResultsFound (2 dossiers, même matricule)")
    _assert(".limit(1)" in src and ".scalars().first()" in src, "anti-doublon : premier dossier seulement")
    _assert("norm_matricule" in src, "anti-doublon : matricule comparé sans casse ni séparateurs")

    # les statistiques de la page Dossiers (cartes) comptent bien la base importée : pas d'exclusion
    from app.api import dossiers as api
    _assert("societaire_id" not in inspect.getsource(api.stats), "cartes de la page Dossiers : incluent la base importée")


# =========================================================================== F
def test_wiring() -> None:
    imp = (BACKEND / "app/services/societaire_import.py").read_text(encoding="utf-8")
    _assert("sync_dossiers" in imp and "report.dossiers_created" in imp, "l'import crée les dossiers")
    _assert(imp.index("await db.execute(stmt)") < imp.index("sync_dossiers"), "dossiers créés APRÈS l'écriture des sociétaires")
    _assert("sync_dossiers" in (BACKEND / "app/conversation/societaire_actions.py").read_text(encoding="utf-8"),
            "une modification par chat met à jour le dossier")
    from app.services.importer_service import ImportReport
    r = ImportReport(target="societaires")
    _assert(r.dossiers_created == 0 and r.dossiers_updated == 0, "rapport : compteurs de dossiers")
    # modèle + migration
    _assert("societaire_id" in Dossier.__table__.columns and Dossier.__table__.columns["societaire_id"].unique,
            "dossiers.societaire_id (unique)")
    boot = (BACKEND / "app/bootstrap.py").read_text(encoding="utf-8")
    _assert("ADD COLUMN IF NOT EXISTS societaire_id" in boot, "migration idempotente pour une base existante")
    # la page « Sociétaires MA2E » est supprimée
    _assert(not (BACKEND / "app/api/societaires.py").exists(), "ancienne API /api/societaires supprimée")
    _assert("societaires_api" not in (BACKEND / "app/main.py").read_text(encoding="utf-8"), "routeur retiré de main.py")
    front = BACKEND.parent / "frontend"
    _assert(not (front / "app/(app)/(workspace)/societaires").exists(), "ancienne page supprimée")
    _assert("/societaires" not in (front / "lib/sidebar-configs.ts").read_text(encoding="utf-8"), "menu supprimé")


def main() -> int:
    for t in (test_conversion, test_sync, test_fiche, test_api_dossiers, test_reporting_and_duplicates, test_wiring):
        t()
        print(f"  ✓ {t.__name__}")
    print(f"OK — tous les asserts passent ({CHECKS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
