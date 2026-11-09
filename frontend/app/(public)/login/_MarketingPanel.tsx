"use client";
import Image from "next/image";
import { useEffect, useState } from "react";

const A = ({ children }: { children: React.ReactNode }) => (
  <strong className="ma2e-auth__em">{children}</strong>
);

const TAGLINES: { title: React.ReactNode; body: React.ReactNode }[] = [
  {
    title: <>Un <A>compagnon digital</A>, pas un formulaire</>,
    body: (
      <>
        Conçu pour <A>comprendre, guider et accompagner</A> chaque sociétaire avec
        naturel. Une conversation simple, fluide, qui vous mène de la première
        salutation à l&apos;enrôlement complet — sans jamais perdre votre fil.
      </>
    ),
  },
  {
    title: <>Une expérience pensée pour <A>vous</A></>,
    body: (
      <>
        Chaque échange est calibré pour <A>réduire l&apos;effort cognitif</A>.
        Suggestions contextuelles, mémoire de session, reconnaissance d&apos;intention :
        l&apos;assistant s&apos;adapte à votre rythme, pas l&apos;inverse.
      </>
    ),
  },
  {
    title: <>L&apos;identification <A>sans friction</A></>,
    body: (
      <>
        Plus de papier, plus d&apos;attente en agence. Une photo de votre pièce, quelques
        mots échangés, et votre dossier est constitué — en{" "}
        <A>moins de dix minutes</A>, où que vous soyez, à toute heure.
      </>
    ),
  },
  {
    title: <>Conformité ARTCI <A>invisible</A></>,
    body: (
      <>
        La loi <A>2013-450</A> est respectée à chaque interaction, sans jamais
        alourdir votre parcours. Consentements signés cryptographiquement, droits
        exerçables d&apos;un mot, journal d&apos;audit immuable.
      </>
    ),
  },
  {
    title: <>Plateforme <A>dédiée MA2E</A></>,
    body: (
      <>
        Plateforme dédiée <A>MA2E</A>, conforme à la loi <A>2013-450</A> sur la
        protection des données ARTCI. Une expérience pensée sur mesure pour
        l&apos;identification des sociétaires du groupe.
      </>
    ),
  },
];

/**
 * Panneau de marque (`sa-auth__brand`) : plaque logo, illustration de
 * l'assistante, message rotatif. Le panneau ne défile jamais.
 */
export default function MarketingPanel() {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const id = setInterval(() => setIdx((i) => (i + 1) % TAGLINES.length), 7000);
    return () => clearInterval(id);
  }, []);

  return (
    <section className="sa-auth__brand" aria-label="Présentation de MA2E">
      <div className="ma2e-auth__art" aria-hidden="true">
        <Image src="/assistant.png" alt="" width={500} height={700} priority className="ma2e-auth__img" />
      </div>

      <div className="sa-auth__claim">
        <div key={idx} className="animate-fade-in" aria-live="polite">
          <h2 className="sa-auth__headline ma2e-auth__headline">{TAGLINES[idx].title}</h2>
          <p className="sa-auth__lead ma2e-auth__lead">{TAGLINES[idx].body}</p>
        </div>
        <div className="ma2e-auth__dots" role="group" aria-label="Messages">
          {TAGLINES.map((_, i) => (
            <button key={i} type="button" onClick={() => setIdx(i)} aria-label={`Message ${i + 1}`} aria-pressed={i === idx} />
          ))}
        </div>
      </div>
    </section>
  );
}
