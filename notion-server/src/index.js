import express from "express";
import bodyParser from "body-parser";
import cookieParser from "cookie-parser";
import cors from "cors";
import dotenv from "dotenv";
import helmet from "helmet";
import morgan from "morgan";
import { body, validationResult } from "express-validator";
import moment from "moment";
import { NotionAPI } from "notion-client";
import path from "path";
import { fileURLToPath } from "url";
// const { NotionAPI } = require("notion-client");

// 환경 변수 로드
dotenv.config();

const app = express();
const port = process.env.NOTION_SERVER_PORT || 8000;

// 미들웨어 설정
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(cors());
app.use(helmet());
app.use(morgan("dev"));

// 기본 라우트
app.get("/", (req, res) => {
  res.send("Hello World!");
});

app.get("/notion/:pageId", async (req, res) => {
  const notion_token = process.env.NOTION_TOKEN;
  const notion = new NotionAPI();
  //   {
  //   authToken: process.env.NOTION_TOKEN, // API 토큰을 여기에 입력
  // }
  const { pageId } = req.params;
  try {
    const recordMap = await notion.getPage(pageId);
    res.json(recordMap);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 예시 라우트
app.post(
  "/data",
  [
    body("name").notEmpty().withMessage("Name is required"),
    body("email").isEmail().withMessage("Invalid email format"),
  ],
  (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ errors: errors.array() });
    }
    const { name, email } = req.body;
    res.json({ message: `Hello, ${name}! Your email is ${email}.` });
  }
);

// 서버 시작
app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});
