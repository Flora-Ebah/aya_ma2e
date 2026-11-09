"use client";
import { forwardRef } from "react";
import type { InputHTMLAttributes, Ref, TextareaHTMLAttributes } from "react";
import { Field, Input, Textarea } from "./Field";

type CommonProps = {
  label?: string;
  hint?: string;
  error?: string;
  mono?: boolean;
};

type InputProps = CommonProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
    onValueChange?: (v: string) => void;
    multiline?: false;
  };

type TextareaProps = CommonProps &
  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "className"> & {
    onValueChange?: (v: string) => void;
    multiline: true;
    rows?: number;
  };

type Props = InputProps | TextareaProps;

/**
 * Champ « tout-en-un » (label + contrôle + aide + erreur). API historique
 * conservée ; pour de nouvelles pages préférer `Field` + `Input`/`Textarea`.
 */
export const TextField = forwardRef<HTMLInputElement | HTMLTextAreaElement, Props>(function TextField(props, ref) {
  const { label, hint, error, mono, multiline, ...rest } = props as CommonProps & { multiline?: boolean } & Record<string, unknown>;
  const required = Boolean((rest as { required?: boolean }).required);
  return (
    <Field label={label} help={hint} error={error} required={required} full={multiline || undefined}>
      {multiline ? (
        <Textarea ref={ref as Ref<HTMLTextAreaElement>} {...(rest as TextareaHTMLAttributes<HTMLTextAreaElement>)} />
      ) : (
        <Input ref={ref as Ref<HTMLInputElement>} mono={mono} {...(rest as InputHTMLAttributes<HTMLInputElement>)} />
      )}
    </Field>
  );
});
