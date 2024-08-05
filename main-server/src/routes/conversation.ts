import express from "express";

const conversation = require("../controllers/conversationController");

const router = express.Router();

router.get(
  "/messages/:conversationId",
  conversation.getMessagesByConversationId
);

module.exports = router;
