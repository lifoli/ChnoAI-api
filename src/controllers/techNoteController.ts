import { Request, Response } from "express";
import express from "express";
import supabase from "../models/db";
import bodyParser from "body-parser";
import puppeteer from "puppeteer";

// import { NotionAPI } from "notion-client";

import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";

// export const getTechNoteNotionById = async (req: Request, res: Response) => {
//   try {
//     const notion = new NotionAPI();
//     const techNoteId = req.params.techNoteId;
//     const recordMap = await notion.getPage(techNoteId);
//     res.json(recordMap);

//     // if (!techNote) {
//     //   return res.status(404).json({ message: "TechNote not found" });
//     // }
//     // res.json(techNote);
//   } catch (error) {
//     const err = error as Error;
//     res.status(500).json({ message: err.message });
//   }
// };

exports.test = (req: Request, res: Response) => {
  console.log("test");
  return res.status(200).send({ message: "Product not found" });
};

exports.createTechNoteFromExtension = async (req: Request, res: Response) => {
  const { user_id, raw_content } = req.body;

  if (!user_id || !raw_content) {
    return res
      .status(400)
      .json({ message: "Missing required fields: user_id or raw_content" });
  }

  try {
    // conversations 테이블에 데이터 추가
    const { data: conversationData, error: conversationError } = await supabase
      .from("conversations")
      .insert([
        {
          user_id,
          conversation_content: raw_content,
          source: "chrome_extension",
        },
      ])
      .select("*")
      .single();

    if (conversationError) {
      console.error("Error inserting conversation:", conversationError);
      return res.status(500).json({ message: "Error inserting conversation" });
    }
    // TODO: 메세지 생성 로직 추가
    const messages = [
      {
        message_type: "question",
        message_content: "conversation로직 들어갈 예정1",
        conversation_id: conversationData.id,
        sequence_number: 1,
      },
      {
        message_type: "answer",
        message_content: "conversation로직 들어갈 예정2",
        conversation_id: conversationData.id,
        sequence_number: 2,
      },
      {
        message_type: "question",
        message_content: "conversation로직 들어갈 예정3",
        conversation_id: conversationData.id,
        sequence_number: 3,
      },
      {
        message_type: "answer",
        message_content: "conversation로직 들어갈 예정4",
        conversation_id: conversationData.id,
        sequence_number: 4,
      },
    ];

    // tech_notes 테이블에 데이터 추가
    const { data: techNoteData, error: techNoteError } = await supabase
      .from("tech_notes")
      .insert([
        {
          conversation_id: conversationData.id,
          title: "Preparing the notes.",
          note_content: "",
          is_completed: false,
        },
      ])
      .select("*")
      .single();

    if (techNoteError) {
      console.error("Error inserting tech note:", techNoteError);
      return res.status(500).json({ message: "Error inserting tech note" });
    }

    // messages 테이블에 데이터 추가
    const { data: messagesData, error: messagesError } = await supabase
      .from("messages")
      .insert(messages)
      .select("*");

    if (messagesError) {
      console.error("Error inserting messages:", messagesError);
      return res.status(500).json({ message: "Error inserting messages" });
    }

    return res.status(201).json({ techNoteData });
  } catch (error) {
    console.error("Unexpected error:", error);
    return res.status(500).json({ message: "An unexpected error occurred" });
  }
};

exports.gettechNoteListByUserId = async (req: Request, res: Response) => {
  const userId = req.params.userId;
  // tech_notes 테이블과 conversation 테이블을 조인해서 user_id로 필터링

  const { data, error } = await supabase
    .from("tech_notes")
    .select("*, conversations!inner(user_id)")
    .eq("conversations.user_id", userId);

  if (error) {
    console.error("Error fetching tech notes:", error);
    return [];
  }

  return res.status(200).send(data);
};

