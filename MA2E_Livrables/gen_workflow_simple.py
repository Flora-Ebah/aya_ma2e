"""BPMN MA2E — vue dirigeant, 7 étapes numérotées, avec consentement ARTCI.

Exécution :
    pip install graphviz
    # + binaire graphviz : https://graphviz.org/download/
    python gen_workflow_simple.py
→ produit `ma2e_workflow_simple.png`.

Sur Google Colab :
    !apt-get -qq install -y graphviz && pip install -q graphviz
puis coller ce script.
"""
from graphviz import Digraph

g = Digraph('MA2E_Workflow_simple', format='png')
g.attr(rankdir='LR', splines='ortho', nodesep='0.55', ranksep='1.0',
       bgcolor='white', dpi='180', pad='0.4', fontname='Helvetica')

g.attr('node', fontname='Helvetica-Bold', fontsize='11',
       style='filled,rounded', penwidth='1.5', margin='0.22,0.14')
g.attr('edge', fontname='Helvetica-Bold', fontsize='10',
       color='#555555', arrowsize='0.85')

ACT = dict(shape='box',     fillcolor='#D4E6F4', color='#5B9BD5')
GW  = dict(shape='diamond', fillcolor='#FFF2CC', color='#BF9000',
           width='0.8', height='0.7')


def start_node(c, name):
    c.node(name, '', shape='circle', fillcolor='#70AD47', color='#385723',
           width='0.42', height='0.42', fixedsize='true', penwidth='3')


def end_ok(c, name, text):
    c.node(name, '', shape='circle', fillcolor='#70AD47', color='#385723',
           width='0.48', height='0.48', fixedsize='true', penwidth='4.5',
           xlabel=f'<<I><FONT COLOR="#385723" POINT-SIZE="10">{text.replace(chr(10),"<BR/>")}</FONT></I>>')


def end_ko(c, name, text):
    c.node(name, '', shape='circle', fillcolor='#E06666', color='#B71C1C',
           width='0.52', height='0.52', fixedsize='true', penwidth='4',
           xlabel=f'<<I><FONT COLOR="#B71C1C" POINT-SIZE="10">{text.replace(chr(10),"<BR/>")}</FONT></I>>')


def end_warn(c, name, text):
    c.node(name, '', shape='circle', fillcolor='#FFB74D', color='#E65100',
           width='0.50', height='0.50', fixedsize='true', penwidth='4',
           xlabel=f'<<I><FONT COLOR="#E65100" POINT-SIZE="10">{text.replace(chr(10),"<BR/>")}</FONT></I>>')


def gw_node(c, name, question):
    c.node(name, '', xlabel=f'<<I><FONT POINT-SIZE="10">{question}</FONT></I>>', **GW)


# -------- Numérotation des flèches (1)→(7) -----------------------------
# On garantit qu'une seule flèche par étape porte le badge numéroté,
# placé EN TÊTE pour qu'on suive 1→7 sans hésitation.
def badge(n, text=None):
    """Badge bleu (n) bien visible + libellé optionnel."""
    inner = (
        f'<TABLE BORDER="0" CELLBORDER="0" CELLPADDING="2"><TR>'
        f'<TD BGCOLOR="#1565C0"><FONT COLOR="white" POINT-SIZE="14"><B> {n} </B></FONT></TD>'
    )
    if text:
        inner += f'<TD><FONT POINT-SIZE="10"><B>{text}</B></FONT></TD>'
    inner += '</TR></TABLE>'
    return f'<{inner}>'


# =========================================================
# LANE 1 — SOCIÉTAIRE
# =========================================================
with g.subgraph(name='cluster_societaire') as c:
    c.attr(label='SOCIÉTAIRE', labeljust='l', style='rounded,filled',
           fillcolor='#FAFAFA', color='#9E9E9E', fontsize='14',
           fontname='Helvetica-Bold', fontcolor='#424242')
    start_node(c, 'S_start')
    c.node('S1', 'Démarre la\nconversation',         **ACT)
    gw_node (c, 'S_consent', 'Accepte\nla notice ?')
    c.node('S2', 'Donne ses infos\n(matricule, CNI)', **ACT)
    c.node('S3', 'Confirme les\ndonnées extraites',   **ACT)
    c.node('S4', 'Reçoit la\nnotification',           **ACT)
    end_ok  (c, 'S_end_val',  'Enrôlement\nterminé')
    end_ko  (c, 'S_end_rej',  'Inscription\nrefusée')
    end_warn(c, 'S_end_comp', 'Complément\nattendu')
    end_ko  (c, 'S_end_no',   'Consentement\nrefusé')

    c.edge('S_start', 'S1')
    # Notice ARTCI : choix Oui/Non
    c.edge('S_consent', 'S2',        label='Oui', fontcolor='#2E7D32')
    c.edge('S_consent', 'S_end_no',  label='Non', fontcolor='#C62828')
    c.edge('S2', 'S3')
    c.edge('S3', 'S4')
    c.edge('S4', 'S_end_val',  color='#70AD47', penwidth='1.5')
    c.edge('S4', 'S_end_rej',  color='#E06666', penwidth='1.5')
    c.edge('S4', 'S_end_comp', color='#FFB74D', penwidth='1.5')

