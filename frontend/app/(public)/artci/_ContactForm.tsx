"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Checkbox, Field, FormActions, FormGrid, Input, Textarea } from "@/components/ui/Field";

type ContactPayload = {
  full_name: string;
  email: string;
  subject: string;
  message: string;
  request_type: "access" | "rectification" | "deletion" | "opposition" | "other";
};

const REQUEST_TYPES: Array<[ContactPayload["request_type"], string]> = [
  ["access", "Accès à mes données (art. 18)"],
  ["rectification", "Rectification (art. 19)"],
  ["deletion", "Suppression / droit à l'oubli (art. 21)"],
  ["opposition", "Opposition au traitement (art. 22)"],
  ["other", "Autre"],
];

export default function ContactForm() {
  const [form, setForm] = useState<ContactPayload>({
    full_name: "", email: "", subject: "", message: "", request_type: "access",
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      // US-29 AC3 : appel serveur réel qui notifie le DPO et trace en audit
      await api.artciContact(form);
      setSubmitted(true);
    } catch {
      setError(
        "Impossible d'enregistrer votre demande. "
          + "Vous pouvez nous écrire directement à dpo@ma2e.ci.",
      );
    } finally {
      setSending(false);
    }
  }

  if (submitted) {
    return (
      <Alert tone="success" title="Demande enregistrée">
        Le DPO MA2E a été notifié et vous répondra sous <strong>30 jours</strong> au plus.
        Vous recevrez une confirmation à l&apos;adresse email indiquée.
      </Alert>
    );
  }

  const update = (k: keyof ContactPayload) => (v: string) => setForm({ ...form, [k]: v });

  return (
    <section aria-labelledby="form-title">
      <Card
        title={<span id="form-title">Formulaire de demande</span>}
        subtitle="Précisez votre demande ci-dessous. Le DPO MA2E sera notifié immédiatement et vous répondra sous 30 jours conformément à la loi 2013-450 (art. 18-22)."
      >
        <FormGrid as="form" onSubmit={onSubmit} noValidate>
          <Field label="Nom complet" required>
            <Input type="text" value={form.full_name} required onValueChange={update("full_name")} />
          </Field>
          <Field label="Adresse email" required>
            <Input type="email" value={form.email} required onValueChange={update("email")} />
          </Field>
          <Field label="Objet" required>
            <Input type="text" value={form.subject} required onValueChange={update("subject")} />
          </Field>

          <fieldset className="sa-fieldset sa-field--full" style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
            <legend className="sa-label" style={{ marginBottom: 4 }}>Nature de la demande</legend>
            <div style={{ display: "flex", flexWrap: "wrap", columnGap: 24 }}>
              {REQUEST_TYPES.map(([k, lbl]) => (
                <Checkbox
                  key={k} radio name="request_type" value={k} label={lbl}
                  checked={form.request_type === k}
                  onChange={() => setForm({ ...form, request_type: k })}
                />
              ))}
            </div>
          </fieldset>

          <Field label="Détail de la demande" required full>
            <Textarea rows={5} required value={form.message} onValueChange={update("message")} />
          </Field>

          {error && (
            <div className="sa-field--full">
              <Alert tone="error" compact>{error}</Alert>
            </div>
          )}

          <div className="sa-field--full">
            <FormActions>
              <Button type="submit" icon="mail-send-01" loading={sending}>
                {sending ? "Envoi…" : "Envoyer au DPO"}
              </Button>
            </FormActions>
          </div>
        </FormGrid>
      </Card>
    </section>
  );
}