// service함수로 이전
async function runHeadlessBrowser(url: string) {
  if (!url.startsWith("https://chatgpt.com/share/")) {
    throw new Error("Invalid URL");
  }

  const browser = await puppeteer.launch({
    headless: true, // 헤드리스 모드 활성화
    args: ["--no-sandbox", "--disable-setuid-sandbox"], // 샌드박스 비활성화 (속도 향상)
  });

  const page = await browser.newPage();

  // 불필요한 리소스 차단
  await page.setRequestInterception(true);
  page.on("request", (request) => {
    const resourceType = request.resourceType();
    if (
      resourceType === "image" ||
      resourceType === "stylesheet" ||
      resourceType === "font"
    ) {
      request.abort();
    } else {
      request.continue();
    }
  });

  try {
    await page.goto(url, { waitUntil: "domcontentloaded" }); // DOMContentLoaded 대기

    const chatUrl = await page.evaluate(() => window.location.href);

    const chatRoomTitle = await page.$eval("h1", (el) => el.textContent);

    const userMessages = await page.$$eval(
      '[data-message-author-role="user"]',
      (elements) => elements.map((el) => el.textContent)
    );
    const assistantMessages = await page.$$eval(
      '[data-message-author-role="assistant"]',
      (elements) => elements.map((el) => el.textContent)
    );

    const data = userMessages.map((question, index) => ({
      question: question || "",
      answer: assistantMessages[index] || "",
    }));

    console.log("Chat URL:", chatUrl, "Chat Room Title:", chatRoomTitle, data);
    return { chatUrl, chatRoomTitle, data };
  } catch (error) {
    console.error("Error occurred:", error);
    throw error;
  } finally {
    await browser.close();
  }
}

exports.createTechNoteFromLink = async (req: Request, res: Response) => {
  const { user_id, url } = req.body;

  if (!user_id || !url) {
    return res
      .status(400)
      .json({ message: "Missing required fields: user_id or url" });
  }

  try {
    const { chatUrl, chatRoomTitle, data } = await runHeadlessBrowser(url);
    console.log("🚀 ~ data:", data);

    // conversations 테이블에 데이터 추가
    const { data: conversationData, error: conversationError } = await supabase
      .from("conversations")
      .insert([
        {
          user_id,
          source: "direct_link",
          link: chatUrl,
        },
      ])
      .select("*")
      .single();

    // 데이터가 없을 경우 에러 처리
    if (conversationError) {
      console.error("Error inserting conversation:", conversationError);
      return res.status(500).json({ message: "Error inserting conversation" });
    }

    const messages = data.flatMap(({ question, answer }, index) => [
      {
        message_type: "question",
        message_content: question,
        conversation_id: conversationData.id,
        sequence_number: index * 2 + 1,
      },
      {
        message_type: "answer",
        message_content: answer,
        conversation_id: conversationData.id,
        sequence_number: index * 2 + 2,
      },
    ]);
    console.log("🚀 ~ messages ~ messages:", messages);

    // tech_notes 테이블에 데이터 추가
    const { data: techNoteData, error: techNoteError } = await supabase
      .from("tech_notes")
      .insert([
        {
          conversation_id: conversationData.id,
          title: chatRoomTitle,
          note_content: "",
          is_completed: false,
        },
      ])
      .select("*")
      .single();

    if (techNoteError) {
      console.error("Error inserting tech note:", techNoteError);
      return res.status(500).json({ message: "Error inserting tech note" });
    }

    // messages 테이블에 데이터 추가
    const { data: messagesData, error: messagesError } = await supabase
      .from("messages")
      .insert(messages)
      .select("*");

    if (messagesError) {
      console.error("Error inserting messages:", messagesError);
      return res.status(500).json({ message: "Error inserting messages" });
    }

    return res.status(201).json({ techNoteData });
  } catch (error) {
    console.error("Unexpected error:", error);
    return res.status(500).json({ message: "An unexpected error occurred" });
  }
};
