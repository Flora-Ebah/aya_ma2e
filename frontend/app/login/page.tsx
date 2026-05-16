"use client";
import Image from "next/image";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken, setUser } from "@/lib/api";
import Logo from "@/components/Logo";
import { IconAlertCircle } from "@/components/icons";

const A = ({ children }: { children: React.ReactNode }) => (
  <strong className="text-accent-400 font-semibold">{children}</strong>
);

const TAGLINES: { title: React.ReactNode; body: React.ReactNode }[] = [
  {
    title: (
      <>
        Un <A>compagnon digital</A>, pas un formulaire
      </>
    ),
    body: (
      <>
        Conçu pour <A>comprendre, guider et accompagner</A> chaque sociétaire avec
        naturel. Une conversation simple, fluide, qui vous mène de la première
        salutation à l'enrôlement complet — sans jamais perdre votre fil.
      </>
    ),
  },
  {
    title: (
      <>
        Une expérience pensée pour <A>vous</A>
      </>
    ),
    body: (
      <>
        Chaque échange est calibré pour <A>réduire l'effort cognitif</A>.
        Suggestions contextuelles, mémoire de session, reconnaissance d'intention :
        l'assistant s'adapte à votre rythme, pas l'inverse.
      </>
    ),
  },
  {
    title: (
      <>
        L'identification <A>sans friction</A>
      </>
    ),
    body: (
      <>
        Plus de papier, plus d'attente en agence. Une photo de votre pièce, quelques
        mots échangés, et votre dossier est constitué — en{" "}
        <A>moins de dix minutes</A>, où que vous soyez, à toute heure.
      </>
    ),
  },
  {
    title: (
      <>
        Conformité ARTCI <A>invisible</A>
      </>
    ),
    body: (
      <>
        La loi <A>2013-450</A> est respectée à chaque interaction, sans jamais
        alourdir votre parcours. Consentements signés cryptographiquement, droits
        exerçables d'un mot, journal d'audit immuable.
      </>
    ),
  },
  {
    title: (
      <>
        Conçu pour le <A>groupe</A>, pensé pour <A>chacun</A>
      </>
    ),
    body: (
      <>
        <A>MA2E</A> aujourd'hui, <A>CIE</A> et <A>SODECI</A> demain. Une architecture
        multi-tenant native qui sert chaque entité du groupe avec sa propre identité,
        ses propres flux, sans jamais compromettre la conformité.
      </>
    ),
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@ma2e.ci");
  const [password, setPassword] = useState("ma2e123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [remember, setRemember] = useState(true);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await api.login(email, password);
      setToken(resp.access_token);
      setUser(resp.user);
      router.replace("/dossiers");
    } catch {
      setError("Identifiants invalides.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white relative overflow-hidden">
      <main className="flex items-center justify-center px-6 py-10 relative z-10">
        <div className="w-full max-w-md">
          <div className="mb-14">
            <Logo size={64} />
          </div>

          <h1 className="text-2xl font-semibold text-ink-900 mb-8 tracking-tight">
            Connexion à MA2E
          </h1>

          <form onSubmit={onSubmit} className="space-y-3">
            <FloatingField
              type="email"
              label="Adresse e-mail"
              value={email}
              onChange={setEmail}
              autoComplete="email"
            />
            <FloatingField
              type="password"
              label="Mot de passe"
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
            />

            <div className="flex items-center justify-between pt-1 pb-2">
              <label className="inline-flex items-center gap-2 text-sm text-ink-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 rounded-sm border-ink-300 text-primary-600 focus:ring-primary-200"
                />
                Rester connecté
              </label>
              <button
                type="button"
                className="text-sm font-medium text-primary-600 hover:text-primary-700"
              >
                Mot de passe oublié ?
              </button>
            </div>

            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-800 rounded px-3 py-2 text-sm">
                <IconAlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white font-medium rounded-sm py-2.5 transition shadow-sm disabled:opacity-50"
            >
              {loading ? "Connexion…" : "Se connecter"}
            </button>
          </form>

          <p className="mt-14 text-[11px] text-ink-400 text-center">
            Plateforme sécurisée · Conforme loi 2013-450 (ARTCI)
          </p>
        </div>
      </main>

      <aside className="hidden lg:flex relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-50 via-primary-100 to-primary-300" />
        <div className="absolute -top-32 -right-32 w-[28rem] h-[28rem] rounded-full bg-primary-400/40 blur-3xl" />
        <div className="absolute -bottom-32 -left-16 w-[24rem] h-[24rem] rounded-full bg-accent-400/30 blur-3xl" />

        <div className="relative z-0 w-full h-full flex items-center justify-center p-12">
          <AssistantArt />
        </div>

        <div
          className="absolute bottom-0 left-0 right-0 h-2/3 z-10 pointer-events-none"
          style={{
            background:
              "linear-gradient(to top, #00150a 0%, #00150a 25%, rgba(0, 35, 16, 0.92) 45%, rgba(0, 65, 28, 0.55) 70%, transparent 100%)",
          }}
        />

        <div className="absolute bottom-0 left-0 right-0 z-20 px-12 pb-12 pt-24">
          <RotatingTagline />
        </div>
      </aside>
    </div>
  );
}

function RotatingTagline() {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setIdx((i) => (i + 1) % TAGLINES.length);
    }, 7000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="text-white max-w-xl">
      <div key={idx} className="animate-fade-in min-h-[7rem]">
        <div className="text-[15px] font-normal tracking-tight leading-snug text-white/95">
          {TAGLINES[idx].title}
        </div>
        <p className="text-[13px] font-light text-white/70 mt-2 leading-relaxed">
          {TAGLINES[idx].body}
        </p>
      </div>
      <div className="flex gap-1.5 mt-5">
        {TAGLINES.map((_, i) => (
          <button
            key={i}
            onClick={() => setIdx(i)}
            className={`h-0.5 rounded-full transition-all duration-500 cursor-pointer ${
              i === idx ? "w-10 bg-white" : "w-5 bg-white/25 hover:bg-white/50"
            }`}
            aria-label={`Slide ${i + 1}`}
          />
        ))}
      </div>
    </div>
  );
}

