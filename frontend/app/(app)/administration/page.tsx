import { redirect } from "next/navigation";

export default function AdministrationIndex() {
  redirect("/administration/utilisateurs");
}
