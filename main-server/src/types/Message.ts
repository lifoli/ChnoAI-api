// src/types/Messages.ts

export type Message = {
  id: number;
  conversation_id: number;
  message_type: "question" | "answer";
  message_content: string;
  sequence_number: number;
  created_at: string;
};
