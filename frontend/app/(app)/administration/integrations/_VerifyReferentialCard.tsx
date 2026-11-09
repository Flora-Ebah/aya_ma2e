"use client";
import { useId, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ConfirmProvider";
import { Icon } from "@/components/Icon";

type VerifyResult = {
  found: boolean;
  matricule: string;
  employeur: string;
  name: string | null;
  fonction: string | null;
  status: string;
  source: string;
};

const EMPLOYEURS = ["CIE", "SODECI", "ERANOVE"];

export default function VerifyReferentialCard() {
  const toast = useToast();
  const uid = useId();
  const [employeur, setEmployeur] = useState("CIE");
  const [matricule, setMatricule] = useState("");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);

  async function run() {
    if (!employeur || !matricule) return;
    setVerifying(true);
    setResult(null);
    try {
      setResult(await api.referentialVerify(employeur, matricule));
    } catch (e: any) {
      toast({ tone: "error", title: "Erreur", message: e.message });
    } finally {
      setVerifying(false);
    }
  }

  return (
    <section className="sa-card" aria-labelledby={`${uid}-t`}>
      <div>
        <h2 className="sa-card__title" id={`${uid}-t`}>Tester le référentiel</h2>
        <p className="sa-card__subtitle">Vérifiez qu&apos;un matricule est reconnu par le référentiel employeur.</p>
      </div>
      <form
        className="sa-form-ligne"
        onSubmit={(e) => { e.preventDefault(); void run(); }}
      >
        <div className="sa-field" style={{ flex: "0 1 200px" }}>
          <label className="sa-label" htmlFor={`${uid}-emp`}>Employeur</label>
          <select id={`${uid}-emp`} className="sa-select" value={employeur} onChange={(e) => setEmployeur(e.target.value)}>
            {EMPLOYEURS.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
        <div className="sa-field">
          <label className="sa-label" htmlFor={`${uid}-mat`}>Matricule</label>
          <input
            id={`${uid}-mat`} className="sa-input sa-mono" type="text" value={matricule}
            onChange={(e) => setMatricule(e.target.value)} placeholder="ex. CIE-00042"
          />
        </div>
        <button
          type="submit" className="sa-btn sa-btn--primary"
          disabled={!matricule || verifying} aria-busy={verifying || undefined}
        >
          {verifying ? "Vérification…" : "Vérifier"}
        </button>
      </form>
      {result && <ResultPanel r={result} />}
    </section>
  );
}

function ResultPanel({ r }: { r: VerifyResult }) {
  return (
    <div className={`sa-alert ${r.found ? "sa-alert--success" : "sa-alert--warning"}`} role="status">
      <Icon name={r.found ? "checkmark-circle-02" : "alert-02"} className="i" />
      <div className="sa-alert__body">
        <div className="sa-alert__title">{r.found ? "Matricule reconnu" : "Matricule non trouvé"}</div>
        {r.found && (
          <div className="sa-alert__text">
            {r.name && <strong>{r.name}</strong>}
            {r.fonction && ` · ${r.fonction}`}
            <div className="sa-help">Statut : {r.status}</div>
          </div>
        )}
        <div className="sa-micro sa-text-soft sa-mono">source : {r.source}</div>
      </div>
    </div>
  );
}