function AssistantArt() {
  return (
    <div className="relative w-full max-w-md max-h-[600px] mx-auto flex items-center justify-center">
      <Image
        src="/assistant.png"
        alt="MA2E Virtual Assistant"
        width={500}
        height={700}
        priority
        className="object-contain drop-shadow-2xl"
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
          const fb = (e.target as HTMLImageElement).nextElementSibling;
          if (fb) (fb as HTMLElement).style.display = "flex";
        }}
      />
      <div
        style={{ display: "none" }}
        className="absolute inset-0 flex-col items-center justify-center text-center"
      >
        <div className="w-56 h-56 bg-white/40 backdrop-blur-sm rounded shadow-card flex items-center justify-center">
          <div className="text-primary-700 text-center px-6">
            <div className="text-sm font-semibold mb-2">Assistant Virtuel</div>
            <div className="text-xs text-primary-700/70">
              Placez votre image à
              <br />
              <code className="font-mono">/public/assistant.png</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FloatingField({
  label,
  value,
  onChange,
  type,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type: string;
  icon?: React.ReactNode;
  autoComplete?: string;
}) {
  return (
    <div className="relative">
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        autoComplete={autoComplete}
        placeholder=" "
        className="peer w-full bg-ink-50 hover:bg-ink-100/60 border border-transparent focus:bg-white focus:border-primary-500 rounded-sm px-3.5 py-3.5 text-[15px] text-ink-900 focus:outline-none transition"
      />
      <label
        className="
          pointer-events-none absolute transition-all
          left-3 -top-2 text-[11px] font-medium text-primary-600 bg-white px-1.5
          peer-placeholder-shown:left-3.5 peer-placeholder-shown:top-1/2 peer-placeholder-shown:-translate-y-1/2 peer-placeholder-shown:text-[15px] peer-placeholder-shown:font-normal peer-placeholder-shown:text-ink-400 peer-placeholder-shown:bg-transparent peer-placeholder-shown:px-0
          peer-focus:left-3 peer-focus:top-[-9px] peer-focus:translate-y-0 peer-focus:text-[11px] peer-focus:font-medium peer-focus:text-primary-600 peer-focus:bg-white peer-focus:px-1.5
        "
      >
        {label}
      </label>
    </div>
  );
}
