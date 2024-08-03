import express from "express";
import * as conversation from "../controllers/conversationController";

const router = express.Router();

router.get(
  "/messages/:conversationId",
  conversation.getMessagesByConversationId
);

export default router;
