import express, { Request, Response } from "express";
import bodyParser from "body-parser";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";
import morgan from "morgan";
import moment from "moment";
import cookieParser from "cookie-parser";
import { body, validationResult } from "express-validator";

dotenv.config();

const app = express();
const port = process.env.PORT || 8080;
// Middleware setup
app.use(helmet()); // Security headers
app.use(cors()); // Enable CORS
app.use(morgan("dev")); // Request logging
app.use(bodyParser.json()); // Parse JSON bodies
app.use(bodyParser.urlencoded({ extended: true })); // Parse URL-encoded bodies
app.use(cookieParser()); // Parse cookies

// Basic route
app.get("/", (req: Request, res: Response) => {
  res.send("Hello World!");
});

const technoteRouter = require("./routes/technote");
const conversationRouter = require("./routes/conversation");
const userRouter = require("./routes/user");

app.use("/user", userRouter);
app.use("/technote", technoteRouter);
app.use("/conversation", conversationRouter);

// Example route with validation
app.post(
  "/example",
  [body("email").isEmail(), body("password").isLength({ min: 5 })],
  (req: Request, res: Response) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    res.send("Valid data!");
  }
);

// Server start
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
