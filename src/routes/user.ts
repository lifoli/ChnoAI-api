import express from "express";

// import review from "../controllers/reviewController";

import * as techNote from "../controllers/techNoteController";

import * as user from "../controllers/userController";
const router = express.Router();

router.get("/test", techNote.test);

router.get("/info/:userId", user.getInfoByUserId);

router.post("/create", user.createUser);

export default router;
