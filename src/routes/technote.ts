import express from "express";

// import review from "../controllers/reviewController";

import * as techNote from "../controllers/techNoteController";
import * as conversation from "../controllers/conversationController";
const router = express.Router();

router.get("/notion/:techNoteId", techNote.getTechNoteNotionById);

router.get("/all/:userId", techNote.gettechNoteListByUserId);

router.post("/create/extension", techNote.createTechNoteFromExtension);

router.post("/create/link", techNote.createTechNoteFromLink);

export default router;
