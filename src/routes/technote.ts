import express from "express";

// import review from "../controllers/reviewController";

const techNote = require("../controllers/techNoteController");
const conversation = require("../controllers/conversationController");
const router = express.Router();

//고객별 리뷰검색 페이지 api
router.get("/test", techNote.test);

// router.get("/notion/:techNoteId", techNote.getTechNoteNotionById);

router.get("/all/:userId", techNote.gettechNoteListByUserId);

module.exports = router;
