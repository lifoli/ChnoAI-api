import express from "express";

// import review from "../controllers/reviewController";

const techNote = require("../controllers/techNoteController");

const user = require("../controllers/userController");
const router = express.Router();

router.get("/test", techNote.test);

router.get("/info/:userId", user.getInfoByUserId);

router.post("/create", user.createUser);

module.exports = router;
