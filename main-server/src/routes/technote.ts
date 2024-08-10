import express from "express";

// import review from "../controllers/reviewController";

const techNote = require("../controllers/techNoteController");
const conversation = require("../controllers/conversationController");
const router = express.Router();

router.get("/notion/:notionPageId", techNote.getTechNoteNotionByPageId);

router.get("/all/:userId", techNote.gettechNoteListByUserId);

router.post("/create/extension", techNote.createTechNoteFromExtension);

router.post("/create/link", techNote.createTechNoteFromLink);

router.post("/create/notionpage/:conversation_id", techNote.createNotionPage);

module.exports = router;
