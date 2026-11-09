"use client";
import { IconButton } from "@/components/ui/IconButton";
import AssistantAvatar from "./_AssistantAvatar";

type Props = {
  avatarOk: boolean;
  onReset: () => void;
};

export default function ChatHeader({ avatarOk, onReset }: Props) {
  return (
    <div className="chat-head">
      <div className="chat-wrap chat-head__row">
        <div className="chat-head__who">
          <AssistantAvatar size={40} avatarOk={avatarOk} ring={false} />
          <div>
            <div className="sa-strong">MA2E Assistant</div>
            <div className="sa-header__eyebrow">En ligne</div>
          </div>
        </div>
        <IconButton icon="cancel-01" variant="outline" label="Terminer la conversation" onClick={onReset} />
      </div>
    </div>
  );
}
