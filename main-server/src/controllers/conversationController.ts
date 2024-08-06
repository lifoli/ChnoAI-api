import { Request, Response } from "express";

import supabase from "../models/db";

exports.getMessagesByConversationId = async (req: Request, res: Response) => {
  const conversationId = req.params.conversationId;
  const { data, error } = await supabase
    .from("messages")
    .select("*")
    .eq("conversation_id", conversationId)
    .order("sequence_number", { ascending: true });

  if (error) {
    console.error("Error fetching messages:", error);
    return [];
  }
  return res.status(200).send(data);
};
