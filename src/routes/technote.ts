import express from "express";

// import review from "../controllers/reviewController";

const techNote = require("../controllers/techNoteController");
const conversation = require("../controllers/conversationController");
const router = express.Router();

// router.get("/notion/:techNoteId", techNote.getTechNoteNotionById);

router.get("/all/:userId", techNote.gettechNoteListByUserId);

router.post("/create/extension", techNote.createTechNoteFromExtension);

router.post("/create/link", techNote.createTechNoteFromLink);

module.exports = router;
