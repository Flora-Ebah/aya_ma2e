"use client";
import Image from "next/image";

type Props = { size?: number; avatarOk?: boolean; ring?: boolean };

/** Avatar de l'assistante (image, sinon pastille « M » aux couleurs de la marque). */
export default function AssistantAvatar({ size = 32, avatarOk = true, ring = true }: Props) {
  const cls = `chat-avatar${ring ? " chat-avatar--ring" : ""}`;
  if (avatarOk) {
    return (
      <span className={cls} style={{ width: size, height: size }}>
        <Image src="/assistant-avatar.png" alt="MA2E Assistant" width={size} height={size} />
      </span>
    );
  }
  return (
    <span className={`${cls} chat-avatar--fallback`} style={{ width: size, height: size, fontSize: size * 0.4 }} aria-label="MA2E Assistant" role="img">
      M
    </span>
  );
}