# =========================================================
# LANE 2 — PLATEFORME MA2E
# =========================================================
with g.subgraph(name='cluster_back') as c:
    c.attr(label='PLATEFORME MA2E', labeljust='l',
           style='rounded,filled', fillcolor='#FAFAFA', color='#9E9E9E',
           fontsize='14', fontname='Helvetica-Bold', fontcolor='#424242')
    c.node('B1', 'Accueille\net guide',                                **ACT)
    c.node('B_notice', 'Présente la\nnotice ARTCI',                    **ACT)
    c.node('B2', 'Contrôles automatiques\n(matricule · OCR · doublon)', **ACT)
    c.node('B3', 'Dossier en attente\nde validation',                  **ACT)
    c.node('B4', "Envoie l'email\nde notification",                    **ACT)
    c.edge('B1', 'B_notice')
    c.edge('B_notice', 'B2', style='invis')  # alignement vertical
    c.edge('B2', 'B3')

# =========================================================
# LANE 3 — AGENT MA2E
# =========================================================
with g.subgraph(name='cluster_agent') as c:
    c.attr(label='AGENT MA2E', labeljust='l', style='rounded,filled',
           fillcolor='#FAFAFA', color='#9E9E9E', fontsize='14',
           fontname='Helvetica-Bold', fontcolor='#424242')
    start_node(c, 'A_start')
    c.node('A1', 'Examine\nle dossier', **ACT)
    gw_node (c, 'GWA', 'Décision ?')
    c.node('A_val',  '✅ Valide',           **ACT)
    c.node('A_rej',  '❌ Rejette\n+ motif', **ACT)
    c.node('A_comp', '🔁 Demande\ncomplément', **ACT)
    c.edge('A_start', 'A1')
    c.edge('A1', 'GWA')

# =========================================================
# FLUX INTER-LANES — 7 flèches numérotées dans l'ordre
# =========================================================
DASH = dict(style='dashed', color='#90A4AE', constraint='false',
            arrowsize='0.9', penwidth='1.8')

# (1) Sociétaire démarre  → Plateforme accueille
g.edge('S1', 'B1',          label=badge(1, 'Démarrage'), **DASH)
# (2) Plateforme présente la notice ARTCI → Sociétaire
g.edge('B_notice', 'S_consent', label=badge(2, 'Notice ARTCI'), **DASH)
# (3) Sociétaire envoie matricule + CNI → Plateforme contrôle
g.edge('S2', 'B2',          label=badge(3, 'Infos transmises'), **DASH)
# (4) Plateforme → Agent : dossier prêt à examiner
g.edge('B3', 'A_start',     label=badge(4, 'Dossier soumis'), **DASH)
# (5) Agent prend une décision (3 issues)
g.edge('GWA', 'A_val',  label=badge(5, 'Valider'),    fontcolor='#2E7D32')
g.edge('GWA', 'A_rej',  label='Rejeter',              fontcolor='#C62828')
g.edge('GWA', 'A_comp', label='Compléter',            fontcolor='#E65100')
# (6) Agent → Plateforme : déclenche l'email
g.edge('A_val',  'B4', label=badge(6, 'Notifier'), **{**DASH, 'color': '#70AD47'})
g.edge('A_rej',  'B4', **{**DASH, 'color': '#E06666'})
g.edge('A_comp', 'B4', **{**DASH, 'color': '#FFB74D'})
# (7) Plateforme → Sociétaire : réception de l'email
g.edge('B4', 'S4', label=badge(7, 'Email reçu'), **DASH)

# =========================================================
# RENDU
# =========================================================
out = g.render('ma2e_workflow_simple', cleanup=True)
print(f"OK -> {out}")
