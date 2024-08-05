// src/types/Conversations.ts

import { ConversationSource } from "./Enums";

export type Conversation = {
  id: number;
  user_id: number;
  source: ConversationSource;
  link: string;
  conversation_content: string;
  created_at: string;
};
