import { Icon } from "@/components/Icon";
import { Card } from "@/components/ui/Card";
import { Grid } from "@/components/ui/Grid";

const INFO_CARDS: Array<{ title: string; body: string; icon: string }> = [
  {
    title: "Qui collecte ?",
    icon: "building-03",
    body: "MA2E, identifiée comme responsable du traitement, par l'intermédiaire de la plateforme digitale opérée par le groupe ERANOVE.",
  },
  {
    title: "Quelles données ?",
    icon: "identity-card",
    body: "Identité (CNI), coordonnées (téléphone, email), matricule employeur, situation familiale, RIB si vous l'avez fourni.",
  },
  {
    title: "Combien de temps ?",
    icon: "clock-01",
    body: "5 ans après votre dernière activité comme sociétaire, conformément à l'article 36 de la loi 2013-450.",
  },
];

export function InfoCardsSection() {
  return (
    <section aria-labelledby="info-cles">
      <h2 id="info-cles" className="sa-sr-only">Informations clés</h2>
      <Grid variant="stats3">
        {INFO_CARDS.map((c) => (
          <article key={c.title} className="sa-card">
            <span className="sa-icon-tile" aria-hidden="true">
              <Icon name={c.icon} />
            </span>
            <h3 className="sa-card__title--sm sa-card__title">{c.title}</h3>
            <p className="sa-body">{c.body}</p>
          </article>
        ))}
      </Grid>
    </section>
  );
}

export function RightsSection() {
  return (
    <section aria-labelledby="vos-droits">
      <Card title={<span id="vos-droits">Vos 5 droits ARTCI</span>}>
        <ol className="ma2e-rights">
          <Right n="1" title="Droit d'accès (article 18)">
            Vous pouvez à tout moment demander une copie de toutes les données que MA2E
            détient sur vous. Réponse sous <strong>30 jours</strong>.
            <br />
            <em>Comment ?</em> Tapez <Cmd>mes données</Cmd> sur WhatsApp ou le chat web,
            ou utilisez le formulaire en bas de page.
          </Right>
          <Right n="2" title="Droit de rectification (article 19)">
            Vous pouvez corriger toute donnée inexacte ou obsolète vous concernant.
            <br />
            <em>Comment ?</em> Tapez <Cmd>corriger mes données</Cmd> sur le chat.
            L&apos;assistante vous guide.
          </Right>
          <Right n="3" title="Droit à l'effacement / droit à l'oubli (article 21)">
            Vous pouvez demander la suppression de vos données après votre désaffiliation,
            sauf obligation légale contraire (durée comptable, par exemple).
            <br />
            <em>Comment ?</em> Tapez <Cmd>supprimer mon dossier</Cmd> ou utilisez le formulaire ci-dessous.
          </Right>
          <Right n="4" title="Droit d'opposition (article 22)">
            Vous pouvez vous opposer au traitement de vos données à des fins de
            communication, sondages, marketing ou tout autre usage qui sort de la mission de mutuelle.
          </Right>
          <Right n="5" title="Droit au retrait du consentement">
            Tout consentement donné peut être retiré à tout moment. Le retrait ne remet pas
            en cause la licéité des traitements effectués avant.
            <br />
            <em>Comment ?</em> Tapez <Cmd>retirer consentement</Cmd>.
          </Right>
        </ol>
      </Card>
    </section>
  );
}

export function DpoContactSection() {
  const dpoEmail = "dpo@ma2e.ci";
  return (
    <section aria-labelledby="contact-dpo">
      <Card title={<span id="contact-dpo">Contacter notre Délégué à la Protection des Données (DPO)</span>}>
        <p className="sa-body">
          Pour toute question, réclamation ou exercice de droits, vous pouvez écrire à
          notre DPO. Délai légal de réponse : <strong>30 jours</strong> (prolongeable de 30
          jours sur justification).
        </p>
        <p className="sa-row" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Icon name="mail-01" className="sa-text-brand" />
          <a href={`mailto:${dpoEmail}`} className="sa-link sa-strong">
            {dpoEmail}
          </a>
        </p>
        <p className="sa-body-sm sa-text-soft">
          En cas de non-réponse ou de réponse insatisfaisante, vous pouvez introduire une réclamation
          auprès de l&apos;<strong>Autorité de Régulation des Télécommunications de Côte d&apos;Ivoire (ARTCI)</strong>{" "}
          :{" "}
          <a href="https://www.artci.ci" target="_blank" rel="noreferrer" className="sa-link">
            www.artci.ci
          </a>
          .
        </p>
      </Card>
    </section>
  );
}

function Right({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <li className="ma2e-rights__item">
      <span className="sa-section-title__num" aria-hidden="true">{n}</span>
      <div>
        <h3 className="sa-h5">{title}</h3>
        <div className="sa-body">{children}</div>
      </div>
    </li>
  );
}

function Cmd({ children }: { children: React.ReactNode }) {
  return <code className="sa-mono ma2e-cmd">{children}</code>;
}
